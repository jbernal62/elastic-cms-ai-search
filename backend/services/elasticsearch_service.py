"""
Elasticsearch service — handles all ES queries for search, content, and analytics.
"""

from functools import lru_cache

from elasticsearch import Elasticsearch

from config import settings


@lru_cache(maxsize=1)
def get_es_client() -> Elasticsearch:
    return Elasticsearch(
        cloud_id=settings.elastic_cloud_id,
        api_key=settings.elastic_api_key,
    )


# ═══════════════════════════════════════════════════════════════════
#  SEARCH
# ═══════════════════════════════════════════════════════════════════

def hybrid_search(
    query: str,
    text_embedding: list[float],
    content_type: str | None = None,
    category: str | None = None,
    region: str | None = None,
    size: int = 20,
) -> dict:
    """BM25 + kNN hybrid search."""
    filters = _build_filters(content_type, category, region)

    body = {
        "size": size,
        "query": {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": query,
                            "fields": ["title^3", "description^2", "tags^2"],
                            "type": "best_fields",
                        }
                    }
                ],
                "filter": filters,
            }
        },
        "knn": {
            "field": "text_embedding",
            "query_vector": text_embedding,
            "k": size,
            "num_candidates": max(size * 5, 100),
        },
        "_source": {"excludes": ["text_embedding", "image_embedding"]},
    }

    # Apply filter to kNN retriever
    if filters:
        body["knn"]["filter"] = {"bool": {"filter": filters}}

    es = get_es_client()
    return es.search(index=settings.content_index, body=body)


def keyword_search(
    query: str,
    content_type: str | None = None,
    category: str | None = None,
    region: str | None = None,
    size: int = 20,
) -> dict:
    """Traditional BM25 keyword search."""
    filters = _build_filters(content_type, category, region)

    body = {
        "size": size,
        "query": {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": query,
                            "fields": ["title^3", "description^2", "tags^2"],
                            "type": "best_fields",
                        }
                    }
                ],
                "filter": filters,
            }
        },
        "_source": {"excludes": ["text_embedding", "image_embedding"]},
    }

    es = get_es_client()
    return es.search(index=settings.content_index, body=body)


def image_similarity_search(
    image_embedding: list[float],
    content_type: str | None = None,
    size: int = 20,
) -> dict:
    """kNN search using CLIP image embedding."""
    filters = _build_filters(content_type)

    body = {
        "size": size,
        "knn": {
            "field": "image_embedding",
            "query_vector": image_embedding,
            "k": size,
            "num_candidates": max(size * 5, 100),
        },
        "_source": {"excludes": ["text_embedding", "image_embedding"]},
    }

    if filters:
        body["knn"]["filter"] = {"bool": {"filter": filters}}

    es = get_es_client()
    return es.search(index=settings.content_index, body=body)


def text_to_image_search(
    clip_text_embedding: list[float],
    size: int = 20,
) -> dict:
    """Search images using text encoded with CLIP (cross-modal)."""
    body = {
        "size": size,
        "knn": {
            "field": "image_embedding",
            "query_vector": clip_text_embedding,
            "k": size,
            "num_candidates": max(size * 5, 100),
            "filter": {"term": {"content_type": "image"}},
        },
        "_source": {"excludes": ["text_embedding", "image_embedding"]},
    }

    es = get_es_client()
    return es.search(index=settings.content_index, body=body)


# ═══════════════════════════════════════════════════════════════════
#  CONTENT & RECOMMENDATIONS
# ═══════════════════════════════════════════════════════════════════

def get_content_by_id(doc_id: str) -> dict | None:
    es = get_es_client()
    try:
        result = es.get(
            index=settings.content_index,
            id=doc_id,
            source_excludes=["text_embedding", "image_embedding"],
        )
        return {"id": result["_id"], **result["_source"]}
    except Exception:
        return None


def get_related_content(doc_id: str, size: int = 6) -> dict:
    """More Like This query for related content."""
    body = {
        "size": size,
        "query": {
            "more_like_this": {
                "fields": ["title", "description", "tags"],
                "like": [{"_index": settings.content_index, "_id": doc_id}],
                "min_term_freq": 1,
                "max_query_terms": 25,
            }
        },
        "_source": {"excludes": ["text_embedding", "image_embedding"]},
    }

    es = get_es_client()
    return es.search(index=settings.content_index, body=body)


def get_recommended_content(text_embedding: list[float], exclude_id: str, size: int = 6) -> dict:
    """kNN-based recommendations using the current document's embedding."""
    body = {
        "size": size,
        "knn": {
            "field": "text_embedding",
            "query_vector": text_embedding,
            "k": size + 1,
            "num_candidates": 50,
            "filter": {
                "bool": {
                    "must_not": {"ids": {"values": [exclude_id]}},
                }
            },
        },
        "_source": {"excludes": ["text_embedding", "image_embedding"]},
    }

    es = get_es_client()
    return es.search(index=settings.content_index, body=body)


def get_content_embedding(doc_id: str) -> list[float] | None:
    """Retrieve the text_embedding for a document (for recommendations)."""
    es = get_es_client()
    try:
        result = es.get(index=settings.content_index, id=doc_id, source_includes=["text_embedding"])
        return result["_source"].get("text_embedding")
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════
#  ANALYTICS QUERIES
# ═══════════════════════════════════════════════════════════════════

def get_top_content(size: int = 20) -> dict:
    body = {
        "size": size,
        "sort": [{"view_count": {"order": "desc"}}],
        "_source": ["title", "content_type", "category", "thumbnail_url", "view_count", "download_count"],
    }
    es = get_es_client()
    return es.search(index=settings.content_index, body=body)


