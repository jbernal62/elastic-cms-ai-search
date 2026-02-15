"""
Asset management endpoints — upload to GCS, list, and delete uploaded assets.
"""

import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from config import settings
from services.elasticsearch_service import delete_document, search_by_source

router = APIRouter(prefix="/api/assets", tags=["Assets"])


def _get_gcs_bucket():
    """Lazy import + bucket accessor to avoid errors when GCS is not configured."""
    if not settings.gcs_bucket_name:
        raise HTTPException(status_code=503, detail="GCS_BUCKET_NAME not configured")
    from google.cloud import storage
    client = storage.Client()
    return client.bucket(settings.gcs_bucket_name)


def _deterministic_id(bucket: str, name: str) -> str:
    return hashlib.sha256(f"{bucket}/{name}".encode()).hexdigest()[:20]


# ─── Upload ──────────────────────────────────────────────────────

@router.post("/upload")
async def upload_asset(
    file: UploadFile = File(...),
    folder: str = Query("uploads", description="Folder path inside the bucket"),
):
    """
    Upload a file to GCS. The Cloud Function will automatically
    pick up the finalize event, generate embeddings, and index it.
    """
    bucket = _get_gcs_bucket()

    # Sanitize folder path
    folder = folder.strip("/")
    object_name = f"{folder}/{file.filename}" if folder else file.filename

    # Upload to GCS
    blob = bucket.blob(object_name)
    content = await file.read()
    blob.upload_from_string(content, content_type=file.content_type)

    public_url = f"https://storage.googleapis.com/{settings.gcs_bucket_name}/{object_name}"
    doc_id = _deterministic_id(settings.gcs_bucket_name, object_name)

    return {
        "status": "uploaded",
        "file": file.filename,
        "gcs_path": f"gs://{settings.gcs_bucket_name}/{object_name}",
        "public_url": public_url,
        "doc_id": doc_id,
        "message": "File uploaded. Embedding and indexing will happen automatically via Cloud Function.",
    }


# ─── List uploaded assets ────────────────────────────────────────

@router.get("")
async def list_assets(
    size: int = Query(100, ge=1, le=500),
):
    """List all assets uploaded via GCS (source='gcs-upload')."""
    response = search_by_source("gcs-upload", size=size)
    results = [
        {"id": hit["_id"], **hit["_source"]}
        for hit in response.get("hits", {}).get("hits", [])
    ]
    return {
        "total": response["hits"]["total"]["value"],
        "assets": results,
    }


# ─── Delete ──────────────────────────────────────────────────────

@router.delete("/{doc_id}")
async def delete_asset(doc_id: str):
    """
    Delete an uploaded asset from Elasticsearch and optionally from GCS.
    """
    from services.elasticsearch_service import get_es_client

    es = get_es_client()

    # Get the document first to find GCS path
    try:
        doc = es.get(index=settings.content_index, id=doc_id, source_includes=["gcs_bucket", "gcs_object", "source"])
        source = doc["_source"]
    except Exception:
        raise HTTPException(status_code=404, detail="Asset not found")

    if source.get("source") != "gcs-upload":
        raise HTTPException(status_code=400, detail="Can only delete GCS-uploaded assets")

    # Delete from GCS if bucket info is available
    gcs_bucket = source.get("gcs_bucket")
    gcs_object = source.get("gcs_object")
    if gcs_bucket and gcs_object:
        try:
            bucket = _get_gcs_bucket()
            blob = bucket.blob(gcs_object)
            blob.delete()
        except Exception as e:
            pass  # GCS deletion is best-effort; ES deletion is the priority

    # Delete from Elasticsearch
    delete_document(doc_id)

    return {"status": "deleted", "doc_id": doc_id}
