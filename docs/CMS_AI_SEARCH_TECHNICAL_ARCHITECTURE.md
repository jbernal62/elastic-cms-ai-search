# CMS AI-Powered Content Discovery Platform — Technical Architecture Document

> **Version**: 1.0
> **Date**: February 2025
> **Audience**: Solutions Architects, Elasticsearch Engineers, ML Engineers
> **Scope**: Full platform architecture, Elasticsearch internals, embedding pipeline, search mechanics, and infrastructure design

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Embedding Pipeline Deep Dive](#3-embedding-pipeline-deep-dive)
   - 3.1 [Models Used and Why](#31-models-used-and-why)
   - 3.2 [Why App-Side Inference Instead of Elasticsearch Inference Endpoints](#32-why-app-side-inference-instead-of-elasticsearch-inference-endpoints)
   - 3.3 [Text Embedding Generation](#33-text-embedding-generation)
   - 3.4 [Image Embedding Generation (CLIP)](#34-image-embedding-generation-clip)
   - 3.5 [Cross-Modal Embedding (Text-to-Image)](#35-cross-modal-embedding-text-to-image)
   - 3.6 [Model Loading and Caching Strategy](#36-model-loading-and-caching-strategy)
4. [Chunk Configuration and Model Limits](#4-chunk-configuration-and-model-limits)
   - 4.1 [Current Chunking Strategy](#41-current-chunking-strategy)
   - 4.2 [Model Token/Character Limits](#42-model-tokencharacter-limits)
   - 4.3 [Why Not RAG-Style Chunking](#43-why-not-rag-style-chunking)
5. [Elasticsearch Index Architecture](#5-elasticsearch-index-architecture)
   - 5.1 [Index Overview](#51-index-overview)
   - 5.2 [cms-content — Primary Search Index](#52-cms-content--primary-search-index)
   - 5.3 [cms-search-logs — Search Telemetry Index](#53-cms-search-logs--search-telemetry-index)
   - 5.4 [cms-click-logs — Click-Through Tracking Index](#54-cms-click-logs--click-through-tracking-index)
   - 5.5 [cms-content-views — Engagement & Referrer Tracking Index](#55-cms-content-views--engagement--referrer-tracking-index)
   - 5.6 [Index Settings and Shard Strategy](#56-index-settings-and-shard-strategy)
6. [Keyword Search vs Hybrid Search — Deep Technical Comparison](#6-keyword-search-vs-hybrid-search--deep-technical-comparison)
   - 6.1 [Keyword Search (BM25 Only)](#61-keyword-search-bm25-only)
   - 6.2 [Hybrid Search (BM25 + kNN + RRF)](#62-hybrid-search-bm25--knn--rrf)
   - 6.3 [How RRF Fusion Works Internally](#63-how-rrf-fusion-works-internally)
   - 6.4 [When Keyword Wins vs When Hybrid Wins](#64-when-keyword-wins-vs-when-hybrid-wins)
   - 6.5 [Image Similarity Search (kNN Only)](#65-image-similarity-search-knn-only)
   - 6.6 [Text-to-Image Cross-Modal Search](#66-text-to-image-cross-modal-search)
   - 6.7 [Comparison Endpoint](#67-comparison-endpoint)
7. [How Images Are Handled in the UI](#7-how-images-are-handled-in-the-ui)
8. [Data Ingestion Pipeline](#8-data-ingestion-pipeline)
9. [Analytics and Observability Layer](#9-analytics-and-observability-layer)
10. [Frontend Architecture](#10-frontend-architecture)
11. [Infrastructure and Deployment](#11-infrastructure-and-deployment)
12. [Known Limitations and Future Improvements](#12-known-limitations-and-future-improvements)

---

## 1. Executive Summary

The **CMS AI Search Platform** is a full-stack semantic search application that combines traditional BM25 keyword search with dense vector search (kNN) using Reciprocal Rank Fusion (RRF) in Elasticsearch. The system indexes ~2,200 multimedia assets (images, videos, audio, articles, papers, books) from 8 different content sources and provides five distinct search modes: hybrid, keyword-only, image similarity, text-to-image cross-modal, and side-by-side comparison.

**Key architectural decisions**:
- Inference runs **app-side in Python** (via SentenceTransformers), not in Elasticsearch's native inference endpoints
- Two models are used: **all-MiniLM-L6-v2** (384-dim text) and **clip-ViT-B-32** (512-dim images + cross-modal)
- Text is **truncated to 512 characters** (not chunked with overlap) — one embedding per asset
- Images in the UI are **URL-referenced thumbnails from remote CDNs**, not imported or bundled locally
- Four Elasticsearch indices track content, search logs, click logs, and content views

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React 19)                      │
│   React Router + Tailwind CSS + Recharts + Axios                │
│   Port: 5173 (Vite dev server)                                  │
│                                                                 │
│   Pages:                                                        │
│   ┌──────────┐ ┌──────────────┐ ┌────────────┐ ┌─────────────┐ │
│   │  Search   │ │ Image Search │ │ Comparison │ │  Dashboard  │ │
│   │  (hybrid) │ │   (CLIP)     │ │ (kw vs hy) │ │ (analytics) │ │
│   └─────┬────┘ └──────┬───────┘ └─────┬──────┘ └──────┬──────┘ │
│         │              │               │               │        │
│         └──────────────┴───────────────┴───────────────┘        │
│                              │                                   │
│                     Axios → /api/* (proxied)                     │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                     BACKEND (FastAPI + Uvicorn)                  │
│                     Port: 8000                                   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    ROUTERS                                  │ │
│  │  search.py    → /api/search, /api/search/keyword,           │ │
│  │                  /api/search/image, /api/search/text-to-image│ │
│  │                  /api/search/compare                        │ │
│  │  content.py   → /api/content/{id}, /related, /recommendations│ │
│  │  analytics.py → /api/analytics/kpis, hit-rate, geo, etc.   │ │
│  └────────┬──────────────────────────────┬─────────────────────┘ │
│           │                              │                       │
│  ┌────────▼────────┐          ┌──────────▼──────────┐            │
│  │ Embedding Layer │          │ Elasticsearch Layer  │            │
│  │                 │          │                      │            │
│  │ SentenceTransf. │          │ elasticsearch-py     │            │
│  │ ┌─────────────┐ │          │ cloud_id + api_key   │            │
│  │ │  MiniLM     │ │          │                      │            │
│  │ │  (384 dims) │ │ ──vec──▶ │ ┌──────────────────┐ │            │
│  │ └─────────────┘ │          │ │   Elastic Cloud   │ │            │
│  │ ┌─────────────┐ │          │ │                   │ │            │
│  │ │  CLIP       │ │          │ │ cms-content       │ │            │
│  │ │  (512 dims) │ │ ──vec──▶ │ │ cms-search-logs   │ │            │
│  │ └─────────────┘ │          │ │ cms-click-logs    │ │            │
│  └─────────────────┘          │ │ cms-content-views │ │            │
│                               │ └──────────────────┘ │            │
│                               └──────────────────────┘            │
└──────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                     ELASTIC CLOUD                                │
│                                                                  │
│  Managed Elasticsearch cluster                                   │
│  Authentication: API Key                                         │
│  4 indices (cms-content, cms-search-logs,                        │
│             cms-click-logs, cms-content-views)                   │
│                                                                  │
│  dense_vector fields with HNSW indexing                          │
│  BM25 + kNN + RRF fusion at query time                          │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. Embedding Pipeline Deep Dive

### 3.1 Models Used and Why

| Model | Hugging Face ID | Dimensions | Max Tokens | Parameters | Purpose |
|-------|----------------|-----------|------------|------------|---------|
| **all-MiniLM-L6-v2** | `sentence-transformers/all-MiniLM-L6-v2` | 384 | 256 word pieces | 22.7M | Text-to-text semantic search |
| **clip-ViT-B-32** | `sentence-transformers/clip-ViT-B-32` | 512 | 77 tokens (text branch) | 151M | Image embeddings + text-to-image cross-modal |

**Why all-MiniLM-L6-v2?**
- One of the most efficient models in the sentence-transformers ecosystem
- 384 dimensions is small enough for fast kNN but large enough for quality semantic matching
- 22.7M parameters means it loads in ~1 second and embeds text in ~2ms per query
- Trained on 1B+ sentence pairs, strong general-domain performance
- Normalized cosine similarity is well-suited for Elasticsearch's `dense_vector` field

**Why clip-ViT-B-32?**
- CLIP (Contrastive Language-Image Pre-training) maps both images and text into the **same 512-dimensional vector space**
- This enables cross-modal search: encode text with CLIP → search against image embeddings
- ViT-B-32 is the base variant — good balance between quality and speed
- The SentenceTransformers wrapper provides a unified `.encode()` API for both PIL images and strings

### 3.2 Why App-Side Inference Instead of Elasticsearch Inference Endpoints

Elasticsearch 8.x offers **inference endpoints** via the `_inference` API and the **Elastic Learned Sparse EncodeR (ELSER)** or custom model uploads via Eland. The question is: **why doesn't this project use them?**

#### What Elasticsearch Inference Endpoints Offer

Elasticsearch has the `PUT _inference/text_embedding/my-model` API which lets you:
1. Deploy a model directly inside the Elasticsearch cluster (via ML nodes)
2. Automatically generate embeddings at **index time** using an `inference` ingest pipeline processor
3. Automatically generate query embeddings at **search time** using `model_id` in kNN queries

This means the client never has to generate embeddings — Elasticsearch handles it internally.

#### Why This Project Uses App-Side Inference Instead

| Factor | ES-Native Inference | App-Side (Current) |
|--------|--------------------|--------------------|
| **Setup complexity** | Requires ML nodes, Eland CLI to upload models, inference pipeline configuration | pip install sentence-transformers — done |
| **Cost** | ML nodes on Elastic Cloud add significant cost (ML-tier pricing) | Runs on same compute as FastAPI (free) |
| **Model flexibility** | Limited to ONNX-compatible models, restricted by cluster resources | Any PyTorch/ONNX model, swap with one config change |
| **Batch ingestion** | Must go through ingest pipelines (sequential per-doc) | Python batch encoding with GPU support (batch_size=64) |
| **CLIP support** | No native CLIP support in ES inference (as of 8.17) | Full CLIP image + text encoding via SentenceTransformers |
| **Cross-modal search** | Not supported natively | Trivially supported (same model, different input types) |
| **Debugging** | Opaque — model runs inside ES cluster | Full Python visibility, logging, profiling |
| **Scaling** | Scale ML nodes independently | Scale FastAPI replicas, optionally add GPU |

**The critical blocker**: Elasticsearch's inference endpoints **do not support CLIP models** or any image embedding workflow. Since this platform requires image-to-image and text-to-image search, the embedding must happen outside Elasticsearch. Once you're already doing app-side inference for images, it makes sense to do text inference there too for consistency.

#### When You SHOULD Use ES Inference Endpoints

- **Pure text search** at production scale (thousands of queries/sec)
- When you want **zero application-side ML dependencies**
- When using **ELSER** (Elasticsearch's own sparse model) for English search
- When your ML team doesn't maintain the inference layer

#### Where the Inference Endpoint Would Be Located (If Used)

If this project migrated to ES-native inference, the configuration would be:

```
PUT _inference/text_embedding/minilm-embedder
{
  "service": "elasticsearch",
  "service_settings": {
    "model_id": ".multilingual-e5-small",  // or custom uploaded model
    "num_allocations": 1,
    "num_threads": 2
  }
}
```

The inference endpoint lives on the **ML nodes** of the Elasticsearch cluster. On Elastic Cloud, this requires enabling the **Machine Learning** tier in your deployment, which provisions dedicated hardware with sufficient memory to hold model weights.

### 3.3 Text Embedding Generation

**Source file**: `backend/models/embeddings.py`

**Single-query inference** (used at search time):

```python
def embed_text(text: str) -> list[float]:
    """Generate a 384-dim embedding from text using MiniLM."""
    model = get_text_model()          # cached singleton
    vec = model.encode(
        text,
        normalize_embeddings=True     # L2 normalize → unit sphere
    )
    return vec.tolist()               # numpy array → Python list
```

**Batch inference** (used at ingestion time):

```python
def embed_texts(texts: list[str]) -> list[list[float]]:
    """Batch-embed multiple texts."""
    model = get_text_model()
    vecs = model.encode(
        texts,
        normalize_embeddings=True,
        batch_size=64,                # process 64 texts per forward pass
        show_progress_bar=True
    )
    return vecs.tolist()
```

**What `normalize_embeddings=True` does**:
- Applies L2 normalization to each vector: `v / ||v||₂`
- After normalization, each vector has magnitude 1.0 (lies on a unit hypersphere)
- This makes **cosine similarity equivalent to dot product**: `cos(a, b) = a·b / (||a||·||b||) = a·b` when both are unit vectors
- Elasticsearch's `similarity: "cosine"` in the dense_vector mapping benefits from pre-normalized vectors because the engine can skip the normalization step during scoring

**Ingestion text construction** (`backend/scripts/ingest_data.py`):

```python
combined = f"{asset['title']}. {asset['description']}. {' '.join(asset['tags'])}"
text_input = combined[:512]  # hard truncation at 512 characters
```

This concatenation creates a single string like:
```
"Mountain Sunset Over Lake. A breathtaking view of the sun setting behind snow-capped
mountains reflected in a crystal clear alpine lake. nature landscape sunset mountains
water reflection golden-hour"
```

### 3.4 Image Embedding Generation (CLIP)

**From raw bytes** (search-time — user uploads an image):

```python
def embed_image_from_bytes(image_bytes: bytes) -> list[float]:
    model = get_clip_model()                                    # clip-ViT-B-32
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")  # PIL → RGB
    vec = model.encode(image, normalize_embeddings=True)        # 512-dim
    return vec.tolist()
```

CLIP's image encoder processes the image through:
1. Resize to 224×224 pixels (ViT-B-32 input size)
2. Normalize pixel values
3. Patch embedding (32×32 patches → 49 patches + CLS token)
4. Vision Transformer forward pass
5. Project to 512-dimensional shared space
6. L2 normalize

**From URL** (ingestion-time — download thumbnails from source APIs):

```python
def embed_image_from_url(url: str) -> list[float] | None:
    try:
        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return embed_image_from_bytes(resp.content)
    except Exception as e:
        print(f"  Failed to embed image from {url}: {e}")
        return None  # graceful failure — document indexed without image embedding
```

If the download fails (404, timeout, CORS), the document is still indexed with `text_embedding` but **without** `image_embedding`. This means the document won't appear in image similarity searches but will still be found via text/hybrid search.

### 3.5 Cross-Modal Embedding (Text-to-Image)

This is the most architecturally interesting embedding in the system.

```python
def embed_text_for_image_search(text: str) -> list[float]:
    """
    Encode text using the CLIP model (512 dims).
    This puts text into the same vector space as images,
    enabling text-to-image search.
    """
    model = get_clip_model()  # CLIP, NOT MiniLM!
    vec = model.encode(text, normalize_embeddings=True)
    return vec.tolist()       # 512 floats (same space as image embeddings)
```

**Why this works**: CLIP was trained with contrastive learning on 400M image-text pairs. The training objective pushes matching image-text pairs **close together** in the 512-dim space and non-matching pairs **apart**. This means:
- `CLIP.encode("golden hour landscape")` → produces a vector near images of golden hour landscapes
- This vector can be used as `query_vector` in kNN search against the `image_embedding` field
- The result is a text query that finds visually similar images **without any keyword matching**

**Important**: The text-to-image search uses `clip-ViT-B-32` (512 dims), NOT `all-MiniLM-L6-v2` (384 dims). These are completely separate vector spaces. MiniLM vectors cannot be compared to CLIP vectors — they have different dimensionality and different semantic spaces.

### 3.6 Model Loading and Caching Strategy

Both models use Python's `functools.lru_cache` for singleton caching:

```python
@lru_cache(maxsize=1)
def get_text_model() -> SentenceTransformer:
    print(f"Loading text model: {settings.text_model_name}...")
    return SentenceTransformer(settings.text_model_name)

@lru_cache(maxsize=1)
def get_clip_model() -> SentenceTransformer:
    print(f"Loading CLIP model: {settings.clip_model_name}...")
    return SentenceTransformer(settings.clip_model_name)
```

**Behavior**:
- **First call**: Downloads model weights from Hugging Face Hub (if not cached locally in `~/.cache/torch/sentence_transformers/`), loads into memory. Takes 2-10 seconds depending on network and hardware.
- **Subsequent calls**: Returns the same in-memory model object. Near-zero overhead.
- **Memory footprint**: MiniLM ~90MB RAM, CLIP ~600MB RAM. Total ~690MB for both models.
- **Thread safety**: `lru_cache` is thread-safe in CPython. SentenceTransformer's `.encode()` holds the GIL during forward pass, so concurrent requests serialize at the model level.

---

## 4. Chunk Configuration and Model Limits

### 4.1 Current Chunking Strategy

This platform uses a **single-embedding-per-document** approach, NOT traditional RAG-style chunking with overlapping windows.

**How text is prepared for embedding**:

```python
# In backend/scripts/ingest_data.py, line 52-53
combined = f"{a.get('title', '')}. {a.get('description', '')}. {' '.join(a.get('tags', []))}"
texts.append(combined[:512])  # hard truncation at 512 characters
```

**Pipeline**:
1. **Concatenate**: `title` + `. ` + `description` + `. ` + `tags (space-joined)`
2. **Truncate**: Slice first 512 characters (Python string slicing, character-level, not token-level)
3. **Embed**: Pass truncated string to MiniLM → one 384-dim vector
4. **Store**: One `text_embedding` field per Elasticsearch document

**There is NO**:
- Splitting into fixed-size windows (e.g., 256-token chunks with 50-token overlap)
- Paragraph-level or sentence-level chunking
- Parent-child relationship between chunks and documents
- Chunk overlap to preserve context across boundaries
- Chunk index (separate from document index)

### 4.2 Model Token/Character Limits

#### all-MiniLM-L6-v2

| Property | Value |
|----------|-------|
| **Max input tokens** | 256 word pieces (WordPiece tokenizer) |
| **Actual truncation by model** | Silently truncates at 256 tokens |
| **Approximate character equivalent** | ~800-1200 characters (depends on vocabulary) |
| **App-side truncation** | 512 characters (conservative, well within token limit) |
| **What happens beyond limit** | Text beyond 256 tokens is silently dropped by the tokenizer |

**Why 512 characters in the code?** The app truncates at 512 characters before tokenization. Since English averages ~4-5 characters per token (including subword pieces), 512 characters ≈ 100-128 tokens, well within MiniLM's 256-token limit. This is a **safe, conservative** truncation.

**Impact on long content**: For short-form assets (image titles, descriptions), 512 characters is usually sufficient. For long-form content (arXiv papers, Gutenberg books), only the beginning (title + first paragraph of description) is embedded. The semantic meaning of later paragraphs is **lost** in the vector representation, though BM25 still indexes the full text fields.

#### clip-ViT-B-32

| Property | Value |
|----------|-------|
| **Text branch max tokens** | 77 tokens (CLIP tokenizer, BPE) |
| **Image input size** | 224 × 224 pixels (auto-resized) |
| **Text truncation** | Silently truncates at 77 tokens |
| **Image preprocessing** | Resize → center crop → normalize → patch embed |

CLIP's 77-token text limit is notably short. For the text-to-image search feature (`/api/search/text-to-image`), only the first ~77 tokens (~300 characters) of the user's query contribute to the embedding. Long, complex queries don't benefit from additional words.

### 4.3 Why Not RAG-Style Chunking

| Approach | Current (Single Embedding) | RAG Chunking (Hypothetical) |
|----------|---------------------------|----------------------------|
| **Documents per asset** | 1 | 5-50 (depending on length) |
| **Index size** | ~2,200 docs | ~20,000-100,000 docs |
| **Ingestion time** | ~2 minutes | ~20-60 minutes |
| **Query complexity** | Simple kNN | kNN + field collapse + inner_hits |
| **Storage** | ~3.4MB vectors (2200 × 384 × 4 bytes) | ~30MB+ vectors |
| **Retrieval precision** | Asset-level (whole doc matches) | Chunk-level (specific passage matches) |
| **Best for** | Short-form metadata search | Long-form document Q&A (RAG) |

**The current approach is appropriate** for this use case because:
- Most assets are images/videos/audio with short metadata (< 200 chars total)
- Even articles and papers have concise abstracts that fit in 512 characters
- The system finds **assets**, not **passages within assets**
- RAG-style retrieval would add complexity without proportional benefit for this content mix

---

## 5. Elasticsearch Index Architecture

### 5.1 Index Overview

```
┌─────────────────────────────────────────────────────┐
│              ELASTIC CLOUD CLUSTER                   │
│                                                      │
│  ┌──────────────────┐    ┌─────────────────────┐     │
│  │   cms-content     │    │  cms-search-logs     │    │
│  │                   │    │                      │    │
│  │  ~2,200 docs      │    │  ~10,000 docs        │    │
│  │  2 shards         │    │  1 shard             │    │
│  │  1 replica        │    │  1 replica           │    │
│  │                   │    │                      │    │
│  │  Fields:          │    │  Fields:             │    │
│  │  - title (text)   │    │  - query_text (text) │    │
│  │  - description    │    │  - search_type (kw)  │    │
│  │  - tags (keyword) │    │  - result_count      │    │
│  │  - text_embedding │    │  - response_time_ms  │    │
│  │    (384 dims)     │    │  - user_id, region   │    │
│  │  - image_embedding│    │  - timestamp         │    │
│  │    (512 dims)     │    │                      │    │
│  │  + 17 more fields │    └──────────────────────┘    │
│  └──────────────────┘                                 │
│                                                      │
│  ┌──────────────────┐    ┌─────────────────────┐     │
│  │  cms-click-logs   │    │  cms-content-views   │    │
│  │                   │    │                      │    │
│  │  ~5,000 docs      │    │  ~8,000 docs         │    │
│  │  1 shard          │    │  1 shard             │    │
│  │  1 replica        │    │  1 replica           │    │
│  │                   │    │                      │    │
│  │  Fields:          │    │  Fields:             │    │
│  │  - content_id     │    │  - content_id        │    │
│  │  - query_text     │    │  - content_type      │    │
│  │  - position       │    │  - category          │    │
│  │  - search_type    │    │  - referrer          │    │
│  │  - timestamp      │    │  - time_spent_secs   │    │
│  │                   │    │  - timestamp         │    │
│  └──────────────────┘    └──────────────────────┘    │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### 5.2 cms-content — Primary Search Index

This is the core index that holds all searchable content. Every search query (hybrid, keyword, image, text-to-image) targets this index.

**Settings**:
```json
{
  "number_of_shards": 2,
  "number_of_replicas": 1
}
```

**Complete field mapping**:

| Field | ES Type | Analyzer | Purpose |
|-------|---------|----------|---------|
| `title` | `text` | `english` | Primary search field, stemming + stopwords. Also has `.raw` keyword subfield for exact match/aggregations |
| `description` | `text` | `english` | Secondary search field with English analysis |
| `content_type` | `keyword` | — | Filter field: `image`, `video`, `audio`, `document`, `article`, `book`, `paper` |
| `tags` | `keyword` | — | Multi-value keyword array. Used in BM25 search (boosted `^2`) and for UI display |
| `category` | `keyword` | — | Filter field: 20+ categories (nature, technology, health, education, etc.) |
| `source` | `keyword` | — | Data origin: `unsplash`, `pexels`, `pixabay`, `freesound`, `wikipedia`, `arxiv`, `gutenberg`, `archive` |
| `author` | `keyword` | — | Creator attribution |
| `license` | `keyword` | — | License type string |
| `url` | `keyword` | — | Full content URL (original source) |
| `thumbnail_url` | `keyword` | — | Remote thumbnail URL (used by UI for display) |
| `preview_url` | `keyword` | — | Extra preview URL (smaller thumbnail) |
| `file_type` | `keyword` | — | File format: `jpg`, `png`, `mp4`, `mp3`, `pdf`, `txt` |
| `created_at` | `date` | — | ISO 8601 timestamp |
| `region` | `keyword` | — | Geographic region: `North America`, `Europe`, `Asia`, etc. |
| `geo_location` | `geo_point` | — | Latitude/longitude for geographic queries |
| `view_count` | `integer` | — | Analytics counter (for sorting/display) |
| `download_count` | `integer` | — | Analytics counter |
| `duration_seconds` | `integer` | — | For video/audio content |
| `width` | `integer` | — | Image/video width in pixels |
| `height` | `integer` | — | Image/video height in pixels |
| `text_embedding` | `dense_vector` | — | **384 dimensions**, indexed with HNSW, cosine similarity |
| `image_embedding` | `dense_vector` | — | **512 dimensions**, indexed with HNSW, cosine similarity |

**Dense vector field configuration**:
```json
"text_embedding": {
    "type": "dense_vector",
    "dims": 384,
    "index": true,
    "similarity": "cosine"
}
```

- `"index": true` — Elasticsearch builds an **HNSW (Hierarchical Navigable Small World)** graph for approximate nearest neighbor search. Without this, kNN would require brute-force comparison against all vectors.
- `"similarity": "cosine"` — Elasticsearch computes `(1 + cosine(a, b)) / 2` to normalize the score to `[0, 1]`. Since embeddings are pre-normalized (unit vectors), this is equivalent to `(1 + dot_product(a, b)) / 2`.

**English analyzer on text fields**: The `english` analyzer applies:
1. Standard tokenization (split on whitespace/punctuation)
2. Lowercase filter
3. English stop words removal ("the", "is", "at", etc.)
4. English stemmer (Porter stemmer: "running" → "run", "mountains" → "mountain")

This means a search for "running through mountains" will match documents containing "ran through mountain" via stemming.

### 5.3 cms-search-logs — Search Telemetry Index

Captures every search event for analytics and observability.

**Settings**: 1 shard, 1 replica

| Field | ES Type | Purpose |
|-------|---------|---------|
| `query_text` | `text` + `.raw` keyword | The user's search query. Text type enables full-text search on queries; `.raw` keyword subfield enables exact-match terms aggregations |
| `search_type` | `keyword` | Which search mode: `hybrid`, `keyword`, `image` |
| `result_count` | `integer` | Number of results returned. `0` indicates a zero-result search |
| `response_time_ms` | `integer` | End-to-end latency including embedding generation |
| `user_id` | `keyword` | Currently hardcoded to `"demo-user"` |
| `session_id` | `keyword` | First 8 chars of a UUID, generated per search |
| `region` | `keyword` | Currently hardcoded to `"North America"` |
| `geo` | `geo_point` | Available for geographic analytics (not populated in demo) |
| `timestamp` | `date` | ISO 8601 when the search occurred |
| `filters_used` | `keyword` | Which filters were active (content_type, category, etc.) |

**How search events are logged** (from `backend/routers/search.py`):

```python
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
```

The `try/except pass` pattern ensures logging failures never impact search latency or availability. This is a **fire-and-forget** pattern — the search response is returned regardless of whether the log was written.

**Analytics queries against this index**:
- **Hit rate**: Date histogram + bucket_script to compute `(total - zero_results) / total * 100`
- **Zero-result queries**: Terms aggregation on `query_text.raw` filtered by `result_count: 0`
- **Geo distribution**: Terms aggregation on `region` with sub-aggregation for top queries per region

### 5.4 cms-click-logs — Click-Through Tracking Index

Tracks when users click on a specific result from search results.

**Settings**: 1 shard, 1 replica

| Field | ES Type | Purpose |
|-------|---------|---------|
| `content_id` | `keyword` | Elasticsearch document ID that was clicked |
| `query_text` | `text` + `.raw` keyword | The search query that produced this result |
| `position` | `integer` | Rank position in the result list (1 = first result) |
| `search_type` | `keyword` | Which search mode produced this result |
| `user_id` | `keyword` | User identifier |
| `session_id` | `keyword` | Session identifier |
| `region` | `keyword` | User region |
| `timestamp` | `date` | When the click occurred |

**Usage status**: Click logs are collected but **not heavily utilized** in the current dashboard. They could be used for:
- Click-through rate (CTR) analysis per query
- Position bias analysis (do users always click first result?)
- nDCG / MRR computation to compare keyword vs hybrid quality
- Training a learning-to-rank model

### 5.5 cms-content-views — Engagement & Referrer Tracking Index

Tracks content detail page views with referrer information.

**Settings**: 1 shard, 1 replica

| Field | ES Type | Purpose |
|-------|---------|---------|
| `content_id` | `keyword` | Elasticsearch document ID viewed |
| `content_type` | `keyword` | Asset type for breakdown analytics |
| `category` | `keyword` | Asset category for trend analysis |
| `user_id` | `keyword` | User identifier |
| `session_id` | `keyword` | Session identifier |
| `region` | `keyword` | User region |
| `referrer` | `keyword` | How the user reached the page: `search`, `recommendation`, `direct`, `external` |
| `time_spent_seconds` | `integer` | Time on page (currently always 0 — not tracked client-side) |
| `timestamp` | `date` | When the view occurred |

**Analytics queries against this index**:
- **Engagement trends**: Terms aggregation on `category` → date histogram sub-agg → view count per category over time
- **Top category KPI**: Terms aggregation on `category`, size=1

### 5.6 Index Settings and Shard Strategy

| Index | Shards | Replicas | Rationale |
|-------|--------|----------|-----------|
| `cms-content` | 2 | 1 | Higher search throughput for the primary search index. 2 shards allow parallel query execution across nodes |
| `cms-search-logs` | 1 | 1 | Append-only analytics. Single shard sufficient for 10K-100K docs |
| `cms-click-logs` | 1 | 1 | Low-volume event data |
| `cms-content-views` | 1 | 1 | Low-volume event data |

**HNSW graph configuration** (Elasticsearch defaults for dense_vector):
- `m`: 16 (number of bi-directional links per node in the HNSW graph)
- `ef_construction`: 100 (size of the dynamic candidate list during index building)
- `ef_search`: Controlled by `num_candidates` in kNN queries (default: `max(size * 5, 100)`)

For 2,200 documents, HNSW provides near-exact results. The approximate nature of HNSW only becomes significant at >100K documents.

---

## 6. Keyword Search vs Hybrid Search — Deep Technical Comparison

### 6.1 Keyword Search (BM25 Only)

**Endpoint**: `GET /api/search/keyword?q=sunset+landscape`

**What happens internally**:

```
User query: "sunset landscape"
         │
         ▼
┌──────────────────────────┐
│    FastAPI Endpoint       │
│    (no embedding needed)  │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────┐
│              Elasticsearch BM25 Query                 │
│                                                       │
│  POST /cms-content/_search                           │
│  {                                                    │
│    "query": {                                         │
│      "bool": {                                        │
│        "must": [{                                     │
│          "multi_match": {                             │
│            "query": "sunset landscape",               │
│            "fields": ["title^3", "description^2",     │
│                       "tags^2"],                       │
│            "type": "best_fields"                      │
│          }                                            │
│        }]                                             │
│      }                                                │
│    }                                                  │
│  }                                                    │
└──────────────────────────────────────────────────────┘
```

**BM25 scoring explained**:

BM25 (Best Match 25) scores each document based on:

```
score(D, Q) = Σ  IDF(qi) × (f(qi, D) × (k1 + 1)) / (f(qi, D) + k1 × (1 - b + b × |D|/avgdl))
              qi∈Q
```

Where:
- `IDF(qi)` = Inverse Document Frequency: rare terms score higher
- `f(qi, D)` = Term frequency of query term `qi` in document `D`
- `k1` = 1.2 (controls term frequency saturation)
- `b` = 0.75 (controls document length normalization)
- `|D|` = document length, `avgdl` = average document length

**Field boosting**: `title^3, description^2, tags^2`
- A match in `title` contributes 3× more score than a match in an unboosted field
- This means a document with "sunset" in the title ranks higher than one with "sunset" only in the description
- `best_fields` type means: take the maximum score from any single field (not sum)

**What BM25 CAN find**:
- Exact term matches: "sunset" → documents containing "sunset"
- Stemmed matches: "running" → documents containing "run", "ran", "runs" (via English analyzer)
- Multi-term matches: "sunset landscape" → documents containing both terms score highest

**What BM25 CANNOT find**:
- Semantic equivalents: "dusk scenery" (no token overlap with "sunset landscape")
- Paraphrases: "when the sun goes down over nature" (no matching stems)
- Conceptual queries: "golden hour photography" (different vocabulary, same concept)
- Intent-level queries: "something peaceful to look at" (abstract intent, no keywords match)

### 6.2 Hybrid Search (BM25 + kNN + RRF)

**Endpoint**: `GET /api/search?q=sunset+landscape`

**What happens internally**:

```
User query: "sunset landscape"
         │
         ▼
┌───────────────────────────────┐
│      FastAPI Endpoint          │
│                                │
│  1. embed_text("sunset         │
│     landscape")                │
│     → [0.032, -0.118, ...,     │
│        0.074]  (384 floats)    │
│     ~50-100ms                  │
└──────────┬────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────┐
│         Elasticsearch Combined Query                     │
│                                                          │
│  POST /cms-content/_search                              │
│  {                                                       │
│    "query": {           ◄── BM25 leg                    │
│      "bool": {                                           │
│        "must": [{                                        │
│          "multi_match": {                                │
│            "query": "sunset landscape",                  │
│            "fields": ["title^3", "description^2",        │
│                       "tags^2"],                          │
│            "type": "best_fields"                         │
│          }                                               │
│        }]                                                │
│      }                                                   │
│    },                                                    │
│    "knn": {             ◄── Vector leg                   │
│      "field": "text_embedding",                          │
│      "query_vector": [0.032, -0.118, ..., 0.074],       │
│      "k": 20,                                            │
│      "num_candidates": 100                               │
│    },                                                    │
│    "rank": {            ◄── Fusion                       │
│      "rrf": {                                            │
│        "rank_window_size": 100,                          │
│        "rank_constant": 60                               │
│      }                                                   │
│    }                                                     │
│  }                                                       │
└─────────────────────────────────────────────────────────┘
```

**Elasticsearch executes TWO independent retrieval pipelines**:

1. **BM25 pipeline**: Standard inverted index lookup, scores documents by term overlap, returns top `rank_window_size` (100) results
2. **kNN pipeline**: HNSW approximate nearest neighbor search on `text_embedding` field, returns top `num_candidates` (100) candidates, then re-ranks to get `k` (20) results

Then **RRF fusion** combines both ranked lists into a single result set.

### 6.3 How RRF Fusion Works Internally

**Reciprocal Rank Fusion (RRF)** is a rank-based fusion algorithm that doesn't depend on raw scores (which are incomparable between BM25 and kNN).

**Formula**:

```
RRF_score(d) = Σ  1 / (rank_constant + rank_i(d))
               i∈{BM25, kNN}
```

With `rank_constant = 60`:

| Document | BM25 Rank | kNN Rank | RRF Score |
|----------|-----------|----------|-----------|
| Doc A | 1 | 5 | 1/(60+1) + 1/(60+5) = 0.01639 + 0.01538 = **0.03177** |
| Doc B | 3 | 2 | 1/(60+3) + 1/(60+2) = 0.01587 + 0.01613 = **0.03200** |
| Doc C | 50 | 1 | 1/(60+50) + 1/(60+1) = 0.00909 + 0.01639 = **0.02548** |
| Doc D | 2 | ∞ (not found) | 1/(60+2) + 0 = **0.01613** |
| Doc E | ∞ (not found) | 3 | 0 + 1/(60+3) = **0.01587** |

**Key properties of RRF**:
- **Score-agnostic**: Only uses rank positions, not raw scores. This avoids the problem of comparing BM25 scores (unbounded) with cosine similarity scores ([0,1]).
- **Balanced fusion**: `rank_constant = 60` means the top-1 result from either system gets score `1/61 ≈ 0.0164`, and the top-100 gets `1/160 ≈ 0.0063`. This is a gentle falloff.
- **Handles partial overlap**: Documents appearing in only one list still get scored (with 0 from the other list).
- **rank_window_size = 100**: Only the top 100 from each system participate in fusion. Documents ranked >100 in both systems are excluded.

### 6.4 When Keyword Wins vs When Hybrid Wins

| Query Type | Keyword (BM25) | Hybrid (BM25 + kNN + RRF) | Winner |
|------------|---------------|--------------------------|--------|
| "sunset landscape" | Finds docs with exact terms | Finds exact + semantically similar | **Hybrid** (marginal improvement) |
| "dusk scenery" | Misses if no doc uses these exact words | kNN finds sunset/landscape docs semantically | **Hybrid** (significant lift) |
| "IMG_4392.jpg" | Finds exact filename match | kNN finds nothing useful; BM25 carries | **Keyword** (kNN adds noise) |
| "peaceful nature" | Finds "peaceful" + "nature" | Also finds "serene", "calm", "tranquil" concepts | **Hybrid** (semantic recall) |
| "einstein relativity" | Finds exact term matches | Also finds related physics concepts | **Hybrid** (topical expansion) |
| "asdkjh" (typo) | Zero results | kNN might find gibberish-adjacent vectors | **Keyword** (both fail, but keyword fails cleanly) |

The **comparison endpoint** (`/api/search/compare`) returns both result sets side-by-side and explicitly flags `hybrid_only_ids` — documents found by hybrid but missed by keyword. This directly demonstrates the semantic lift.

### 6.5 Image Similarity Search (kNN Only)

**Endpoint**: `POST /api/search/image` (upload an image file)

```
User uploads image bytes
         │
         ▼
┌───────────────────────────────┐
│  embed_image_from_bytes()      │
│  → CLIP ViT-B-32 encoder      │
│  → 512-dim normalized vector   │
│  ~100-200ms                    │
└──────────┬────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────┐
│  Elasticsearch kNN-only Query                        │
│                                                      │
│  "knn": {                                           │
│    "field": "image_embedding",    ◄── 512-dim field │
│    "query_vector": [CLIP output],                    │
│    "k": 20,                                          │
│    "num_candidates": 100                             │
│  }                                                   │
│                                                      │
│  No BM25, no RRF — pure vector similarity            │
└─────────────────────────────────────────────────────┘
```

**Only works for image assets** that have an `image_embedding` field populated during ingestion. Non-image assets (articles, papers, books) and images whose thumbnail download failed during ingestion will NOT appear in these results.

### 6.6 Text-to-Image Cross-Modal Search

**Endpoint**: `GET /api/search/text-to-image?q=golden+hour+landscape`

```
User query: "golden hour landscape"
         │
         ▼
┌──────────────────────────────────────┐
│  embed_text_for_image_search()        │
│  Uses CLIP text encoder (NOT MiniLM!) │
│  → 512-dim vector in IMAGE space      │
│  ~50-100ms                            │
└──────────┬───────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────┐
│  Elasticsearch kNN Query                             │
│                                                      │
│  "knn": {                                           │
│    "field": "image_embedding",                       │
│    "query_vector": [CLIP text output],               │
│    "k": 20,                                          │
│    "num_candidates": 100,                            │
│    "filter": {"term": {"content_type": "image"}}     │
│  }                                                   │
│                                                      │
│  Text → CLIP → kNN against image vectors             │
└─────────────────────────────────────────────────────┘
```

**This is possible because** CLIP was trained contrastively: matching text-image pairs are pushed close in the shared 512-dim space. So `CLIP.encode_text("golden hour")` produces a vector near `CLIP.encode_image(golden_hour_photo.jpg)`.

### 6.7 Comparison Endpoint

**Endpoint**: `GET /api/search/compare?q=sunset+landscape`

Executes both keyword search and hybrid search in parallel (sequential in code), returns both result sets, and computes `hybrid_only_ids`:

```python
# In backend/routers/search.py
kw_ids = {r["id"] for r in kw_results}
hybrid_only_ids = [r["id"] for r in hybrid_results if r["id"] not in kw_ids]
```

**Response structure**:
```json
{
  "query": "sunset landscape",
  "response_time_ms": 245,
  "keyword": {
    "total": 35,
    "results": [/* BM25-only results */]
  },
  "hybrid": {
    "total": 47,
    "results": [/* BM25+kNN+RRF results */]
  },
  "hybrid_only_ids": ["doc_abc", "doc_xyz"]  // found by hybrid, missed by keyword
}
```

The UI highlights `hybrid_only_ids` results with an indigo border to visually demonstrate semantic lift.

---

## 7. How Images Are Handled in the UI

### The Short Answer

**Images are NOT imported, bundled, or stored locally.** The UI renders images directly from remote URLs (Unsplash, Pexels, Pixabay CDNs) using standard HTML `<img>` tags. The `data/assets/` directory is empty.

### The Full Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                     INGESTION TIME                               │
│                                                                  │
│  download_assets.py fetches METADATA from APIs:                  │
│                                                                  │
│  Unsplash API → { "urls": { "thumb": "https://images.unsplash.  │
│                    com/photo-abc?w=200" } }                      │
│                                                                  │
│  Stored in all_assets.json as:                                   │
│  {                                                               │
│    "url": "https://unsplash.com/photos/abc",      ← full page   │
│    "thumbnail_url": "https://images.unsplash.com/             ←──┤
│                      photo-abc?w=300",              thumbnail    │
│    "preview_url": "https://images.unsplash.com/               │
│                    photo-abc?w=100"                  tiny preview │
│  }                                                               │
│                                                                  │
│  These URLs are indexed as KEYWORD fields in Elasticsearch       │
│  (stored as strings, not as binary image data)                   │
└──────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                     SEARCH TIME (UI)                             │
│                                                                  │
│  Elasticsearch returns: { "thumbnail_url": "https://images.     │
│  unsplash.com/photo-abc?w=300" }                                │
│                                                                  │
│  ResultCard.tsx renders:                                         │
│                                                                  │
│  {result.thumbnail_url ? (                                       │
│    <img                                                          │
│      src={result.thumbnail_url}    ◄── browser fetches directly  │
│      alt={result.title}                from Unsplash CDN         │
│      className="w-full h-full object-cover"                      │
│      loading="lazy"                ◄── deferred loading          │
│      onError={(e) => {             ◄── hide if URL is broken     │
│        (e.target as HTMLImageElement).style.display = "none";    │
│      }}                                                          │
│    />                                                            │
│  ) : (                                                           │
│    <div>                           ◄── fallback icon if no URL   │
│      <Icon className="w-12 h-12 text-gray-300" />               │
│    </div>                                                        │
│  )}                                                              │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                     BROWSER NETWORK                              │
│                                                                  │
│  GET https://images.unsplash.com/photo-abc?w=300                │
│  → 200 OK (JPEG, ~20KB)                                        │
│  → Rendered in the 160px tall thumbnail area                     │
│                                                                  │
│  The image bytes never touch the FastAPI backend.                │
│  The browser fetches directly from the CDN.                      │
└──────────────────────────────────────────────────────────────────┘
```

### Implications

| Aspect | Impact |
|--------|--------|
| **Storage** | Zero image storage on backend/Elasticsearch. Only URL strings (~100 bytes each) |
| **Bandwidth** | Backend serves only JSON. Image bandwidth is between browser ↔ CDN |
| **Latency** | Images load asynchronously with `loading="lazy"`. Search results appear instantly; thumbnails fill in progressively |
| **Reliability** | If source CDN is down or URL expires, the image doesn't render. `onError` hides broken images gracefully |
| **CORS** | Unsplash, Pexels, Pixabay all have permissive CORS policies for their CDN domains. No CORS issues in practice |
| **Caching** | Browser caches images per standard HTTP cache headers from the CDN. Repeated views are fast |
| **Cost** | No object storage costs (S3, GCS). Free CDN bandwidth from source APIs |

### For Non-Image Content Types

When `thumbnail_url` is empty or null (common for audio, articles, books), the UI renders a **Lucide React icon** based on `content_type`:

| Content Type | Fallback Icon |
|-------------|---------------|
| `image` | ImageIcon |
| `video` | Video |
| `audio` | Music |
| `document` | FileText |
| `article` | FileText |
| `book` | BookOpen |
| `paper` | GraduationCap |

---

## 8. Data Ingestion Pipeline

### Stage 1: Metadata Collection

**Script**: `backend/scripts/download_assets.py`

Fetches metadata (NOT binary files) from 8 content APIs:

| Source | Content Types | API Key Required | Items Fetched |
|--------|-------------|-----------------|---------------|
| Unsplash | Photos | Yes (Client-ID) | ~300 (15 searches × 20/page) |
| Pexels | Photos + Videos | Yes (Bearer) | ~400 |
| Pixabay | Images + Videos + Music | Yes (Query param) | ~500 |
| Freesound | Audio/SFX | Yes (Token) | ~200 |
| Wikipedia | Articles | No | ~200 (sample articles) |
| arXiv | Academic Papers | No (OAI) | ~200 |
| Project Gutenberg | Books | No | ~200 |
| Internet Archive | Mixed | No | ~200 |

**Output**: `data/metadata/all_assets.json` — ~2,200 items, ~2.2MB

### Stage 2: Index Setup

**Script**: `backend/scripts/setup_indices.py`

1. Connects to Elastic Cloud via `cloud_id` + `api_key`
2. Creates all 4 indices with full mappings (see Section 5)
3. Supports `--delete` flag to recreate existing indices
4. Validates cluster connectivity before proceeding

### Stage 3: Embedding Generation + Bulk Indexing

**Script**: `backend/scripts/ingest_data.py`

```
Load all_assets.json (~2,200 items)
           │
           ▼
   Generate text embeddings
   ┌─────────────────────────────────────────────────────┐
   │  For each asset:                                     │
   │    combined = title + ". " + description + ". " +    │
   │              tags.join(" ")                           │
   │    text = combined[:512]   ◄── truncate              │
   │                                                      │
   │  embed_texts(all_texts, batch_size=64)               │
   │  → MiniLM generates 384-dim vectors                  │
   │  → ~2,200 embeddings in ~5-10 seconds                │
   └──────────────────────────────┬──────────────────────┘
                                  │
                                  ▼
   Generate image embeddings (selective)
   ┌─────────────────────────────────────────────────────┐
   │  For each asset WHERE:                               │
   │    content_type == "image" AND thumbnail_url exists   │
   │                                                      │
   │  1. Download thumbnail from URL (httpx, 15s timeout) │
   │  2. PIL.open() → RGB conversion                      │
   │  3. CLIP ViT-B-32 → 512-dim vector                  │
   │  4. If download fails → skip (no image_embedding)    │
   │                                                      │
   │  Progress logged every 50 images                     │
   │  ~500-1000 images, ~2-5 minutes                      │
   └──────────────────────────────┬──────────────────────┘
                                  │
                                  ▼
   Bulk index into Elasticsearch
   ┌─────────────────────────────────────────────────────┐
   │  elasticsearch.helpers.bulk()                        │
   │    chunk_size = 100                                  │
   │    raise_on_error = False                            │
   │                                                      │
   │  Each document includes:                             │
   │    - All metadata fields                             │
   │    - text_embedding (always present, 384 floats)     │
   │    - image_embedding (only for images, 512 floats)   │
   │                                                      │
   │  After indexing: es.indices.refresh() + count verify │
   └─────────────────────────────────────────────────────┘
```

### Stage 4: Synthetic Analytics Data

**Script**: `backend/scripts/generate_analytics.py`

Generates realistic-looking analytics data for the dashboard:

| Data Type | Volume | Time Range | Characteristics |
|-----------|--------|-----------|-----------------|
| Search logs | 10,000 events | Last 90 days | 15% zero-result rate, regional distribution |
| Click logs | 5,000 events | Last 90 days | Position-weighted (earlier ranks clicked more) |
| Content views | 8,000 events | Last 90 days | Power-law distribution (80/20 rule) |

---

## 9. Analytics and Observability Layer

### Dashboard KPIs

**Endpoint**: `GET /api/analytics/kpis`

| KPI | Elasticsearch Query | Index |
|-----|-------------------|-------|
| Total Assets | `es.count(index="cms-content")` | cms-content |
| Total Searches | `es.count(index="cms-search-logs")` | cms-search-logs |
| Avg Hit Rate | `(total - zero_result_count) / total × 100` | cms-search-logs |
| Top Category | `terms(field="category", size=1)` | cms-content-views |

### Search Hit Rate Over Time

**Endpoint**: `GET /api/analytics/search-hit-rate?interval=day&days=90`

Uses a **bucket_script** aggregation — a Painless script that computes derived metrics within each date histogram bucket:

```json
{
  "aggs": {
    "over_time": {
      "date_histogram": { "field": "timestamp", "calendar_interval": "day" },
      "aggs": {
        "total": { "value_count": { "field": "query_text.raw" } },
        "zero_hits": { "filter": { "term": { "result_count": 0 } } },
        "hit_rate": {
          "bucket_script": {
            "buckets_path": { "total": "total", "zeros": "zero_hits._count" },
            "script": "params.total > 0 ? ((params.total - params.zeros) / params.total) * 100 : 0"
          }
        }
      }
    }
  }
}
```

This produces per-day/week/month hit rate percentages without any application-side computation.

### Zero-Result Query Analysis

**Endpoint**: `GET /api/analytics/zero-results`

```json
{
  "query": { "term": { "result_count": 0 } },
  "aggs": {
    "failed_queries": {
      "terms": { "field": "query_text.raw", "size": 50 },
      "aggs": {
        "latest": { "max": { "field": "timestamp" } }
      }
    }
  }
}
```

Identifies queries users searched for but got no results — valuable for content gap analysis and synonym dictionary expansion.

### Geographic Distribution

**Endpoint**: `GET /api/analytics/geo-distribution`

```json
{
  "aggs": {
    "regions": {
      "terms": { "field": "region", "size": 30 },
      "aggs": {
        "top_queries": { "terms": { "field": "query_text.raw", "size": 5 } },
        "search_count": { "value_count": { "field": "query_text.raw" } }
      }
    }
  }
}
```

Shows search volume per region and the most popular queries within each region.

### Engagement Trends

**Endpoint**: `GET /api/analytics/engagement-trends?interval=week&days=90`

Aggregates content views by category over time to show which content categories are trending.

### Content Type Breakdown

**Endpoint**: `GET /api/analytics/content-type-breakdown`

Aggregates total view_count by content_type to show distribution of engagement across asset types (image vs video vs article, etc.).

---

## 10. Frontend Architecture

### Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Framework | React | 19.0.0 |
| Routing | React Router | 7.1.0 |
| Build Tool | Vite | 6.0.5 |
| Styling | Tailwind CSS | 3.4.17 |
| Charts | Recharts | 2.15.0 |
| Icons | Lucide React | 0.469.0 |
| HTTP Client | Axios | 1.7.9 |
| Language | TypeScript | 5.7.2 |

### Page Routes

| Route | Component | Purpose |
|-------|-----------|---------|
| `/` | SearchPage | Default hybrid search interface |
| `/image-search` | ImageSearchPage | Image upload → CLIP similarity search |
| `/compare` | ComparisonPage | Side-by-side keyword vs hybrid |
| `/content/:id` | ContentDetailPage | Single asset view + related + recommendations |
| `/dashboard` | DashboardPage | Analytics charts and KPIs |

### API Client

**File**: `frontend/src/api/client.ts`

Axios instance with:
- `baseURL: "/api"` — proxied by Vite to `http://localhost:8000`
- `timeout: 30000` — 30-second timeout for slow embedding operations

### Key Components

| Component | Purpose |
|-----------|---------|
| `SearchBar` | Text input with search icon + submit button |
| `ResultCard` | Thumbnail + title + description + tags + metadata + score badge |
| `ImageUploader` | Drag & drop image upload with preview |
| `RecommendationPanel` | Grid of recommended content (MLT or kNN) |
| `SearchHitRateChart` | Dual-axis line chart (Recharts) |
| `TopContentChart` | Bar chart of most-viewed content |
| `ZeroResultsTable` | Bar chart of failed queries |
| `GeoHeatmap` | Regional search volume + top queries |
| `EngagementTrends` | Multi-series line chart by category |
| `ContentTypeChart` | Pie chart of content type distribution |

---

## 11. Infrastructure and Deployment

### Current Setup

| Component | Technology | Hosting |
|-----------|-----------|---------|
| Backend | FastAPI + Uvicorn | Local (port 8000) |
| Frontend | Vite dev server | Local (port 5173) |
| Elasticsearch | Elastic Cloud | Managed (cloud_id) |
| Models | SentenceTransformers | In-process (CPU) |
| Image Storage | None | Remote CDNs |

### Python Dependencies

```
fastapi==0.115.6
uvicorn[standard]==0.34.0
elasticsearch>=8.17.0
sentence-transformers==3.3.1
Pillow==11.1.0
python-multipart==0.0.20
httpx==0.28.1
pydantic==2.10.4
pydantic-settings==2.7.1
python-dotenv==1.0.1
```

### Running the Application

```bash
# Backend
cd backend
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev  # http://localhost:5173

# Ingestion (one-time)
cd backend
python -m scripts.setup_indices
python -m scripts.download_assets
python -m scripts.ingest_data
python -m scripts.generate_analytics
```

### No Docker/Kubernetes Configuration

The project does not include Docker/Compose files. For containerization, you would need:

1. **Backend image**: Python 3.11 + FastAPI + SentenceTransformers (~2GB with model weights)
2. **Frontend image**: Node build → static files served by nginx (~50MB)
3. **Elasticsearch**: Elastic Cloud (external, no container needed)

---

## 12. Known Limitations and Future Improvements

### Current Limitations

| Limitation | Impact | Mitigation Path |
|-----------|--------|-----------------|
| **512-char truncation** | Long documents lose semantic meaning beyond first ~100 tokens | Implement RAG-style chunking with parent-child relationships |
| **App-side inference** | Single Python process bottleneck at scale | Migrate to ES inference endpoints or dedicated model serving (Triton, TorchServe) |
| **No CLIP in ES** | Can't do ES-native image inference | Keep app-side CLIP; potentially use ONNX export |
| **Single-vector per doc** | No passage-level retrieval | Add chunk index with `field_collapse` on parent_id |
| **Hardcoded user/region** | No real user tracking | Integrate auth (OAuth/JWT) and GeoIP |
| **No query caching** | Repeated queries re-embed and re-query | Add Redis/Memcached for popular query results |
| **No re-ranking** | RRF is deterministic, not learned | Add cross-encoder re-ranking (e.g., ms-marco-MiniLM-L-6-v2) |
| **Synthetic analytics** | Dashboard data is fake | Connect to real user event pipeline |
| **Click logs underused** | CTR/nDCG not computed | Build relevance metrics pipeline |
| **Image URL dependency** | Broken URLs = missing thumbnails | Mirror images to S3/GCS or implement URL health checks |

### Production Migration Path

```
                         CURRENT                         PRODUCTION
                    ┌──────────────┐              ┌──────────────────────┐
                    │  FastAPI     │              │   FastAPI + Gunicorn  │
                    │  (single)    │              │   (4 workers, K8s)    │
                    │              │              │                       │
                    │  MiniLM ─────│──────────▶   │   Model Serving       │
                    │  CLIP   ─────│              │   (Triton/TorchServe) │
                    └──────┬───────┘              └──────────┬────────────┘
                           │                                 │
                    ┌──────▼───────┐              ┌──────────▼────────────┐
                    │ Elastic Cloud│              │   Elastic Cloud        │
                    │ (no ML nodes)│──────────▶   │   + ML nodes           │
                    │              │              │   + ELSER              │
                    └──────────────┘              │   + Inference pipelines │
                                                 └────────────────────────┘
```

---

## Appendix A: Complete Elasticsearch Query Reference

### A.1 Hybrid Search Query (Actual ES Body)

```json
{
  "size": 20,
  "query": {
    "bool": {
      "must": [
        {
          "multi_match": {
            "query": "sunset landscape",
            "fields": ["title^3", "description^2", "tags^2"],
            "type": "best_fields"
          }
        }
      ],
      "filter": [
        { "term": { "content_type": "image" } },
        { "term": { "category": "nature" } }
      ]
    }
  },
  "knn": {
    "field": "text_embedding",
    "query_vector": [0.032, -0.118, "... 384 floats ..."],
    "k": 20,
    "num_candidates": 100,
    "filter": {
      "bool": {
        "filter": [
          { "term": { "content_type": "image" } },
          { "term": { "category": "nature" } }
        ]
      }
    }
  },
  "rank": {
    "rrf": {
      "rank_window_size": 100,
      "rank_constant": 60
    }
  },
  "_source": {
    "excludes": ["text_embedding", "image_embedding"]
  }
}
```

### A.2 More Like This Query (Related Content)

```json
{
  "size": 6,
  "query": {
    "more_like_this": {
      "fields": ["title", "description", "tags"],
      "like": [{ "_index": "cms-content", "_id": "doc_abc123" }],
      "min_term_freq": 1,
      "max_query_terms": 25
    }
  },
  "_source": { "excludes": ["text_embedding", "image_embedding"] }
}
```

### A.3 kNN Recommendations (Excluding Source Document)

```json
{
  "size": 6,
  "knn": {
    "field": "text_embedding",
    "query_vector": [0.032, -0.118, "... 384 floats ..."],
    "k": 7,
    "num_candidates": 50,
    "filter": {
      "bool": {
        "must_not": { "ids": { "values": ["doc_abc123"] } }
      }
    }
  },
  "_source": { "excludes": ["text_embedding", "image_embedding"] }
}
```

### A.4 Dashboard KPI Aggregation (Hit Rate)

```json
{
  "size": 0,
  "aggs": {
    "total": { "value_count": { "field": "query_text.raw" } },
    "zero_hits": { "filter": { "term": { "result_count": 0 } } }
  }
}
```

Application-side: `avg_hit_rate = ((total - zeros) / total * 100)`

---

## Appendix B: Vector Dimension Summary

| Vector Field | Model | Dimensions | Distance Metric | Index Type | Where Used |
|-------------|-------|-----------|-----------------|-----------|------------|
| `text_embedding` | all-MiniLM-L6-v2 | 384 | Cosine | HNSW | Hybrid search, recommendations |
| `image_embedding` | clip-ViT-B-32 | 512 | Cosine | HNSW | Image similarity, text-to-image |

**These are separate vector spaces. You cannot compare a 384-dim MiniLM vector against a 512-dim CLIP vector.** They encode different types of semantic information using different model architectures trained on different datasets.

---

*End of Technical Architecture Document*
