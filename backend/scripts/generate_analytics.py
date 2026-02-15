"""
Generates realistic simulated analytics data for the dashboard demo.

Usage:
    cd backend
    python -m scripts.generate_analytics

Creates ~10,000 search logs, ~5,000 click logs, and ~8,000 view events
spread over the last 90 days with realistic patterns.
"""

import os
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

from config import settings

# ── Realistic search queries ────────────────────────────────────────

POPULAR_QUERIES = [
    "sunset landscape", "business meeting", "modern architecture",
    "healthy food recipes", "ocean wildlife", "space exploration",
    "artificial intelligence", "mountain hiking", "city nightlife",
    "tropical beach", "vintage photography", "forest animals",
    "abstract art", "renewable energy", "classical music",
    "fitness workout", "luxury travel", "street fashion",
    "underwater photography", "startup technology",
    "machine learning tutorial", "climate change research",
    "quantum physics", "digital marketing", "sustainable design",
    "world cuisine", "ancient history", "sports highlights",
    "meditation nature sounds", "cybersecurity fundamentals",
]

ZERO_RESULT_QUERIES = [
    "flying car prototype 2025", "mars colonization updates",
    "holographic display technology", "quantum internet setup",
    "neural interface headset", "anti-gravity experiment",
    "time travel theory proof", "teleportation breakthrough",
    "underwater city blueprints", "invisibility cloak material",
    "dinosaur DNA cloning", "perpetual motion machine",
    "alien signal decoded", "dark matter collector",
    "warp drive engineering", "consciousness upload guide",
]

CATEGORIES = [
    "nature", "technology", "business", "health", "travel",
    "food", "science", "art", "music", "sports",
    "architecture", "animals", "ocean", "space", "education",
]

REGIONS = ["North America", "South America", "Europe", "Asia", "Africa", "Oceania", "Middle East"]
REGION_WEIGHTS = [0.28, 0.10, 0.25, 0.20, 0.06, 0.05, 0.06]

GEO_POINTS = {
    "North America": {"lat": 39.8, "lon": -98.5},
    "South America": {"lat": -14.2, "lon": -51.9},
    "Europe": {"lat": 50.1, "lon": 9.2},
    "Asia": {"lat": 34.0, "lon": 100.6},
    "Africa": {"lat": 1.6, "lon": 28.0},
    "Oceania": {"lat": -25.3, "lon": 133.8},
    "Middle East": {"lat": 29.3, "lon": 47.5},
}

SEARCH_TYPES = ["hybrid", "keyword", "image"]
SEARCH_TYPE_WEIGHTS = [0.55, 0.35, 0.10]

REFERRERS = ["search", "recommendation", "direct", "external"]
REFERRER_WEIGHTS = [0.45, 0.25, 0.20, 0.10]


def random_timestamp(days_ago_max: int = 90) -> str:
    now = datetime.now(timezone.utc)
    delta = timedelta(
        days=random.randint(0, days_ago_max),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
        seconds=random.randint(0, 59),
    )
    return (now - delta).isoformat()


def get_es_client() -> Elasticsearch:
    return Elasticsearch(
        cloud_id=settings.elastic_cloud_id,
        api_key=settings.elastic_api_key,
    )


def get_content_ids(es: Elasticsearch, sample_size: int = 200) -> list[str]:
    """Fetch some real content IDs from the content index."""
    resp = es.search(
        index=settings.content_index,
        body={"size": sample_size, "_source": False},
    )
    return [hit["_id"] for hit in resp["hits"]["hits"]]


def generate_search_logs(count: int = 10000) -> list[dict]:
    """Generate realistic search log entries."""
    logs = []
    for _ in range(count):
        is_zero_result = random.random() < 0.15  # 15% zero-result rate
        if is_zero_result:
            query = random.choice(ZERO_RESULT_QUERIES)
            result_count = 0
        else:
            query = random.choice(POPULAR_QUERIES)
            result_count = random.randint(1, 50)

        region = random.choices(REGIONS, weights=REGION_WEIGHTS, k=1)[0]
        search_type = random.choices(SEARCH_TYPES, weights=SEARCH_TYPE_WEIGHTS, k=1)[0]

        logs.append({
            "_index": settings.search_logs_index,
            "_source": {
                "query_text": query,
                "search_type": search_type,
                "result_count": result_count,
                "response_time_ms": random.randint(50, 800),
                "user_id": f"user-{random.randint(1, 500)}",
                "session_id": str(uuid.uuid4())[:8],
                "region": region,
                "geo": GEO_POINTS[region],
                "timestamp": random_timestamp(),
                "filters_used": random.choice(["none", "content_type", "category", "region"]),
            },
        })
    return logs


