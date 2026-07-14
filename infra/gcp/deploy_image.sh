#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${GCLOUD_PROJECT_ID:-stellar-cumulus-437308-n4}"
ACCOUNT="${GCLOUD_ACCOUNT:-admin@hb-capital.app}"
REGION="${GCLOUD_REGION:-europe-west3}"
REPOSITORY="${GCLOUD_REPOSITORY:-python-livestream-eu}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/app:${IMAGE_TAG}"

export CLOUDSDK_CORE_ACCOUNT="$ACCOUNT"
export CLOUDSDK_CORE_PROJECT="$PROJECT_ID"

if gcloud meta list-files-for-upload | grep -qx '.env'; then
  echo "Refusing to build: .env would be uploaded to Cloud Build" >&2
  exit 1
fi

gcloud builds submit --tag="$IMAGE_URI" .
echo "$IMAGE_URI"
