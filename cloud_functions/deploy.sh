#!/usr/bin/env bash
# ============================================================
#  Deploy the GCS Asset Ingestion Cloud Function (gen2)
#
#  Usage:
#    export GCS_BUCKET_NAME="cms-ai-assets-YOUR_PROJECT"
#    export ELASTIC_CLOUD_ID="your-cloud-id"
#    export ELASTIC_API_KEY="your-api-key"
#    bash deploy.sh
#
#  Prerequisites:
#    - gcloud CLI authenticated with a project selected
#    - The GCS bucket already created (run setup_gcs_bucket.sh first)
#    - Eventarc API and Cloud Functions API enabled
# ============================================================

set -euo pipefail

BUCKET_NAME="${GCS_BUCKET_NAME:?Set GCS_BUCKET_NAME env var}"
CLOUD_ID="${ELASTIC_CLOUD_ID:?Set ELASTIC_CLOUD_ID env var}"
API_KEY="${ELASTIC_API_KEY:?Set ELASTIC_API_KEY env var}"
REGION="${GCS_LOCATION:-us-central1}"
FUNCTION_NAME="${FUNCTION_NAME:-cms-asset-ingestion}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "══════════════════════════════════════════════════════════"
echo "  Deploying Cloud Function: ${FUNCTION_NAME}"
echo "══════════════════════════════════════════════════════════"
echo "  Bucket : gs://${BUCKET_NAME}"
echo "  Region : ${REGION}"
echo ""

# Enable required APIs
echo "▸ Enabling required APIs..."
gcloud services enable \
  cloudfunctions.googleapis.com \
  cloudbuild.googleapis.com \
  eventarc.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  --quiet

echo "▸ Deploying function..."
gcloud functions deploy "${FUNCTION_NAME}" \
  --gen2 \
  --runtime=python311 \
  --region="${REGION}" \
  --source="${SCRIPT_DIR}/asset_ingestion" \
  --entry-point=process_asset \
  --trigger-event-filters="type=google.cloud.storage.object.v1.finalized" \
  --trigger-event-filters="bucket=${BUCKET_NAME}" \
  --memory=4Gi \
  --timeout=300s \
  --min-instances=0 \
  --max-instances=10 \
  --set-env-vars="ELASTIC_CLOUD_ID=${CLOUD_ID},ELASTIC_API_KEY=${API_KEY},GCS_BUCKET_NAME=${BUCKET_NAME}"

echo ""
echo "✔ Cloud Function '${FUNCTION_NAME}' deployed successfully."
echo ""
echo "  Test it by uploading a file:"
echo "    gsutil cp test-image.jpg gs://${BUCKET_NAME}/images/"
echo ""
echo "  Check logs:"
echo "    gcloud functions logs read ${FUNCTION_NAME} --region=${REGION} --gen2"
echo ""