def generate_click_logs(content_ids: list[str], count: int = 5000) -> list[dict]:
    """Generate click log entries tied to search sessions."""
    logs = []
    for _ in range(count):
        region = random.choices(REGIONS, weights=REGION_WEIGHTS, k=1)[0]
        logs.append({
            "_index": settings.click_logs_index,
            "_source": {
                "content_id": random.choice(content_ids),
                "query_text": random.choice(POPULAR_QUERIES),
                "position": random.randint(1, 20),
                "search_type": random.choices(SEARCH_TYPES, weights=SEARCH_TYPE_WEIGHTS, k=1)[0],
                "user_id": f"user-{random.randint(1, 500)}",
                "session_id": str(uuid.uuid4())[:8],
                "region": region,
                "timestamp": random_timestamp(),
            },
        })
    return logs


def generate_view_logs(content_ids: list[str], count: int = 8000) -> list[dict]:
    """Generate content view events with power-law distribution."""
    # Make some content much more popular
    popular_ids = content_ids[: len(content_ids) // 5]  # top 20% get more views
    rest_ids = content_ids[len(content_ids) // 5 :]

    logs = []
    for _ in range(count):
        # 60% of views go to the top 20% of content (power law)
        if random.random() < 0.6 and popular_ids:
            content_id = random.choice(popular_ids)
        elif rest_ids:
            content_id = random.choice(rest_ids)
        else:
            content_id = random.choice(content_ids)

        region = random.choices(REGIONS, weights=REGION_WEIGHTS, k=1)[0]
        referrer = random.choices(REFERRERS, weights=REFERRER_WEIGHTS, k=1)[0]

        logs.append({
            "_index": settings.content_views_index,
            "_source": {
                "content_id": content_id,
                "content_type": random.choice(["image", "video", "audio", "article", "paper", "book"]),
                "category": random.choice(CATEGORIES),
                "user_id": f"user-{random.randint(1, 500)}",
                "session_id": str(uuid.uuid4())[:8],
                "region": region,
                "referrer": referrer,
                "time_spent_seconds": random.randint(5, 300),
                "timestamp": random_timestamp(),
            },
        })
    return logs


def main():
    print("=" * 60)
    print("  CMS AI Search — Analytics Data Generator")
    print("=" * 60)

    es = get_es_client()
    info = es.info()
    print(f"Connected to: {info['cluster_name']} (v{info['version']['number']})")

    # Get real content IDs
    print("\nFetching content IDs...")
    content_ids = get_content_ids(es)
    print(f"  Found {len(content_ids)} content items")

    if not content_ids:
        print("  WARNING: No content found! Run ingest_data.py first.")
        print("  Generating analytics with fake content IDs...")
        content_ids = [f"fake-{i}" for i in range(200)]

    # Generate search logs
    print("\nGenerating search logs (10,000)...")
    search_logs = generate_search_logs(10000)
    success, errors = bulk(es, search_logs, chunk_size=500, raise_on_error=False)
    print(f"  Indexed: {success} search logs")

    # Generate click logs
    print("Generating click logs (5,000)...")
    click_logs = generate_click_logs(content_ids, 5000)
    success, errors = bulk(es, click_logs, chunk_size=500, raise_on_error=False)
    print(f"  Indexed: {success} click logs")

    # Generate view logs
    print("Generating view logs (8,000)...")
    view_logs = generate_view_logs(content_ids, 8000)
    success, errors = bulk(es, view_logs, chunk_size=500, raise_on_error=False)
    print(f"  Indexed: {success} view logs")

    # Refresh indices
    for idx in [settings.search_logs_index, settings.click_logs_index, settings.content_views_index]:
        es.indices.refresh(index=idx)

    # Summary
    print("\nFinal counts:")
    for idx in [settings.search_logs_index, settings.click_logs_index, settings.content_views_index]:
        count = es.count(index=idx)["count"]
        print(f"  {idx}: {count} documents")

    print("\nDone! Dashboard data is ready.")


if __name__ == "__main__":
    main()
