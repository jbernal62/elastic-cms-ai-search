#!/usr/bin/env bash
# ============================================================
#  GCS Bucket Setup for CMS AI Search — Asset Storage & CDN
#
#  Usage:
#    export GCS_BUCKET_NAME="cms-ai-assets-YOUR_PROJECT"
#    bash setup_gcs_bucket.sh
#
#  Prerequisites:
#    - gcloud CLI installed and authenticated
#    - A GCP project selected (gcloud config set project ...)
# ============================================================

set -euo pipefail

BUCKET_NAME="${GCS_BUCKET_NAME:?Set GCS_BUCKET_NAME env var first (e.g. cms-ai-assets-myproject)}"
LOCATION="${GCS_LOCATION:-us-central1}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "══════════════════════════════════════════════════════════"
echo "  CMS AI Search — GCS Bucket Setup"
echo "══════════════════════════════════════════════════════════"
echo "  Bucket : gs://${BUCKET_NAME}"
echo "  Region : ${LOCATION}"
echo ""

# 1. Create the bucket
echo "▸ Creating bucket..."
if gcloud storage buckets describe "gs://${BUCKET_NAME}" &>/dev/null; then
  echo "  Bucket already exists — skipping creation."
else
  gcloud storage buckets create "gs://${BUCKET_NAME}" \
    --location="${LOCATION}" \
    --uniform-bucket-level-access \
    --public-access-prevention=inherited
  echo "  Bucket created."
fi

# 2. Make objects publicly readable (CDN-like access)
echo "▸ Setting public read access..."
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET_NAME}" \
  --member=allUsers \
  --role=roles/storage.objectViewer \
  --quiet
echo "  Public access granted."

# 3. Apply CORS config
echo "▸ Applying CORS configuration..."
gcloud storage buckets update "gs://${BUCKET_NAME}" \
  --cors-file="${SCRIPT_DIR}/gcs_cors.json"
echo "  CORS applied."

# 4. Enable GCS notifications to Eventarc (for Cloud Functions gen2)
# Note: Eventarc handles this automatically when deploying the Cloud Function
# with --trigger-event-filters. No manual notification setup needed for gen2.

echo ""
echo "✔ Bucket gs://${BUCKET_NAME} is ready."
echo ""
echo "  Public URL pattern:"
echo "    https://storage.googleapis.com/${BUCKET_NAME}/<object-path>"
echo ""
echo "  Upload test:"
echo "    gsutil cp test-image.jpg gs://${BUCKET_NAME}/images/"
echo "    curl -I https://storage.googleapis.com/${BUCKET_NAME}/images/test-image.jpg"
echo ""
