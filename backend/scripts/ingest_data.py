"""
Reads downloaded asset metadata, generates embeddings, and bulk-indexes into Elasticsearch.

Usage:
    cd backend
    python -m scripts.ingest_data

Prerequisites:
    1. Run setup_indices.py first
    2. Run download_assets.py first (or have data/metadata/all_assets.json)
"""

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

from config import settings
from models.embeddings import embed_texts, embed_image_from_url

DATA_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "metadata" / "all_assets.json"
BATCH_SIZE = 100


def get_es_client() -> Elasticsearch:
    # Read credentials directly from .env to avoid pydantic-settings cloud_id parsing issue
    from pathlib import Path
    env_path = Path(__file__).resolve().parent.parent / ".env"
    cloud_id = ""
    api_key = ""
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("ELASTIC_CLOUD_ID="):
                cloud_id = line.split("=", 1)[1].strip()
            elif line.startswith("ELASTIC_API_KEY="):
                api_key = line.split("=", 1)[1].strip()
    return Elasticsearch(cloud_id=cloud_id, api_key=api_key)


def load_assets() -> list[dict]:
    if not DATA_FILE.exists():
        print(f"ERROR: {DATA_FILE} not found. Run download_assets.py first.")
        sys.exit(1)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        assets = json.load(f)
    print(f"Loaded {len(assets)} assets from {DATA_FILE.name}")
    return assets


def generate_text_embeddings(assets: list[dict]) -> list[list[float]]:
    """Generate text embeddings for all assets in batches."""
    texts = []
    for a in assets:
        combined = f"{a.get('title', '')}. {a.get('description', '')}. {' '.join(a.get('tags', []))}"
        texts.append(combined[:512])  # truncate long text

    print(f"Generating text embeddings for {len(texts)} assets...")
    start = time.time()
    embeddings = embed_texts(texts)
    elapsed = time.time() - start
    print(f"  Text embeddings done in {elapsed:.1f}s ({len(texts)/elapsed:.0f} items/sec)")
    return embeddings


def generate_image_embeddings(assets: list[dict]) -> dict[int, list[float]]:
    """Generate CLIP image embeddings for image assets that have thumbnail URLs."""
    image_indices = [
        i for i, a in enumerate(assets)
        if a.get("content_type") == "image" and a.get("thumbnail_url")
    ]
    print(f"Generating image embeddings for {len(image_indices)} image assets...")

    embeddings = {}
    done = 0
    for i in image_indices:
        url = assets[i]["thumbnail_url"]
        vec = embed_image_from_url(url)
        if vec:
            embeddings[i] = vec
        done += 1
        if done % 50 == 0:
            print(f"  Image embeddings: {done}/{len(image_indices)}")

    print(f"  Image embeddings done: {len(embeddings)} successful out of {len(image_indices)}")
    return embeddings


def bulk_index(es: Elasticsearch, assets: list[dict], text_embeddings: list, image_embeddings: dict):
    """Bulk index all assets into Elasticsearch."""

    def generate_actions():
        for i, asset in enumerate(assets):
            doc = {
                "title": asset.get("title", ""),
                "description": asset.get("description", ""),
                "content_type": asset.get("content_type", ""),
                "tags": asset.get("tags", []),
                "category": asset.get("category", ""),
                "source": asset.get("source", ""),
                "author": asset.get("author", ""),
                "license": asset.get("license", ""),
                "url": asset.get("url", ""),
                "thumbnail_url": asset.get("thumbnail_url", ""),
                "preview_url": asset.get("preview_url", ""),
                "file_type": asset.get("file_type", ""),
                "created_at": asset.get("created_at"),
                "region": asset.get("region", ""),
                "geo_location": asset.get("geo_location"),
                "width": asset.get("width", 0),
                "height": asset.get("height", 0),
                "duration_seconds": asset.get("duration_seconds", 0),
                "view_count": asset.get("view_count", 0),
                "download_count": asset.get("download_count", 0),
                "text_embedding": text_embeddings[i],
            }

            # Add image embedding if available
            if i in image_embeddings:
                doc["image_embedding"] = image_embeddings[i]

            yield {
                "_index": settings.content_index,
                "_source": doc,
            }

    print(f"\nBulk indexing {len(assets)} documents into '{settings.content_index}'...")
    start = time.time()
    success, errors = bulk(es, generate_actions(), chunk_size=BATCH_SIZE, raise_on_error=False)
    elapsed = time.time() - start

    print(f"  Indexed: {success} documents in {elapsed:.1f}s")
    if errors:
        print(f"  Errors: {len(errors)}")
        for err in errors[:5]:
            print(f"    {err}")


def main():
    print("=" * 60)
    print("  CMS AI Search — Data Ingestion")
    print("=" * 60)

    # Load data
    assets = load_assets()

    # Generate embeddings
    text_embeddings = generate_text_embeddings(assets)
    image_embeddings = generate_image_embeddings(assets)

    # Index into Elasticsearch
    es = get_es_client()
    info = es.info()
    print(f"\nConnected to: {info['cluster_name']} (v{info['version']['number']})")

    bulk_index(es, assets, text_embeddings, image_embeddings)

    # Verify
    es.indices.refresh(index=settings.content_index)
    count = es.count(index=settings.content_index)["count"]
    print(f"\nFinal document count in '{settings.content_index}': {count}")
    print("Done!")


if __name__ == "__main__":
    main()
