"""
Creates all Elasticsearch indices for the CMS AI Search platform.

Usage:
    cd backend
    python -m scripts.setup_indices

Requires ELASTIC_CLOUD_ID and ELASTIC_API_KEY in .env
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from elasticsearch import Elasticsearch
from config import settings


def get_es_client() -> Elasticsearch:
    return Elasticsearch(
        cloud_id=settings.elastic_cloud_id,
        api_key=settings.elastic_api_key,
    )


# ── Main content index ──────────────────────────────────────────────
CMS_CONTENT_MAPPING = {
    "settings": {
        "number_of_shards": 2,
        "number_of_replicas": 1,
    },
    "mappings": {
        "properties": {
            # --- Text fields ---
            "title": {
                "type": "text",
                "analyzer": "english",
                "fields": {"raw": {"type": "keyword"}},
            },
            "description": {
                "type": "text",
                "analyzer": "english",
            },
            # --- Keyword / structured fields ---
            "content_type": {"type": "keyword"},  # image, video, audio, document, article, book, paper
            "tags": {"type": "keyword"},
            "category": {"type": "keyword"},
            "source": {"type": "keyword"},  # unsplash, pexels, pixabay, wikipedia, arxiv, gutenberg, archive
            "author": {"type": "keyword"},
            "license": {"type": "keyword"},
            "url": {"type": "keyword"},
            "thumbnail_url": {"type": "keyword"},
            "preview_url": {"type": "keyword"},
            "file_type": {"type": "keyword"},  # jpg, png, mp4, mp3, pdf, txt
            # --- Date ---
            "created_at": {"type": "date"},
            # --- Geo ---
            "region": {"type": "keyword"},
            "geo_location": {"type": "geo_point"},
            # --- Numeric ---
            "view_count": {"type": "integer"},
            "download_count": {"type": "integer"},
            "duration_seconds": {"type": "integer"},  # for video/audio
            "width": {"type": "integer"},
            "height": {"type": "integer"},
            # --- Vector embeddings ---
            "text_embedding": {
                "type": "dense_vector",
                "dims": settings.text_embedding_dims,
                "index": True,
                "similarity": "cosine",
            },
            "image_embedding": {
                "type": "dense_vector",
                "dims": settings.image_embedding_dims,
                "index": True,
                "similarity": "cosine",
            },
        }
    },
}

# ── Search logs ─────────────────────────────────────────────────────
SEARCH_LOGS_MAPPING = {
    "settings": {"number_of_shards": 1, "number_of_replicas": 1},
    "mappings": {
        "properties": {
            "query_text": {
                "type": "text",
                "fields": {"raw": {"type": "keyword"}},
            },
            "search_type": {"type": "keyword"},  # keyword, hybrid, image
            "result_count": {"type": "integer"},
            "response_time_ms": {"type": "integer"},
            "user_id": {"type": "keyword"},
            "session_id": {"type": "keyword"},
            "region": {"type": "keyword"},
            "geo": {"type": "geo_point"},
            "timestamp": {"type": "date"},
            "filters_used": {"type": "keyword"},  # which filters were active
        }
    },
}

# ── Click logs ──────────────────────────────────────────────────────
CLICK_LOGS_MAPPING = {
    "settings": {"number_of_shards": 1, "number_of_replicas": 1},
    "mappings": {
        "properties": {
            "content_id": {"type": "keyword"},
            "query_text": {
                "type": "text",
                "fields": {"raw": {"type": "keyword"}},
            },
            "position": {"type": "integer"},  # rank position when clicked
            "search_type": {"type": "keyword"},
            "user_id": {"type": "keyword"},
            "session_id": {"type": "keyword"},
            "region": {"type": "keyword"},
            "timestamp": {"type": "date"},
        }
    },
}

# ── Content views ───────────────────────────────────────────────────
CONTENT_VIEWS_MAPPING = {
    "settings": {"number_of_shards": 1, "number_of_replicas": 1},
    "mappings": {
        "properties": {
            "content_id": {"type": "keyword"},
            "content_type": {"type": "keyword"},
            "category": {"type": "keyword"},
            "user_id": {"type": "keyword"},
            "session_id": {"type": "keyword"},
            "region": {"type": "keyword"},
            "referrer": {"type": "keyword"},  # search, recommendation, direct
            "time_spent_seconds": {"type": "integer"},
            "timestamp": {"type": "date"},
        }
    },
}

INDICES = {
    settings.content_index: CMS_CONTENT_MAPPING,
    settings.search_logs_index: SEARCH_LOGS_MAPPING,
    settings.click_logs_index: CLICK_LOGS_MAPPING,
    settings.content_views_index: CONTENT_VIEWS_MAPPING,
}


def create_indices(es: Elasticsearch, delete_existing: bool = False):
    for index_name, body in INDICES.items():
        if es.indices.exists(index=index_name):
            if delete_existing:
                print(f"  Deleting existing index: {index_name}")
                es.indices.delete(index=index_name)
            else:
                print(f"  Index already exists: {index_name} (skipping)")
                continue

        es.indices.create(index=index_name, body=body)
        print(f"  Created index: {index_name}")


def main():
    print("Connecting to Elastic Cloud...")
    es = get_es_client()
    info = es.info()
    print(f"  Connected to cluster: {info['cluster_name']} (v{info['version']['number']})")

    delete_flag = "--delete" in sys.argv
    if delete_flag:
        print("\n⚠  --delete flag set: existing indices will be recreated!\n")

    print("Creating indices...")
    create_indices(es, delete_existing=delete_flag)

    print("\nIndex summary:")
    for index_name in INDICES:
        if es.indices.exists(index=index_name):
            count = es.count(index=index_name)["count"]
            print(f"  {index_name}: {count} documents")

    print("\nDone!")


if __name__ == "__main__":
    main()
