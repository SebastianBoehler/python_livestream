# Continuous Terminal Stream

The continuous stream publishes one public terminal view without involving the LLM, TTS, show rotation, or segment pipeline.

## Operating Contract

- input: one HTTPS `STREAM_URL`
- capture: isolated `1920x1080` Xvfb display and kiosk Chromium
- frame rate: constant `30 FPS`
- video: `libx264`, H.264 High, 10 Mbps CBR, two B-frames, one reference frame, BT.709, `yuv420p`
- keyframes: every 60 frames, exactly two seconds
- audio: generated silent stereo AAC, 48 kHz, 128 kbps
- production output: RTMPS
- process model: one browser navigation with in-process FFmpeg reconnects

The application rejects a redirect to a different page before FFmpeg starts. The sole canonicalization exception is the same HTTPS path moving from a bare hostname to its `www` hostname. This prevents accidentally broadcasting a login screen when a private terminal route loses authentication. Use a deliberately public market-only URL for unattended streaming.

## Secret Handling

Prefer a mounted file:

```dotenv
STREAM_URL=https://www.hb-capital.app/livestream
YOUTUBE_STREAM_KEY_FILE=/run/secrets/youtube_stream_key
```

The file is read once, stripped, and rejected if it is missing, empty, malformed, or still a placeholder. If `YOUTUBE_STREAM_KEY_FILE` is configured, the direct environment fallback is not used.

For local development, this fallback is supported:

```dotenv
YOUTUBE_STREAM_KEY=your-real-development-key
```

The ingest path and query are redacted from command logs. Chromium, Xvfb, and FFmpeg receive a small allowlisted environment that excludes stream and provider credentials.

FFmpeg writes machine-readable progress every five seconds through the redacting log forwarder. The resulting container logs expose frame rate, speed, duplicated frames, and dropped frames for soak validation without printing the ingest key.

## Container Run

The default image runs as the unprivileged `stream` user and keeps the Chromium sandbox enabled:

```bash
docker build -t python-livestream .
docker run --rm \
  --shm-size=2g \
  -e STREAM_URL=https://www.hb-capital.app/livestream \
  -e YOUTUBE_STREAM_KEY_FILE=/run/secrets/youtube_stream_key \
  -v /secure/host/youtube_stream_key:/run/secrets/youtube_stream_key:ro \
  python-livestream
```

The mounted key must be readable by the container's unprivileged runtime user while remaining inaccessible to unrelated host users. Do not bake it into the image.

For long-running use, `docker compose up -d` adds `restart: unless-stopped`.
Unexpected FFmpeg exits reconnect after 1, 2, 5, and then at most 10 seconds
without restarting Chromium or Xvfb. The backoff resets after an FFmpeg session
runs for five minutes. Compose remains responsible for fatal configuration,
browser, virtual-display, or container failures.

## Local RTMP Smoke Endpoint

An explicit loopback RTMP output is allowed so the command can be tested without contacting YouTube:

```dotenv
STREAM_URL=http://localhost:3000/livestream
STREAM_OUTPUT_URL=rtmp://127.0.0.1:1935/live/test
```

Remote plaintext RTMP endpoints and remote plaintext page URLs are rejected. `STREAM_OUTPUT_URL` bypasses the YouTube key only when it passes this validation.

For a receiver-free VM burn-in, write a local FLV instead. The path must be absolute, end in `.flv`, and cannot be combined with `STREAM_OUTPUT_URL`:

```dotenv
STREAM_URL=http://localhost:3000/livestream
STREAM_OUTPUT_FILE=/tmp/terminal.flv
```

After stopping the burn-in, inspect the output:

```bash
ffprobe -v error -show_streams /tmp/terminal.flv
```

## Narrated Show

The previous narrated runtime remains independent:

```bash
python stream_url.py
docker compose --profile narrated up narrated
```

Its capture, segment, music, LLM, and TTS configuration has not been moved into the continuous terminal entry point.
