"""
Bulk ingestion script for the animals dataset stored in GCS.

Downloads every image from gs://cms-ai-assets-elastic-sa/datasets/animals/,
generates CLIP (512D) image + MiniLM (384D) text embeddings, and upserts into
the cms-content Elasticsearch index using the same deterministic document IDs
as the Cloud Function ingestion service.

Usage (run from backend/ directory):
    python -m scripts.ingest_animals_gcs

Requirements:
    pip install google-cloud-storage sentence-transformers Pillow elasticsearch

Env (.env in backend/):
    ELASTIC_CLOUD_ID=...
    ELASTIC_API_KEY=...
    GCS_BUCKET_NAME=cms-ai-assets-elastic-sa   # optional, defaults to this value
"""

import hashlib
import io
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from google.cloud import storage
from PIL import Image
from sentence_transformers import SentenceTransformer

# ── Constants ────────────────────────────────────────────────────

BUCKET_NAME = "cms-ai-assets-elastic-sa"
GCS_PREFIX = "datasets/animals/"
CONTENT_INDEX = "cms-content"
BATCH_SIZE = 50   # docs per ES bulk request
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff"}

# ── Read credentials from .env ───────────────────────────────────


def _read_env() -> tuple[str, str]:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    cloud_id, api_key = "", ""
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("ELASTIC_CLOUD_ID="):
                cloud_id = line.split("=", 1)[1].strip()
            elif line.startswith("ELASTIC_API_KEY="):
                api_key = line.split("=", 1)[1].strip()
    if not cloud_id or not api_key:
        print("ERROR: ELASTIC_CLOUD_ID and ELASTIC_API_KEY must be set in backend/.env")
        sys.exit(1)
    return cloud_id, api_key


def get_es_client() -> Elasticsearch:
    cloud_id, api_key = _read_env()
    return Elasticsearch(cloud_id=cloud_id, api_key=api_key)


# ── Lazy model singletons ────────────────────────────────────────

_text_model: SentenceTransformer | None = None
_clip_model: SentenceTransformer | None = None


def get_text_model() -> SentenceTransformer:
    global _text_model
    if _text_model is None:
        print("Loading text model: all-MiniLM-L6-v2 ...")
        _text_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _text_model


def get_clip_model() -> SentenceTransformer:
    global _clip_model
    if _clip_model is None:
        print("Loading CLIP model: clip-ViT-B-32 ...")
        _clip_model = SentenceTransformer("clip-ViT-B-32")
    return _clip_model


# ── Helpers ──────────────────────────────────────────────────────


def deterministic_id(bucket: str, name: str) -> str:
    """SHA-256 doc ID — matches the Cloud Function ingestion service."""
    return hashlib.sha256(f"{bucket}/{name}".encode()).hexdigest()[:20]


def title_from_filename(filename: str) -> str:
    stem = PurePosixPath(filename).stem
    title = re.sub(r"[-_]", " ", stem)
    title = re.sub(r"([a-z])([A-Z])", r"\1 \2", title)
    return title.strip().title()


def tags_from_path(object_path: str) -> list[str]:
    parts = PurePosixPath(object_path).parent.parts
    return [p.lower().replace("_", " ").replace("-", " ") for p in parts if p]


def embed_image_bytes(image_bytes: bytes) -> list[float] | None:
    try:
        model = get_clip_model()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        vec = model.encode(image, normalize_embeddings=True)
        return vec.tolist()
    except Exception as e:
        print(f"    CLIP embed failed: {e}")
        return None


def embed_text(text: str) -> list[float]:
    model = get_text_model()
    vec = model.encode(text, normalize_embeddings=True)
    return vec.tolist()


# ── Core ingestion logic ─────────────────────────────────────────


