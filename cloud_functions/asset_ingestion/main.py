"""
Cloud Function (gen2) — GCS Asset Ingestion Pipeline

Triggered when a new object is finalized (uploaded) to the CMS assets bucket.
Downloads the file, generates text + image embeddings, and indexes into Elasticsearch.

Entry point: process_asset
"""

import hashlib
import io
import os
import re
from datetime import datetime, timezone
from pathlib import PurePosixPath

import functions_framework
from cloudevents.http import CloudEvent
from elasticsearch import Elasticsearch
from google.cloud import storage
from PIL import Image
from sentence_transformers import SentenceTransformer

# ── Config from environment ──────────────────────────────────────

ELASTIC_CLOUD_ID = os.environ["ELASTIC_CLOUD_ID"]
ELASTIC_API_KEY = os.environ["ELASTIC_API_KEY"]
CONTENT_INDEX = os.environ.get("CONTENT_INDEX", "cms-content")

# ── MIME → content_type mapping ──────────────────────────────────

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff", ".svg"}
DOCUMENT_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".md", ".rtf", ".csv", ".xls", ".xlsx", ".pptx"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".aac", ".m4a"}

SUPPORTED_IMAGE_FOR_CLIP = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff"}


def _classify_content_type(filename: str) -> str:
    ext = PurePosixPath(filename).suffix.lower()
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in DOCUMENT_EXTENSIONS:
        return "document"
    if ext in VIDEO_EXTENSIONS:
        return "video"
    if ext in AUDIO_EXTENSIONS:
        return "audio"
    return "document"


def _get_file_type(filename: str) -> str:
    ext = PurePosixPath(filename).suffix.lower().lstrip(".")
    return ext or "unknown"


def _title_from_filename(filename: str) -> str:
    stem = PurePosixPath(filename).stem
    # Convert snake_case/kebab-case/camelCase to spaces
    title = re.sub(r"[-_]", " ", stem)
    title = re.sub(r"([a-z])([A-Z])", r"\1 \2", title)
    return title.strip().title()


def _tags_from_path(object_path: str) -> list[str]:
    parts = PurePosixPath(object_path).parent.parts
    # Use folder names as tags (skip empty/root)
    return [p.lower().replace("_", " ").replace("-", " ") for p in parts if p]


# ── Lazy model singletons (warm across invocations) ─────────────

_text_model = None
_clip_model = None


def _get_text_model() -> SentenceTransformer:
    global _text_model
    if _text_model is None:
        print("Loading text model: all-MiniLM-L6-v2")
        _text_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _text_model


def _get_clip_model() -> SentenceTransformer:
    global _clip_model
    if _clip_model is None:
        print("Loading CLIP model: clip-ViT-B-32")
        _clip_model = SentenceTransformer("clip-ViT-B-32")
    return _clip_model


def _embed_text(text: str) -> list[float]:
    model = _get_text_model()
    vec = model.encode(text, normalize_embeddings=True)
    return vec.tolist()


def _embed_image(image_bytes: bytes) -> list[float] | None:
    try:
        model = _get_clip_model()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        vec = model.encode(image, normalize_embeddings=True)
        return vec.tolist()
    except Exception as e:
        print(f"  Failed to generate image embedding: {e}")
        return None


def _get_es_client() -> Elasticsearch:
    return Elasticsearch(cloud_id=ELASTIC_CLOUD_ID, api_key=ELASTIC_API_KEY)


def _deterministic_id(bucket: str, name: str) -> str:
    return hashlib.sha256(f"{bucket}/{name}".encode()).hexdigest()[:20]


# ── Cloud Function entry point ──────────────────────────────────

@functions_framework.cloud_event
def process_asset(cloud_event: CloudEvent):
    """Triggered by GCS object finalize event."""

    data = cloud_event.data
    bucket_name = data["bucket"]
    object_name = data["name"]
    content_type_mime = data.get("contentType", "")

    print(f"Processing: gs://{bucket_name}/{object_name} ({content_type_mime})")

    # Skip non-asset files (e.g. folder markers, .gitkeep)
    filename = PurePosixPath(object_name).name
    if not filename or filename.startswith("."):
        print(f"  Skipping non-asset file: {object_name}")
        return

    content_type = _classify_content_type(filename)
    file_type = _get_file_type(filename)

    # Download the file from GCS
    gcs_client = storage.Client()
    bucket = gcs_client.bucket(bucket_name)
    blob = bucket.blob(object_name)
    file_bytes = blob.download_as_bytes()

    print(f"  Downloaded {len(file_bytes)} bytes | type={content_type} | file_type={file_type}")

    # Build metadata
    title = _title_from_filename(filename)
    tags = _tags_from_path(object_name)
    public_url = f"https://storage.googleapis.com/{bucket_name}/{object_name}"

    # Build the text to embed
    text_for_embedding = f"{title}. {' '.join(tags)}"[:512]

    # Generate text embedding
    print(f"  Generating text embedding for: {text_for_embedding[:80]}...")
    text_embedding = _embed_text(text_for_embedding)

    # Generate image embedding if applicable
    image_embedding = None
    ext = PurePosixPath(filename).suffix.lower()
    if content_type == "image" and ext in SUPPORTED_IMAGE_FOR_CLIP:
        print("  Generating CLIP image embedding...")
        image_embedding = _embed_image(file_bytes)

    # Get image dimensions if applicable
    width, height = 0, 0
    if content_type == "image":
        try:
            img = Image.open(io.BytesIO(file_bytes))
            width, height = img.size
        except Exception:
            pass

    # Build Elasticsearch document
    doc = {
        "title": title,
        "description": f"Uploaded asset: {filename}",
        "content_type": content_type,
        "tags": tags,
        "category": tags[0] if tags else "uploads",
        "source": "gcs-upload",
        "author": "",
        "license": "",
        "url": public_url,
        "thumbnail_url": public_url if content_type == "image" else "",
        "preview_url": public_url if content_type == "image" else "",
        "file_type": file_type,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "region": "",
        "geo_location": None,
        "width": width,
        "height": height,
        "duration_seconds": 0,
        "view_count": 0,
        "download_count": 0,
        "text_embedding": text_embedding,
        "gcs_bucket": bucket_name,
        "gcs_object": object_name,
    }

    if image_embedding:
        doc["image_embedding"] = image_embedding

    # Index into Elasticsearch (upsert using deterministic ID)
    doc_id = _deterministic_id(bucket_name, object_name)
    es = _get_es_client()
    es.index(index=CONTENT_INDEX, id=doc_id, document=doc)
    print(f"  Indexed document {doc_id} into {CONTENT_INDEX}")
    print(f"  ✔ Done processing {object_name}")
