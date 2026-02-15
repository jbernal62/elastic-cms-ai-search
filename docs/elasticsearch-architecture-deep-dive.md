# CMS AI Search - Elasticsearch Architecture Deep Dive

## 1. Scope and Ground Truth

This document is based on the current implementation in `cms-ai-search` and explains the system from an Elasticsearch-first perspective, including:

- End-to-end data and query flow
- Embedding generation architecture
- Why Elasticsearch native inference is not used in this version
- Where inference happens today
- Exact index structure (all indices)
- Logs, views, and analytics model
- Keyword search vs hybrid search behavior
- Chunk configuration and model limits
- Why the UI shows images and where the image source actually comes from

All statements below are tied to concrete code paths from this repository.

---

## 2. System Architecture (High-Level)

The application has three logical layers:

1. Frontend (React/Vite)
2. Backend API (FastAPI + local embedding runtime)
3. Elasticsearch (Elastic Cloud deployment with four main indices)

### 2.1 Frontend responsibilities

- Sends search requests to backend API (`/api/search`, `/api/search/keyword`, `/api/search/image`, `/api/search/compare`)
- Shows result cards and thumbnails
- Calls analytics logging endpoints for click tracking
- Renders dashboards from Elasticsearch aggregations exposed by backend routes

### 2.2 Backend responsibilities

- Connects to Elastic Cloud using `cloud_id` + `api_key`
- Generates embeddings locally using `sentence-transformers`
- Executes Elasticsearch keyword, kNN, hybrid, and aggregation queries
- Logs search and interaction events into dedicated indices
- Provides content, related content, and recommendation APIs

### 2.3 Elasticsearch responsibilities

- Stores content metadata + vectors
- Executes BM25, kNN, and RRF rank fusion queries
- Stores search logs, click logs, and view logs
- Powers dashboard aggregations (hit rate, zero results, geo, trends, KPIs)

---

## 3. Configuration and Runtime Topology

Core config values are in `backend/config.py`.

### 3.1 Connection config

- `elastic_cloud_id`
- `elastic_api_key`

Backend client is built once and cached (`lru_cache`) in `backend/services/elasticsearch_service.py`.

### 3.2 Index names

- Content index: `cms-content`
- Search logs: `cms-search-logs`
- Click logs: `cms-click-logs`
- Content views: `cms-content-views`

### 3.3 Embedding model config

- Text model: `all-MiniLM-L6-v2`
- CLIP model: `clip-ViT-B-32`
- Text vector dims: `384`
- Image vector dims: `512`

These values must match index mapping dimensions for dense vectors.

---

## 4. Where Inference Happens Today

### 4.1 Current inference location

Inference does not happen inside Elasticsearch in this implementation.

Inference is executed in the backend process:

- `backend/models/embeddings.py`
  - loads `SentenceTransformer` models
  - encodes text and image inputs
  - returns vectors to routers/services

### 4.2 Effective inference endpoints in this architecture

There is no Elasticsearch `/_inference/...` call in this codebase.

The practical inference entrypoints are API routes that call local embedding code:

- `GET /api/search` (text embedding for hybrid search)
- `POST /api/search/image` (image bytes to CLIP embedding)
- `GET /api/search/text-to-image` (text to CLIP text embedding)

### 4.3 Why Elasticsearch native model inference is not being used

From the current code, this architecture is intentionally app-side inference:

1. Simpler deployment model for demo/prototype workflows
2. Model control stays in Python runtime
3. Direct compatibility with local data ingestion scripts

Tradeoff:

1. Inference scaling is tied to API compute layer
2. No ES-native model lifecycle orchestration in cluster
3. More moving parts to operate at production scale

---

## 5. End-to-End Ingestion Flow

Ingestion consists of three stages.

## 5.1 Stage A - metadata collection

Script: `backend/scripts/download_assets.py`

This script fetches metadata from:

- Unsplash
- Pexels
- Pixabay
- Freesound
- Wikipedia
- arXiv
- Gutenberg
- Internet Archive

It writes merged metadata into:

- `data/metadata/all_assets.json`

Important detail:

- The system stores remote media URLs (`url`, `thumbnail_url`, `preview_url`)
- It does not copy or persist media binaries into your local repo or Elasticsearch blob fields

## 5.2 Stage B - vector generation

Script: `backend/scripts/ingest_data.py`

For each asset:

