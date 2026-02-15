"""
Content API endpoints — single content view, related content, recommendations.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from services.elasticsearch_service import (
    get_content_by_id,
    get_content_embedding,
    get_recommended_content,
    get_related_content,
    log_view_event,
)

router = APIRouter(prefix="/api/content", tags=["Content"])


def _format_hits(response: dict) -> list[dict]:
    return [
        {"id": hit["_id"], "score": hit.get("_score"), **hit["_source"]}
        for hit in response.get("hits", {}).get("hits", [])
    ]


@router.get("/{doc_id}")
async def get_content(doc_id: str):
    """Get a single content item by ID."""
    content = get_content_by_id(doc_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    # Log view event
    try:
        log_view_event({
            "content_id": doc_id,
            "content_type": content.get("content_type", ""),
            "category": content.get("category", ""),
            "user_id": "demo-user",
            "session_id": str(uuid.uuid4())[:8],
            "region": "North America",
            "referrer": "direct",
            "time_spent_seconds": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        pass

    return content


@router.get("/{doc_id}/related")
async def related_content(
    doc_id: str,
    size: int = Query(6, ge=1, le=20),
):
    """Get related content using More Like This."""
    response = get_related_content(doc_id, size)
    return {
        "source_id": doc_id,
        "method": "more_like_this",
        "results": _format_hits(response),
    }


@router.get("/{doc_id}/recommendations")
async def recommended_content(
    doc_id: str,
    size: int = Query(6, ge=1, le=20),
):
    """Get recommended content using vector similarity (kNN)."""
    embedding = get_content_embedding(doc_id)
    if not embedding:
        raise HTTPException(status_code=404, detail="Content embedding not found")

    response = get_recommended_content(embedding, doc_id, size)
    return {
        "source_id": doc_id,
        "method": "vector_knn",
        "results": _format_hits(response),
    }
