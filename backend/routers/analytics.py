"""
Analytics API endpoints — dashboard data, search metrics, engagement trends.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Query
from pydantic import BaseModel

from services.elasticsearch_service import (
    get_content_type_breakdown,
    get_dashboard_kpis,
    get_engagement_trends,
    get_geo_distribution,
    get_search_hit_rate,
    get_top_content,
    get_zero_result_queries,
    log_click_event,
    log_search_event,
)

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


# ─── Dashboard KPIs ───────────────────────────────────────────────
@router.get("/kpis")
async def dashboard_kpis():
    """Top-level KPI cards: total assets, total searches, hit rate, top category."""
    return get_dashboard_kpis()


# ─── Most viewed content ──────────────────────────────────────────
@router.get("/top-content")
async def top_content(size: int = Query(20, ge=1, le=50)):
    """Most viewed content items, sorted by view_count."""
    response = get_top_content(size)
    return [
        {"id": hit["_id"], **hit["_source"]}
        for hit in response["hits"]["hits"]
    ]


# ─── Search hit rate over time ────────────────────────────────────
@router.get("/search-hit-rate")
async def search_hit_rate(
    interval: str = Query("day", regex="^(day|week|month)$"),
    days: int = Query(90, ge=7, le=365),
):
    """Search success rate over time (percentage of searches with results)."""
    response = get_search_hit_rate(interval, days)
    buckets = response["aggregations"]["over_time"]["buckets"]
    return [
        {
            "date": b["key_as_string"],
            "total_searches": b["total"]["value"],
            "zero_result_searches": b["zero_hits"]["doc_count"],
            "hit_rate": round(b["hit_rate"]["value"], 1) if "hit_rate" in b else 0,
        }
        for b in buckets
    ]


# ─── Zero-result queries ──────────────────────────────────────────
@router.get("/zero-results")
async def zero_result_queries(size: int = Query(50, ge=1, le=200)):
    """Queries that returned no results — content gap opportunities."""
    response = get_zero_result_queries(size)
    buckets = response["aggregations"]["failed_queries"]["buckets"]
    return [
        {
            "query": b["key"],
            "count": b["doc_count"],
            "last_seen": b["latest"]["value_as_string"] if b["latest"]["value"] else None,
        }
        for b in buckets
    ]


# ─── Geographic distribution ──────────────────────────────────────
@router.get("/geo-distribution")
async def geo_distribution(size: int = Query(30, ge=1, le=50)):
    """Search activity by region with top queries per region."""
    response = get_geo_distribution(size)
    buckets = response["aggregations"]["regions"]["buckets"]
    return [
        {
            "region": b["key"],
            "search_count": b["search_count"]["value"],
            "top_queries": [q["key"] for q in b["top_queries"]["buckets"]],
        }
        for b in buckets
    ]


# ─── Engagement trends by category ────────────────────────────────
@router.get("/engagement-trends")
async def engagement_trends(
    interval: str = Query("week", regex="^(day|week|month)$"),
    days: int = Query(90, ge=7, le=365),
):
    """Content engagement (views) over time, broken down by category."""
    response = get_engagement_trends(interval, days)
    categories = response["aggregations"]["by_category"]["buckets"]
    return [
        {
            "category": cat["key"],
            "trend": [
                {
                    "date": point["key_as_string"],
                    "views": point["views"]["value"],
                }
                for point in cat["trend"]["buckets"]
            ],
        }
        for cat in categories
    ]


# ─── Content type breakdown ───────────────────────────────────────
@router.get("/content-type-breakdown")
async def content_type_breakdown():
    """Distribution of content by type with total views."""
    response = get_content_type_breakdown()
    buckets = response["aggregations"]["by_type"]["buckets"]
    return [
        {
            "content_type": b["key"],
            "count": b["doc_count"],
            "total_views": b["total_views"]["value"],
        }
        for b in buckets
    ]


# ─── Event logging endpoints (called by frontend) ─────────────────
class SearchLogEvent(BaseModel):
    query_text: str
    search_type: str
    result_count: int
    response_time_ms: int = 0
    region: str = "North America"


class ClickLogEvent(BaseModel):
    content_id: str
    query_text: str = ""
    position: int = 0
    search_type: str = "hybrid"
    region: str = "North America"


@router.post("/log-search")
async def log_search(event: SearchLogEvent):
    """Log a search event for analytics."""
    log_search_event({
        **event.model_dump(),
        "user_id": "demo-user",
        "session_id": "demo-session",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return {"status": "ok"}


@router.post("/log-click")
async def log_click(event: ClickLogEvent):
    """Log a click/interaction event."""
    log_click_event({
        **event.model_dump(),
        "user_id": "demo-user",
        "session_id": "demo-session",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return {"status": "ok"}
