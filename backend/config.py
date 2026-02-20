"""
Configuration for Elastic Cloud and application settings.

Set these environment variables before running:
  ELASTIC_CLOUD_ID=your-deployment:base64...
  ELASTIC_API_KEY=your-api-key

Or create a .env file in the backend/ directory.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # -- Elastic Cloud --
    elastic_cloud_id: str = ""
    elastic_api_key: str = ""

    # -- Index names --
    content_index: str = "cms-content"
    search_logs_index: str = "cms-search-logs"
    click_logs_index: str = "cms-click-logs"
    content_views_index: str = "cms-content-views"

    # -- Embedding models --
    text_model_name: str = "all-MiniLM-L6-v2"
    clip_model_name: str = "clip-ViT-B-32"
    text_embedding_dims: int = 384
    image_embedding_dims: int = 512

    # -- API keys for data sources (optional — scripts work with free tiers) --
    unsplash_access_key: str = ""
    pexels_api_key: str = ""
    freesound_api_key: str = ""

    # -- GCS asset storage --
    gcs_bucket_name: str = ""

    # -- App settings --
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
