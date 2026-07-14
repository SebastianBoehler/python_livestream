#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${GCLOUD_PROJECT_ID:-stellar-cumulus-437308-n4}"
ACCOUNT="${GCLOUD_ACCOUNT:-admin@hb-capital.app}"
REGION="${GCLOUD_REGION:-europe-west3}"
ZONE="${GCLOUD_ZONE:-europe-west3-a}"
INSTANCE_NAME="${GCLOUD_INSTANCE:-hb-youtube-stream}"
MACHINE_TYPE="${GCLOUD_MACHINE_TYPE:-c3-standard-4}"
NETWORK_NAME="${GCLOUD_NETWORK:-hb-livestream}"
SUBNET_NAME="${GCLOUD_SUBNET:-hb-livestream-eu3}"
SUBNET_RANGE="${GCLOUD_SUBNET_RANGE:-10.31.0.0/28}"
ROUTER_NAME="${GCLOUD_ROUTER:-hb-livestream-router-eu3}"
NAT_NAME="${GCLOUD_NAT:-hb-livestream-nat-eu3}"
REPOSITORY="${GCLOUD_REPOSITORY:-python-livestream-eu}"
SERVICE_ACCOUNT_NAME="${GCLOUD_SERVICE_ACCOUNT:-livestream-runner}"
SECRET_NAME="${GCLOUD_STREAM_SECRET:-youtube-livestream-key}"
STREAM_URL="${STREAM_URL:-https://www.hb-capital.app/livestream}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
AUTOSTART="${LIVESTREAM_AUTOSTART:-false}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/app:${IMAGE_TAG}"

retry() {
  local attempts="$1"
  local delay_seconds="$2"
  shift 2
  local attempt
  for ((attempt = 1; attempt <= attempts; attempt += 1)); do
    if "$@"; then
      return 0
    fi
    if ((attempt == attempts)); then
      return 1
    fi
    sleep "$delay_seconds"
  done
}

command -v gcloud >/dev/null || {
  echo "gcloud is required" >&2
  exit 1
}

export CLOUDSDK_CORE_ACCOUNT="$ACCOUNT"
export CLOUDSDK_CORE_PROJECT="$PROJECT_ID"

active_account="$(gcloud auth list --filter=status:ACTIVE --format='value(account)')"
if [[ "$active_account" != "$ACCOUNT" ]]; then
  echo "Expected active gcloud account $ACCOUNT, found ${active_account:-none}" >&2
  exit 1
fi

gcloud services enable \
  artifactregistry.googleapis.com \
  compute.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com \
  secretmanager.googleapis.com

if ! gcloud artifacts repositories describe "$REPOSITORY" --location="$REGION" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$REPOSITORY" \
    --location="$REGION" \
    --repository-format=docker \
    --description="HB Capital livestream runtime images"
fi

if ! gcloud iam service-accounts describe "$SERVICE_ACCOUNT_EMAIL" >/dev/null 2>&1; then
  gcloud iam service-accounts create "$SERVICE_ACCOUNT_NAME" \
    --display-name="HB livestream runtime"
fi

retry 12 5 gcloud artifacts repositories add-iam-policy-binding "$REPOSITORY" \
  --location="$REGION" \
  --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
  --role="roles/artifactregistry.reader" >/dev/null

for role in roles/logging.logWriter roles/monitoring.metricWriter; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="$role" \
    --condition=None >/dev/null
done

if ! gcloud secrets describe "$SECRET_NAME" >/dev/null 2>&1; then
  gcloud secrets create "$SECRET_NAME" --replication-policy=automatic
fi
gcloud secrets add-iam-policy-binding "$SECRET_NAME" \
  --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
  --role="roles/secretmanager.secretAccessor" >/dev/null

if ! gcloud compute networks describe "$NETWORK_NAME" >/dev/null 2>&1; then
  gcloud compute networks create "$NETWORK_NAME" --subnet-mode=custom
fi
if ! gcloud compute networks subnets describe "$SUBNET_NAME" --region="$REGION" >/dev/null 2>&1; then
  gcloud compute networks subnets create "$SUBNET_NAME" \
    --network="$NETWORK_NAME" \
    --region="$REGION" \
    --range="$SUBNET_RANGE" \
    --enable-private-ip-google-access
fi
if ! gcloud compute routers describe "$ROUTER_NAME" --region="$REGION" >/dev/null 2>&1; then
  gcloud compute routers create "$ROUTER_NAME" \
    --network="$NETWORK_NAME" \
    --region="$REGION"
fi
if ! gcloud compute routers nats describe "$NAT_NAME" --router="$ROUTER_NAME" --region="$REGION" >/dev/null 2>&1; then
  gcloud compute routers nats create "$NAT_NAME" \
    --router="$ROUTER_NAME" \
    --region="$REGION" \
    --auto-allocate-nat-external-ips \
    --nat-all-subnet-ip-ranges \
    --enable-logging \
    --log-filter=ERRORS_ONLY
fi

if ! gcloud compute firewall-rules describe hb-livestream-allow-iap-ssh >/dev/null 2>&1; then
  gcloud compute firewall-rules create hb-livestream-allow-iap-ssh \
    --network="$NETWORK_NAME" \
    --direction=INGRESS \
    --priority=1000 \
    --action=ALLOW \
    --rules=tcp:22 \
    --source-ranges=35.235.240.0/20 \
    --target-service-accounts="$SERVICE_ACCOUNT_EMAIL"
fi

if gcloud compute instances describe "$INSTANCE_NAME" --zone="$ZONE" >/dev/null 2>&1; then
  gcloud compute instances add-metadata "$INSTANCE_NAME" \
    --zone="$ZONE" \
    --metadata="enable-oslogin=TRUE,block-project-ssh-keys=TRUE,livestream-image=${IMAGE_URI},livestream-secret=${SECRET_NAME},livestream-url=${STREAM_URL},livestream-autostart=${AUTOSTART}" \
    --metadata-from-file="startup-script=${SCRIPT_DIR}/startup.sh" >/dev/null
  echo "Instance $INSTANCE_NAME already exists; metadata refreshed and runtime state left unchanged."
else
  gcloud compute instances create "$INSTANCE_NAME" \
    --zone="$ZONE" \
    --machine-type="$MACHINE_TYPE" \
    --network="$NETWORK_NAME" \
    --subnet="$SUBNET_NAME" \
    --no-address \
    --service-account="$SERVICE_ACCOUNT_EMAIL" \
    --scopes=cloud-platform \
    --image-family=cos-stable \
    --image-project=cos-cloud \
    --boot-disk-size=50GB \
    --boot-disk-type=pd-balanced \
    --maintenance-policy=MIGRATE \
    --restart-on-failure \
    --shielded-secure-boot \
    --shielded-vtpm \
    --shielded-integrity-monitoring \
    --metadata="enable-oslogin=TRUE,block-project-ssh-keys=TRUE,livestream-image=${IMAGE_URI},livestream-secret=${SECRET_NAME},livestream-url=${STREAM_URL},livestream-autostart=${AUTOSTART}" \
    --metadata-from-file="startup-script=${SCRIPT_DIR}/startup.sh"
fi

echo "Infrastructure ready."
echo "Image: $IMAGE_URI"
echo "VM: $INSTANCE_NAME ($ZONE, no public IP, autostart=$AUTOSTART)"
echo "The stream key secret exists, but this script does not upload or print a value."