def list_blobs(gcs_client: storage.Client) -> list[storage.Blob]:
    bucket = gcs_client.bucket(BUCKET_NAME)
    blobs = [
        b for b in bucket.list_blobs(prefix=GCS_PREFIX)
        if PurePosixPath(b.name).suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    return blobs


def process_blob(blob: storage.Blob) -> dict | None:
    """Download a GCS blob and return an ES-ready document dict, or None on failure."""
    filename = PurePosixPath(blob.name).name
    try:
        file_bytes = blob.download_as_bytes()
    except Exception as e:
        print(f"    Download failed for {blob.name}: {e}")
        return None

    # Metadata
    title = title_from_filename(filename)
    tags = tags_from_path(blob.name)
    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{blob.name}"
    text_for_embedding = f"{title}. {' '.join(tags)}"[:512]

    # Embeddings
    text_embedding = embed_text(text_for_embedding)
    image_embedding = embed_image_bytes(file_bytes)

    # Dimensions
    width, height = 0, 0
    try:
        img = Image.open(io.BytesIO(file_bytes))
        width, height = img.size
    except Exception:
        pass

    doc = {
        "title": title,
        "description": f"Animal photo: {filename}",
        "content_type": "image",
        "tags": tags,
        "category": "animals",
        "source": "gcs-upload",
        "author": "",
        "license": "",
        "url": public_url,
        "thumbnail_url": public_url,
        "preview_url": public_url,
        "file_type": PurePosixPath(filename).suffix.lower().lstrip("."),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "region": "",
        "geo_location": None,
        "width": width,
        "height": height,
        "duration_seconds": 0,
        "view_count": 0,
        "download_count": 0,
        "text_embedding": text_embedding,
        "gcs_bucket": BUCKET_NAME,
        "gcs_object": blob.name,
    }
    if image_embedding:
        doc["image_embedding"] = image_embedding

    return doc


def bulk_upsert(es: Elasticsearch, batch: list[tuple[str, dict]]) -> tuple[int, int]:
    """Upsert a batch of (doc_id, doc) pairs. Returns (success, error) counts."""
    actions = [
        {
            "_op_type": "index",
            "_index": CONTENT_INDEX,
            "_id": doc_id,
            "_source": doc,
        }
        for doc_id, doc in batch
    ]
    success, errors = bulk(es, actions, raise_on_error=False)
    return success, len(errors) if isinstance(errors, list) else 0


# ── Main ─────────────────────────────────────────────────────────


def main():
    print("=" * 60)
    print("  Animals GCS Ingestion — Elastic CMS AI Search")
    print("=" * 60)
    print(f"  Bucket  : gs://{BUCKET_NAME}/{GCS_PREFIX}")
    print(f"  Index   : {CONTENT_INDEX}")
    print(f"  Batch   : {BATCH_SIZE} docs per ES request")
    print()

    # Connect
    es = get_es_client()
    info = es.info()
    print(f"Connected to Elasticsearch: {info['cluster_name']} (v{info['version']['number']})\n")

    gcs_client = storage.Client(project="elastic-sa")

    # List blobs
    print("Listing images in GCS ...")
    blobs = list_blobs(gcs_client)
    total = len(blobs)
    print(f"Found {total} image files in gs://{BUCKET_NAME}/{GCS_PREFIX}\n")

    if total == 0:
        print("Nothing to ingest. Exiting.")
        return

    # Pre-load models so first-image timing is accurate
    get_text_model()
    get_clip_model()
    print()

    # Process + bulk index
    batch: list[tuple[str, dict]] = []
    total_success = 0
    total_errors = 0
    total_skipped = 0
    start_time = time.time()

    for idx, blob in enumerate(blobs, 1):
        print(f"[{idx:5d}/{total}] {blob.name}", end="", flush=True)
        doc = process_blob(blob)
        if doc is None:
            total_skipped += 1
            print(" — SKIPPED")
            continue

        has_img_emb = "image_embedding" in doc
        print(f" — text+{'CLIP' if has_img_emb else 'no-CLIP'} embeddings", end="", flush=True)

        doc_id = deterministic_id(BUCKET_NAME, blob.name)
        batch.append((doc_id, doc))

        if len(batch) >= BATCH_SIZE:
            s, e = bulk_upsert(es, batch)
            total_success += s
            total_errors += e
            batch = []
            elapsed = time.time() - start_time
            rate = idx / elapsed
            remaining = (total - idx) / rate if rate > 0 else 0
            print(f" | indexed {idx} | {rate:.1f}/s | ~{remaining/60:.0f}m left")
        else:
            print()

    # Flush remaining
    if batch:
        s, e = bulk_upsert(es, batch)
        total_success += s
        total_errors += e

    # Refresh + verify
    es.indices.refresh(index=CONTENT_INDEX)
    count = es.count(index=CONTENT_INDEX)["count"]

    elapsed = time.time() - start_time
    print()
    print("=" * 60)
    print(f"  Ingestion complete in {elapsed/60:.1f} min")
    print(f"  Indexed  : {total_success}")
    print(f"  Errors   : {total_errors}")
    print(f"  Skipped  : {total_skipped}")
    print(f"  Total docs in '{CONTENT_INDEX}': {count}")
    print("=" * 60)


if __name__ == "__main__":
    main()
