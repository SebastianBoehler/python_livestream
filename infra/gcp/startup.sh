#!/usr/bin/env bash
set -euo pipefail

METADATA_ROOT="http://metadata.google.internal/computeMetadata/v1"
METADATA_HEADER="Metadata-Flavor: Google"

metadata() {
  curl --fail --silent --show-error -H "$METADATA_HEADER" "$METADATA_ROOT/$1"
}

IMAGE_URI="$(metadata instance/attributes/livestream-image)"
AUTOSTART="$(metadata instance/attributes/livestream-autostart)"
PROJECT_ID="$(metadata project/project-id)"

install -d -m 0755 /var/lib/hb-livestream
install -d -m 0700 /run/hb-livestream

cat >/var/lib/hb-livestream/prepare.sh <<'PREPARE'
#!/usr/bin/env bash
set -euo pipefail

METADATA_ROOT="http://metadata.google.internal/computeMetadata/v1"
METADATA_HEADER="Metadata-Flavor: Google"
metadata() {
  curl --fail --silent --show-error -H "$METADATA_HEADER" "$METADATA_ROOT/$1"
}

PROJECT_ID="$(metadata project/project-id)"
IMAGE_URI="$(metadata instance/attributes/livestream-image)"
SECRET_NAME="$(metadata instance/attributes/livestream-secret)"
STREAM_URL="$(metadata instance/attributes/livestream-url)"
TOKEN_JSON="$(metadata instance/service-accounts/default/token)"
ACCESS_TOKEN="$(printf '%s' "$TOKEN_JSON" | tr -d '\n' | sed -n 's/.*"access_token"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')"

if [[ -z "$ACCESS_TOKEN" ]]; then
  echo "Unable to obtain a VM service-account access token" >&2
  exit 1
fi

SECRET_JSON="$(curl --fail --silent --show-error \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  "https://secretmanager.googleapis.com/v1/projects/${PROJECT_ID}/secrets/${SECRET_NAME}/versions/latest:access")"
SECRET_DATA="$(printf '%s' "$SECRET_JSON" | tr -d '\n' | sed -n 's/.*"data"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')"

umask 077
install -d -m 0700 /run/hb-livestream
printf '%s' "$SECRET_DATA" | base64 --decode >/run/hb-livestream/youtube.key
test -s /run/hb-livestream/youtube.key

cat >/run/hb-livestream/runtime.env <<ENV
YOUTUBE_STREAM_KEY_FILE=/run/secrets/youtube.key
STREAM_URL=$STREAM_URL
ENV

REGISTRY_HOST="${IMAGE_URI%%/*}"
printf '%s' "$ACCESS_TOKEN" | docker login \
  --username oauth2accesstoken \
  --password-stdin \
  "https://${REGISTRY_HOST}" >/dev/null
docker pull "$IMAGE_URI"
docker logout "$REGISTRY_HOST" >/dev/null 2>&1 || true
PREPARE
chmod 0750 /var/lib/hb-livestream/prepare.sh

cat >/etc/systemd/system/hb-livestream.service <<UNIT
[Unit]
Description=HB Capital market livestream
After=docker.service network-online.target
Wants=network-online.target
Requires=docker.service

[Service]
Type=simple
ExecStartPre=/bin/bash /var/lib/hb-livestream/prepare.sh
ExecStartPre=-/usr/bin/docker rm -f hb-youtube-stream
ExecStart=/usr/bin/docker run --rm --name hb-youtube-stream \\
  --shm-size=2g \\
  --env-file=/run/hb-livestream/runtime.env \\
  --mount=type=bind,src=/run/hb-livestream/youtube.key,dst=/run/secrets/youtube.key,readonly \\
  --log-driver=gcplogs \\
  --log-opt=gcp-project=$PROJECT_ID \\
  $IMAGE_URI
ExecStop=/usr/bin/docker stop --time=20 hb-youtube-stream
Restart=always
RestartSec=10
TimeoutStartSec=0
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
if [[ "$AUTOSTART" == "true" ]]; then
  systemctl enable --now hb-livestream.service
else
  systemctl disable hb-livestream.service >/dev/null 2>&1 || true
  echo "hb-livestream.service installed but intentionally not started"
fi