1. Build text string: `title + description + tags`
2. Truncate text to first `512` characters
3. Batch-encode text with MiniLM (normalized embeddings, batch size 64)
4. For images with `thumbnail_url`, download image and create CLIP image embedding

Result:

- Every document gets `text_embedding`
- Image documents may additionally get `image_embedding`

## 5.3 Stage C - Elasticsearch indexing

Same script uses Elasticsearch bulk API:

- Chunk size for bulk indexing: `100` (`BATCH_SIZE = 100`)
- Index target: `cms-content`

Document stored includes metadata and vectors.

---

## 6. Index Design: Complete Structure

All mappings are defined in `backend/scripts/setup_indices.py`.

## 6.1 `cms-content` index

Purpose: primary retrieval index for content search and recommendation.

### Settings

- `number_of_shards: 2`
- `number_of_replicas: 1`

### Field groups

Text fields:

- `title` (text, analyzer `english`, plus `title.raw` keyword)
- `description` (text, analyzer `english`)

Structured keyword fields:

- `content_type`
- `tags`
- `category`
- `source`
- `author`
- `license`
- `url`
- `thumbnail_url`
- `preview_url`
- `file_type`
- `region`

Date:

- `created_at` (date)

Geo:

- `geo_location` (geo_point)

Numeric:

- `view_count`
- `download_count`
- `duration_seconds`
- `width`
- `height`

Vectors:

- `text_embedding` (dense_vector, dims 384, indexed, cosine)
- `image_embedding` (dense_vector, dims 512, indexed, cosine)

## 6.2 `cms-search-logs` index

Purpose: telemetry of search requests.

### Settings

- `number_of_shards: 1`
- `number_of_replicas: 1`

### Fields

- `query_text` (text + `query_text.raw` keyword)
- `search_type` (keyword: keyword/hybrid/image)
- `result_count` (integer)
- `response_time_ms` (integer)
- `user_id` (keyword)
- `session_id` (keyword)
- `region` (keyword)
- `geo` (geo_point)
- `timestamp` (date)
- `filters_used` (keyword)

## 6.3 `cms-click-logs` index

Purpose: clickthrough events.

### Settings

- `number_of_shards: 1`
- `number_of_replicas: 1`

### Fields

- `content_id`
- `query_text` (text + raw keyword)
- `position`
- `search_type`
- `user_id`
- `session_id`
- `region`
- `timestamp`

## 6.4 `cms-content-views` index

Purpose: content engagement and referrer tracking.

### Settings

- `number_of_shards: 1`
- `number_of_replicas: 1`

### Fields

- `content_id`
- `content_type`
- `category`
- `user_id`
- `session_id`
- `region`
- `referrer` (search/recommendation/direct)
- `time_spent_seconds`
- `timestamp`

---

## 7. Query Processing in Elasticsearch

## 7.1 Keyword search (BM25 only)

Path:

- API: `GET /api/search/keyword`
- Service: `keyword_search(...)`

ES behavior:

- `multi_match` over `title^3`, `description^2`, `tags^2`
- optional `bool.filter` for `content_type`, `category`, `region`
- no vectors

Use case:

- exact or near-exact lexical matching
- deterministic term relevance

## 7.2 Hybrid search (BM25 + kNN + RRF)

Path:

- API: `GET /api/search`
- Service: `hybrid_search(...)`

Pipeline:

1. Query text -> MiniLM embedding
2. ES query includes:
   - BM25 `multi_match`
   - kNN on `text_embedding`
3. ES rank fusion via `rank.rrf`

Current tuning:

- `k = size`
- `num_candidates = max(size * 5, 100)`
- `rank_window_size = 100`
- `rank_constant = 60`

Practical effect:

- captures semantic relevance even when terms do not overlap exactly
- can recover meaning-based matches keyword search misses

## 7.3 Image similarity search

Path:

- API: `POST /api/search/image`
- Service: `image_similarity_search(...)`

Pipeline:

1. Uploaded bytes -> CLIP image embedding
2. kNN query on `image_embedding`
3. Optional filters by content type

## 7.4 Text-to-image search (cross-modal)

Path:

- API: `GET /api/search/text-to-image`
- Service: `text_to_image_search(...)`

Pipeline:

1. Text query encoded by CLIP text encoder
2. kNN against `image_embedding`
3. hard filter `content_type = image`

---

## 8. Keyword vs Hybrid Search: Main Differences

