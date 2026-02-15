"""
Embedding models for text and image content.

Uses:
  - all-MiniLM-L6-v2  (384 dims) for text embeddings
  - clip-ViT-B-32     (512 dims) for image + cross-modal embeddings

Models are loaded lazily on first use and cached as singletons.
"""

import io
from functools import lru_cache

import httpx
from PIL import Image
from sentence_transformers import SentenceTransformer

from config import settings


@lru_cache(maxsize=1)
def get_text_model() -> SentenceTransformer:
    print(f"Loading text model: {settings.text_model_name}...")
    return SentenceTransformer(settings.text_model_name)


@lru_cache(maxsize=1)
def get_clip_model() -> SentenceTransformer:
    print(f"Loading CLIP model: {settings.clip_model_name}...")
    return SentenceTransformer(settings.clip_model_name)


def embed_text(text: str) -> list[float]:
    """Generate a 384-dim embedding from text using MiniLM."""
    model = get_text_model()
    vec = model.encode(text, normalize_embeddings=True)
    return vec.tolist()


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Batch-embed multiple texts."""
    model = get_text_model()
    vecs = model.encode(texts, normalize_embeddings=True, batch_size=64, show_progress_bar=True)
    return vecs.tolist()


def embed_image_from_bytes(image_bytes: bytes) -> list[float]:
    """Generate a 512-dim CLIP embedding from raw image bytes."""
    model = get_clip_model()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    vec = model.encode(image, normalize_embeddings=True)
    return vec.tolist()


def embed_image_from_url(url: str) -> list[float] | None:
    """Download an image from a URL and return its CLIP embedding."""
    try:
        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return embed_image_from_bytes(resp.content)
    except Exception as e:
        print(f"  Failed to embed image from {url}: {e}")
        return None


def embed_text_for_image_search(text: str) -> list[float]:
    """
    Encode text using the CLIP model (512 dims).
    This puts text into the same vector space as images,
    enabling text-to-image search.
    """
    model = get_clip_model()
    vec = model.encode(text, normalize_embeddings=True)
    return vec.tolist()
