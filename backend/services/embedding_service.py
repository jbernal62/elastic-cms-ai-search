"""
Thin wrapper around embedding models for use by routers.
Keeps router code clean by centralizing embedding logic.
"""

from models.embeddings import (
    embed_text,
    embed_image_from_bytes,
    embed_text_for_image_search,
)


def get_search_embedding(query: str) -> list[float]:
    """Get text embedding for hybrid search."""
    return embed_text(query)


def get_image_search_embedding(image_bytes: bytes) -> list[float]:
    """Get CLIP embedding from uploaded image."""
    return embed_image_from_bytes(image_bytes)


def get_text_to_image_embedding(query: str) -> list[float]:
    """Get CLIP text embedding for cross-modal image search."""
    return embed_text_for_image_search(query)
