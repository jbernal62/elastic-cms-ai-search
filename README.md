# Elastic CMS AI Search

A full-stack AI-powered content management and search platform built with **Elasticsearch**, **SentenceTransformers**, **React**, and **Google Cloud Platform**. Supports hybrid text search, image similarity search, and an event-driven asset ingestion pipeline.

## Architecture

```
                          +-------------------+
                          |   React Frontend  |
                          |  (Vite + Tailwind)|
                          +--------+----------+
                                   |
                                   v
                          +-------------------+
                          |  FastAPI Backend   |
                          |  (Python 3.11)     |
                          +--------+----------+
                                   |
                    +--------------+--------------+
                    |                             |
                    v                             v
           +----------------+          +-------------------+
           | Elasticsearch  |          | GCS Asset Bucket  |
           | (Elastic Cloud)|          | (Public / CDN)    |
           +----------------+          +--------+----------+
                                                |
                                       GCS finalize event
                                                |
                                                v
                                    +------------------------+
                                    | Asset Ingestion Service|
                                    | (Cloud Run + Eventarc) |
                                    +------------------------+
```

### Key Components

| Component | Tech Stack | Description |
|-----------|-----------|-------------|
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS | Search UI, image search, content comparison, asset management, analytics dashboard |
| **Backend** | FastAPI, Uvicorn, Python 3.11 | REST API for search, content retrieval, analytics, and asset management |
| **Search Engine** | Elasticsearch (Elastic Cloud) | Hybrid search with BM25 + kNN + RRF, dense vector embeddings |
| **Embeddings** | SentenceTransformers | `all-MiniLM-L6-v2` (384D text) and `clip-ViT-B-32` (512D image) |
| **Asset Pipeline** | Cloud Run, Eventarc, GCS | Event-driven: upload to GCS triggers automatic embedding and indexing |
| **Deployment** | Google Cloud Run, Artifact Registry | Containerized services with pre-cached ML models |

## Features

- **Hybrid Search** — Combines BM25 full-text search with semantic vector search using Reciprocal Rank Fusion (RRF)
- **Image Similarity Search** — Upload an image or provide a URL to find visually similar content using CLIP embeddings
- **Content Comparison** — Side-by-side comparison of search results from different strategies
- **Asset Management** — Drag-and-drop upload of images/documents to GCS with automatic embedding and indexing
- **Analytics Dashboard** — Search logs, click-through tracking, and content performance metrics
- **Content Detail Pages** — Rich content pages with related content recommendations

## Project Structure

```
cms-ai-search/
├── backend/
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Configuration (env vars / .env)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── models/
│   │   └── embeddings.py       # SentenceTransformer embedding logic
│   ├── routers/
│   │   ├── search.py           # /api/search endpoints
│   │   ├── content.py          # /api/content endpoints
│   │   ├── analytics.py        # /api/analytics endpoints
│   │   └── assets.py           # /api/assets endpoints (upload, list, delete)
│   ├── services/
│   │   └── elasticsearch_service.py  # ES client, index management, queries
│   └── scripts/
│       ├── setup_gcs_bucket.sh       # One-time GCS bucket creation
│       └── gcs_cors.json             # CORS config for the bucket
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf              # Nginx config with API proxy
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── App.tsx             # Main app with routing
│       ├── api/
│       │   └── client.ts       # API client (search, content, assets)
│       └── pages/
│           ├── SearchPage.tsx
│           ├── ImageSearchPage.tsx
│           ├── ComparisonPage.tsx
│           ├── ContentDetailPage.tsx
│           ├── AssetsPage.tsx
│           └── DashboardPage.tsx
├── cloud_functions/
│   └── asset_ingestion/
│       ├── main.py             # CloudEvent handler: embed + index on GCS upload
│       ├── requirements.txt
│       └── Dockerfile          # Pre-caches ML models for fast cold starts
├── data/                       # Ingestion scripts and sample data
├── docs/                       # Technical architecture documentation
└── .gitignore
```

## Prerequisites

- **Python 3.11+**
- **Node.js 20+**
- **Elasticsearch** — An Elastic Cloud deployment (or local cluster)
- **Google Cloud SDK** — For GCS bucket and Cloud Run deployment
- **Docker** (optional) — For local container builds

