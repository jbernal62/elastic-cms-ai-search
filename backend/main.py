"""
CMS AI Search Platform — FastAPI Application

Start with:
    cd backend
    uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routers import analytics, assets, content, search

app = FastAPI(
    title="CMS AI-Powered Content Discovery",
    description="Elasticsearch-powered semantic search, image similarity, and content analytics",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router)
app.include_router(content.router)
app.include_router(analytics.router)
app.include_router(assets.router)


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    from services.elasticsearch_service import get_es_client
    try:
        es = get_es_client()
        info = es.info()
        return {
            "status": "healthy",
            "elasticsearch": {
                "cluster": info["cluster_name"],
                "version": info["version"]["number"],
            },
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