## 8.1 Matching behavior

Keyword (BM25):

- driven by token overlap, tf-idf style term weighting, field boosts
- fails when user wording and document wording differ significantly

Hybrid (BM25 + vectors + RRF):

- combines lexical precision with semantic recall
- can retrieve conceptually related content with low lexical overlap

## 8.2 Relevance profile

Keyword:

- strong precision for exact matches
- weaker for paraphrases or intent-level searches

Hybrid:

- stronger recall and intent matching
- possible semantic false positives if vector space is broad

## 8.3 Operational profile

Keyword:

- lower compute overhead
- no embedding generation latency

Hybrid:

- extra embedding latency in API layer
- kNN and fusion adds query complexity
- better user experience for natural language discovery

## 8.4 UI support for comparison

`/api/search/compare` returns keyword and hybrid side-by-side plus IDs found only by hybrid.

This directly demonstrates semantic lift in your frontend compare page.

---

## 9. Logging, Views, and Analytics Data Model

## 9.1 Search logging

Search APIs call `_log(...)` in router:

- records query text, type, result count, latency, region, user/session, timestamp
- indexed into `cms-search-logs`

## 9.2 Click logging

Frontend `logClick(...)` posts to:

- `POST /api/analytics/log-click`

Backend indexes click events into:

- `cms-click-logs`

## 9.3 View logging

Content detail request `GET /api/content/{doc_id}` logs view event into:

- `cms-content-views`

## 9.4 Dashboard query behavior

Analytics endpoints use Elasticsearch aggregations:

- hit rate over time from search logs
- zero-result terms from `query_text.raw`
- region distribution + top queries
- engagement trends by category over date histograms
- content type breakdown and KPI rollups

Important implementation detail:

- dashboard "top content" currently sorts by `view_count` in `cms-content`, not by real-time aggregated views from `cms-content-views`

---

## 10. Chunking Configuration and Model Limits

You asked specifically about chunking. In this codebase, there is no multi-chunk document chunker (no paragraph windows, no overlap pipeline).

Current behavior is single text string per asset:

1. Concatenate title, description, tags
2. Truncate to 512 characters
3. Embed once

This is not RAG-style chunking.

## 10.1 Current limits in practice

- Long documents lose context beyond 512 chars
- One embedding per asset reduces granularity for long articles/papers/books
- No chunk-level retrieval means fewer precise long-form matches

## 10.2 Model constraints

- `all-MiniLM-L6-v2`:
  - 384-dim vectors
  - efficient, but lower semantic capacity than larger embedding models
- `clip-ViT-B-32`:
  - 512-dim image/text embedding space
  - good cross-modal baseline but not state-of-the-art for all domains

## 10.3 Elasticsearch constraints to keep aligned

- Index dense_vector dims must match model output dims
- Changing model family usually requires:
  - new mapping or new index
  - backfill/reindex with regenerated embeddings

---

## 11. Why the UI Shows Images (URL vs Imported Files)

The UI is showing URL-based thumbnails/images, not importing binaries into the frontend bundle.

### 11.1 What gets indexed

In metadata + ingestion, each asset stores URL fields:

- `url`
- `thumbnail_url`
- `preview_url`

### 11.2 What the UI renders

- `ResultCard` uses `src={result.thumbnail_url}`
- `RecommendationPanel` uses `src={r.thumbnail_url}`
- Content detail for images uses `src={content.url || content.thumbnail_url}`

Therefore:

1. Browser requests remote image URLs directly
2. Elasticsearch stores metadata links, not image blobs
3. "Image in UI" means remote render via URL, not local import

### 11.3 Why this matters operationally

- Fast implementation and smaller storage footprint
- But dependent on source URL availability and CORS/network reliability
- Broken source URLs produce missing thumbnails in UI

---

## 12. Elasticsearch Side: Behind-the-Scenes Mechanics

## 12.1 Hybrid query internals in this app

The hybrid query sends both lexical and vector retrieval in one ES search request, then uses built-in RRF rank phase.

Implications:

- Candidate generation comes from two relevance channels
- Final ordering rewards documents ranked well by either or both channels
- Reduces brittleness of pure BM25

## 12.2 Filter propagation

Filters from request params are added to:

- `bool.filter` for lexical branch
- kNN `filter` for vector branch

This keeps retrieval constrained consistently across both channels.

## 12.3 Source payload optimization