## Local Development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
ELASTIC_CLOUD_ID=your-deployment:base64...
ELASTIC_API_KEY=your-api-key
GCS_BUCKET_NAME=your-bucket-name
EOF

uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs on `http://localhost:5173` and proxies API requests to the backend on port 8000.

## GCP Deployment

### 1. Set Up GCS Bucket

```bash
cd backend/scripts
chmod +x setup_gcs_bucket.sh
./setup_gcs_bucket.sh
```

This creates a public GCS bucket with CORS enabled for asset uploads.

### 2. Build and Deploy Backend

```bash
# Build Docker image with Cloud Build
gcloud builds submit ./backend \
  --tag us-central1-docker.pkg.dev/YOUR_PROJECT/YOUR_REPO/cms-backend:latest

# Deploy to Cloud Run
gcloud run deploy cms-backend \
  --image us-central1-docker.pkg.dev/YOUR_PROJECT/YOUR_REPO/cms-backend:latest \
  --region us-central1 \
  --memory 4Gi --cpu 2 \
  --set-env-vars "ELASTIC_CLOUD_ID=...,ELASTIC_API_KEY=...,GCS_BUCKET_NAME=..." \
  --allow-unauthenticated
```

### 3. Build and Deploy Frontend

```bash
gcloud builds submit ./frontend \
  --tag us-central1-docker.pkg.dev/YOUR_PROJECT/YOUR_REPO/cms-frontend:latest

gcloud run deploy cms-frontend \
  --image us-central1-docker.pkg.dev/YOUR_PROJECT/YOUR_REPO/cms-frontend:latest \
  --region us-central1 \
  --set-env-vars "BACKEND_URL=https://YOUR-BACKEND-URL" \
  --allow-unauthenticated
```

### 4. Deploy Asset Ingestion Service

The ingestion service runs as a Cloud Run service triggered by GCS events via Eventarc.

```bash
# Build image with pre-cached ML models
gcloud builds submit ./cloud_functions/asset_ingestion \
  --tag us-central1-docker.pkg.dev/YOUR_PROJECT/YOUR_REPO/cms-asset-ingestion:latest

# Deploy to Cloud Run
gcloud run deploy cms-asset-ingestion \
  --image us-central1-docker.pkg.dev/YOUR_PROJECT/YOUR_REPO/cms-asset-ingestion:latest \
  --region us-central1 \
  --memory 4Gi --cpu 2 --timeout 300 \
  --min-instances 0 --max-instances 10 --concurrency 1 \
  --set-env-vars "ELASTIC_CLOUD_ID=...,ELASTIC_API_KEY=...,GCS_BUCKET_NAME=...,TRANSFORMERS_OFFLINE=1" \
  --no-allow-unauthenticated

# Create Eventarc trigger
gcloud eventarc triggers create cms-asset-ingestion-trigger \
  --location us-central1 \
  --destination-run-service cms-asset-ingestion \
  --destination-run-region us-central1 \
  --event-filters "type=google.cloud.storage.object.v1.finalized" \
  --event-filters "bucket=YOUR_BUCKET_NAME" \
  --service-account YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com
```

## Elasticsearch Index

The `cms-content` index stores all content with the following key fields:

| Field | Type | Description |
|-------|------|-------------|
| `title` | text | Content title (BM25 searchable) |
| `description` | text | Content description |
| `text_embedding` | dense_vector (384D) | MiniLM text embedding |
| `image_embedding` | dense_vector (512D) | CLIP image embedding |
| `content_type` | keyword | `image`, `video`, `audio`, `document` |
| `source` | keyword | Origin (`unsplash`, `pexels`, `gcs-upload`, etc.) |
| `thumbnail_url` | keyword | URL for thumbnail display |
| `tags` | keyword[] | Content tags for filtering |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ELASTIC_CLOUD_ID` | Yes | Elastic Cloud deployment ID |
| `ELASTIC_API_KEY` | Yes | Elastic Cloud API key |
| `GCS_BUCKET_NAME` | For assets | GCS bucket name for asset uploads |
| `CORS_ORIGINS` | No | Allowed CORS origins (default: localhost) |
| `UNSPLASH_ACCESS_KEY` | No | Unsplash API key for data ingestion |
| `PEXELS_API_KEY` | No | Pexels API key for data ingestion |

## License

MIT