def get_search_hit_rate(interval: str = "day", days: int = 90) -> dict:
    body = {
        "size": 0,
        "query": {"range": {"timestamp": {"gte": f"now-{days}d/d"}}},
        "aggs": {
            "over_time": {
                "date_histogram": {"field": "timestamp", "calendar_interval": interval},
                "aggs": {
                    "total": {"value_count": {"field": "query_text.raw"}},
                    "zero_hits": {"filter": {"term": {"result_count": 0}}},
                    "hit_rate": {
                        "bucket_script": {
                            "buckets_path": {"total": "total", "zeros": "zero_hits._count"},
                            "script": "params.total > 0 ? ((params.total - params.zeros) / params.total) * 100 : 0",
                        }
                    },
                },
            }
        },
    }
    es = get_es_client()
    return es.search(index=settings.search_logs_index, body=body)


def get_zero_result_queries(size: int = 50) -> dict:
    body = {
        "size": 0,
        "query": {"term": {"result_count": 0}},
        "aggs": {
            "failed_queries": {
                "terms": {"field": "query_text.raw", "size": size},
                "aggs": {
                    "latest": {"max": {"field": "timestamp"}},
                },
            }
        },
    }
    es = get_es_client()
    return es.search(index=settings.search_logs_index, body=body)


def get_geo_distribution(size: int = 30) -> dict:
    body = {
        "size": 0,
        "aggs": {
            "regions": {
                "terms": {"field": "region", "size": size},
                "aggs": {
                    "top_queries": {"terms": {"field": "query_text.raw", "size": 5}},
                    "search_count": {"value_count": {"field": "query_text.raw"}},
                },
            }
        },
    }
    es = get_es_client()
    return es.search(index=settings.search_logs_index, body=body)


def get_engagement_trends(interval: str = "week", days: int = 90) -> dict:
    body = {
        "size": 0,
        "query": {"range": {"timestamp": {"gte": f"now-{days}d/d"}}},
        "aggs": {
            "by_category": {
                "terms": {"field": "category", "size": 10},
                "aggs": {
                    "trend": {
                        "date_histogram": {"field": "timestamp", "calendar_interval": interval},
                        "aggs": {
                            "views": {"value_count": {"field": "content_id"}},
                        },
                    }
                },
            }
        },
    }
    es = get_es_client()
    return es.search(index=settings.content_views_index, body=body)


def get_content_type_breakdown() -> dict:
    body = {
        "size": 0,
        "aggs": {
            "by_type": {
                "terms": {"field": "content_type", "size": 20},
                "aggs": {
                    "total_views": {"sum": {"field": "view_count"}},
                },
            }
        },
    }
    es = get_es_client()
    return es.search(index=settings.content_index, body=body)


def get_dashboard_kpis() -> dict:
    """Get high-level KPIs for the dashboard header."""
    es = get_es_client()

    total_assets = es.count(index=settings.content_index)["count"]
    total_searches = es.count(index=settings.search_logs_index)["count"]

    # Average hit rate
    hit_rate_body = {
        "size": 0,
        "aggs": {
            "total": {"value_count": {"field": "query_text.raw"}},
            "zero_hits": {"filter": {"term": {"result_count": 0}}},
        },
    }
    hit_rate_resp = es.search(index=settings.search_logs_index, body=hit_rate_body)
    total = hit_rate_resp["aggregations"]["total"]["value"]
    zeros = hit_rate_resp["aggregations"]["zero_hits"]["doc_count"]
    avg_hit_rate = ((total - zeros) / total * 100) if total > 0 else 0

    # Top category
    top_cat_body = {
        "size": 0,
        "aggs": {"top_cat": {"terms": {"field": "category", "size": 1}}},
    }
    top_cat_resp = es.search(index=settings.content_views_index, body=top_cat_body)
    top_cat_buckets = top_cat_resp["aggregations"]["top_cat"]["buckets"]
    top_category = top_cat_buckets[0]["key"] if top_cat_buckets else "N/A"

    return {
        "total_assets": total_assets,
        "total_searches": total_searches,
        "avg_hit_rate": round(avg_hit_rate, 1),
        "top_category": top_category,
    }


# ═══════════════════════════════════════════════════════════════════
#  ANALYTICS LOGGING
# ═══════════════════════════════════════════════════════════════════

def log_search_event(event: dict):
    es = get_es_client()
    es.index(index=settings.search_logs_index, document=event)


def log_click_event(event: dict):
    es = get_es_client()
    es.index(index=settings.click_logs_index, document=event)


def log_view_event(event: dict):
    es = get_es_client()
    es.index(index=settings.content_views_index, document=event)


# ═══════════════════════════════════════════════════════════════════
#  ASSETS (GCS uploads)
# ═══════════════════════════════════════════════════════════════════

def search_by_source(source: str, size: int = 100) -> dict:
    """Return all documents from a given source (e.g. 'gcs-upload')."""
    body = {
        "size": size,
        "query": {"term": {"source": source}},
        "sort": [{"created_at": {"order": "desc"}}],
        "_source": {"excludes": ["text_embedding", "image_embedding"]},
    }
    es = get_es_client()
    return es.search(index=settings.content_index, body=body)


def delete_document(doc_id: str):
    """Delete a document from the content index."""
    es = get_es_client()
    es.delete(index=settings.content_index, id=doc_id)


# ═══════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════

def _build_filters(
    content_type: str | None = None,
    category: str | None = None,
    region: str | None = None,
) -> list[dict]:
    filters = []
    if content_type:
        filters.append({"term": {"content_type": content_type}})
    if category:
        filters.append({"term": {"category": category}})
    if region:
        filters.append({"term": {"region": region}})
    return filters
