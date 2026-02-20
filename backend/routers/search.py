"""
Search API endpoints — natural language, image, keyword, and comparison.
"""

import time
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, File, Query, UploadFile

from services.elasticsearch_service import (
    hybrid_search,
    image_similarity_search,
    keyword_search,
    log_search_event,
    text_to_image_search,
)
from services.embedding_service import (
    get_image_search_embedding,
    get_search_embedding,
    get_text_to_image_embedding,
)

router = APIRouter(prefix="/api/search", tags=["Search"])


def _format_hits(response: dict) -> list[dict]:
    """Extract and format hits from ES response."""
    return [
        {"id": hit["_id"], "score": hit.get("_score"), **hit["_source"]}
        for hit in response.get("hits", {}).get("hits", [])
    ]


def _log(query: str, search_type: str, result_count: int, response_time_ms: int):
    """Fire-and-forget search log."""
    try:
        log_search_event({
            "query_text": query,
            "search_type": search_type,
            "result_count": result_count,
            "response_time_ms": response_time_ms,
            "user_id": "demo-user",
            "session_id": str(uuid.uuid4())[:8],
            "region": "North America",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        pass  # analytics logging should never break search


# ─── Natural language hybrid search ────────────────────────────────
@router.get("")
async def search(
    q: str = Query(..., min_length=1, description="Search query"),
    content_type: str | None = Query(None),
    category: str | None = Query(None),
    region: str | None = Query(None),
    size: int = Query(20, ge=1, le=100),
):
    """
    Hybrid search combining BM25 keyword matching with semantic vector search.
    """
    start = time.time()
    print(f"[SEARCH] q={q!r} content_type={content_type!r} category={category!r} region={region!r}")
    embedding = get_search_embedding(q)
    response = hybrid_search(q, embedding, content_type, category, region, size)
    elapsed_ms = int((time.time() - start) * 1000)

    results = _format_hits(response)
    _log(q, "hybrid", len(results), elapsed_ms)

    return {
        "query": q,
        "search_type": "hybrid",
        "total": response["hits"]["total"]["value"],
        "response_time_ms": elapsed_ms,
        "results": results,
    }


# ─── Keyword-only search ──────────────────────────────────────────
@router.get("/keyword")
async def search_keyword(
    q: str = Query(..., min_length=1),
    content_type: str | None = Query(None),
    category: str | None = Query(None),
    region: str | None = Query(None),
    size: int = Query(20, ge=1, le=100),
):
    """Traditional BM25 keyword search (no vectors)."""
    start = time.time()
    response = keyword_search(q, content_type, category, region, size)
    elapsed_ms = int((time.time() - start) * 1000)

    results = _format_hits(response)
    _log(q, "keyword", len(results), elapsed_ms)

    return {
        "query": q,
        "search_type": "keyword",
        "total": response["hits"]["total"]["value"],
        "response_time_ms": elapsed_ms,
        "results": results,
    }


# ─── Image similarity search ──────────────────────────────────────
@router.post("/image")
async def search_by_image(
    file: UploadFile = File(...),
    content_type: str | None = Query(None),
    size: int = Query(20, ge=1, le=100),
):
    """Upload an image and find visually similar content using CLIP embeddings."""
    start = time.time()
    image_bytes = await file.read()
    embedding = get_image_search_embedding(image_bytes)
    response = image_similarity_search(embedding, content_type, size)
    elapsed_ms = int((time.time() - start) * 1000)

    results = _format_hits(response)
    _log(f"[image upload: {file.filename}]", "image", len(results), elapsed_ms)

    return {
        "query": f"Image: {file.filename}",
        "search_type": "image_similarity",
        "total": response["hits"]["total"]["value"],
        "response_time_ms": elapsed_ms,
        "results": results,
    }


# ─── Text-to-image search ─────────────────────────────────────────
@router.get("/text-to-image")
async def search_text_to_image(
    q: str = Query(..., min_length=1),
    size: int = Query(20, ge=1, le=100),
):
    """Search for images using a text description (cross-modal CLIP search)."""
    start = time.time()
    clip_embedding = get_text_to_image_embedding(q)
    response = text_to_image_search(clip_embedding, size)
    elapsed_ms = int((time.time() - start) * 1000)

    results = _format_hits(response)
    return {
        "query": q,
        "search_type": "text_to_image",
        "total": response["hits"]["total"]["value"],
        "response_time_ms": elapsed_ms,
        "results": results,
    }


# ─── Side-by-side comparison ──────────────────────────────────────
@router.get("/compare")
async def compare_search(
    q: str = Query(..., min_length=1),
    content_type: str | None = Query(None),
    category: str | None = Query(None),
    size: int = Query(20, ge=1, le=100),
):
    """
    Returns both keyword and hybrid results for the same query,
    enabling side-by-side comparison in the UI.
    """
    start = time.time()
    embedding = get_search_embedding(q)

    kw_response = keyword_search(q, content_type, category, size=size)
    hybrid_response = hybrid_search(q, embedding, content_type, category, size=size)

    elapsed_ms = int((time.time() - start) * 1000)

    kw_results = _format_hits(kw_response)
    hybrid_results = _format_hits(hybrid_response)

    # Find IDs unique to hybrid (semantic wins)
    kw_ids = {r["id"] for r in kw_results}
    hybrid_only_ids = [r["id"] for r in hybrid_results if r["id"] not in kw_ids]

    return {
        "query": q,
        "response_time_ms": elapsed_ms,
        "keyword": {
            "total": kw_response["hits"]["total"]["value"],
            "results": kw_results,
        },
        "hybrid": {
            "total": hybrid_response["hits"]["total"]["value"],
            "results": hybrid_results,
        },
        "hybrid_only_ids": hybrid_only_ids,
    }