Search responses exclude vector fields:

- `_source.excludes: ["text_embedding", "image_embedding"]`

This reduces payload size and avoids transferring large vectors to UI.

## 12.4 Recommendation patterns

Two recommendation modes:

1. More Like This (`title`, `description`, `tags`)
2. Vector kNN recommendations using stored `text_embedding`

This dual strategy gives lexical and semantic recommendation options.

---

## 13. Known Gaps and Practical Improvements

## 13.1 Inference architecture gap

Current: local app inference.

If you need centralized Elasticsearch-native inference:

1. Deploy supported models/inference endpoints in ES
2. Move embedding generation from app scripts to ES inference pipeline or query-time inference endpoint
3. Validate parity in vector dims and similarity settings

## 13.2 Chunking gap

Current single-vector-per-asset design is weak for long documents.

Recommended:

1. Add chunk index (for chunk-level vectors)
2. Store parent asset ID + chunk text + chunk order
3. Retrieve chunks semantically, then collapse/group by parent asset

## 13.3 Analytics modeling gap

Current analytics mostly read search logs and view logs; click logs are underused in dashboards.

Recommended:

1. Add CTR dashboards (clicks / searches by query/type)
2. Add query reformulation funnels
3. Add content-type-level conversion metrics

## 13.4 Production hardening

Recommended:

1. ILM policies for log indices
2. index templates and aliases for versioned migrations
3. explicit refresh and bulk retry/backoff strategy
4. SLA metrics for embedding latency, kNN latency, and error rates

---

## 14. Exact Process Walkthrough (Step-by-Step)

This sequence describes one hybrid search request from user input to rendered results.

1. User enters query in UI Search page.
2. Frontend calls `GET /api/search?q=...`.
3. Backend router starts timer.
4. Backend generates MiniLM query embedding.
5. Backend sends Elasticsearch request with:
   - BM25 multi_match query
   - kNN on `text_embedding`
   - RRF rank fusion
   - optional filters
6. Elasticsearch returns ranked hits.
7. Backend formats hits, excluding vectors.
8. Backend logs search event to `cms-search-logs`.
9. Frontend renders cards with `thumbnail_url` images from source URLs.
10. If user clicks a result:
    - frontend sends click log
    - backend stores event in `cms-click-logs`
11. If user opens detail page:
    - backend logs content view in `cms-content-views`
12. Dashboard later aggregates these logs for KPIs and trends.

---

## 15. Answering Your Core Questions Directly

## 15.1 "Why are you not using models in Elasticsearch?"

Because the current implementation uses `sentence-transformers` in backend Python for embedding generation. There are no Elasticsearch inference API calls in this code.

## 15.2 "Where is the inference endpoint located?"

Inference is effectively inside backend code (`backend/models/embeddings.py`) and invoked by search routes. No ES inference endpoint is configured in this repo.

## 15.3 "How is the index structured, every index, logs, views?"

Four indices exist:

- `cms-content` for searchable assets + vectors
- `cms-search-logs` for query telemetry
- `cms-click-logs` for clicks
- `cms-content-views` for view events/engagement

Mappings and settings are defined in `backend/scripts/setup_indices.py`.

## 15.4 "Main difference between keyword vs hybrid?"

Keyword = BM25 lexical only.  
Hybrid = BM25 + vector kNN + RRF fusion.

Hybrid adds semantic retrieval and usually improves recall and intent matching.

## 15.5 "Chunk configuration and model limits?"

No true chunking pipeline exists now.  
There is only one combined text per asset, truncated to 512 characters before embedding. Model dims are 384 (text) and 512 (image/CLIP).

## 15.6 "Why UI showing images? imported or thumbnail URL?"

UI displays remote image URLs (`thumbnail_url` or `url`) retrieved from Elasticsearch metadata. It is not importing static local image assets into the frontend bundle.

---

## 16. Final Technical Summary

This project is a metadata-and-vector search platform where Elasticsearch is the retrieval and analytics core, while embedding inference currently runs in the FastAPI layer.

Elasticsearch is used strongly for:

- dense vector storage and ANN search
- lexical BM25 search
- hybrid rank fusion (RRF)
- telemetry/event storage
- analytics aggregations

The largest architectural distinction to understand is:

- search relevance is Elasticsearch-native,
- but embedding generation is application-native.

That is why you do not see Elasticsearch inference endpoint usage in the present codebase.
