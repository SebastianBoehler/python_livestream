# Python Livestream Toolkit

Python Livestream Toolkit automates a news-style YouTube livestream from a web page or visual source, generates fresh bulletin scripts with an LLM, renders narration with TTS, mixes background music, and publishes continuously through FFmpeg.

The project is optimized around a buffered broadcast pipeline rather than a single blocking loop. That makes it suitable for continuous crypto, macro, or market commentary streams where research, narration, and playout need to overlap cleanly.

## What It Does

- Streams a URL or visual source directly to YouTube Live
- Buffers prepared news segments ahead of playout
- Persists recent coverage memory to reduce repetition
- Routes script generation across xAI, Gemini, or OpenRouter
- Supports stable screenshot capture, macOS screen capture, and isolated virtual-display capture for containers
- Mixes continuous background music under narrated bulletins
- Supports optional music-only breaks between segments
- Runs well on low-cost Linux VMs with the default slim container image

## Capture Modes

| Backend | Best for | Notes |
| --- | --- | --- |
| `playwright` | stability | Default path, typically around `12 FPS` |
| `screen` | local macOS experiments | Captures an entire display via `avfoundation` |
| `virtual-screen` | Docker or Linux VM | Captures only an isolated Xvfb-hosted Chromium session |

If you do not want to stream your real desktop, use `virtual-screen` on Linux or in the provided container image.

## Architecture

The runtime is split into small modules:

1. `llm/` generates bulletin scripts
2. `tts/` renders narration
3. `broadcast/pipeline.py` prepares queued segments
4. `broadcast/streaming.py` handles FFmpeg playout
5. `broadcast/memory.py` records prior coverage context
6. `broadcast/intermission.py` inserts optional music-only gaps

More detail lives in [docs/architecture.md](/Users/sebastianboehler/Documents/GitHub/python_livestream/docs/architecture.md).

## Quick Start

### Local install

```bash
git clone https://github.com/SebastianBoehler/python_livestream.git
cd python_livestream
pip install -r requirements.txt
playwright install
```

`requirements.txt` includes the full local-model stack. The default container intentionally uses the lighter [requirements-stream.txt](/Users/sebastianboehler/Documents/GitHub/python_livestream/requirements-stream.txt) instead.

### Environment

Copy [.env.example](/Users/sebastianboehler/Documents/GitHub/python_livestream/.env.example) to `.env` and set the values you need.

Common settings:

```dotenv
YOUTUBE_STREAM_KEY=<your-youtube-stream-key>
STREAM_URL=https://example.com
NEWS_SEGMENT_SECONDS=180
SEGMENT_BUFFER_SIZE=3
STREAM_CAPTURE_BACKEND=playwright
STREAM_ORIENTATION=landscape
STREAM_FPS=12
INTER_SEGMENT_MUSIC_SECONDS=0
NEWS_LLM_PROVIDER_ORDER=xai
```

Provider credentials depend on which services you use:

- `GEMINI_API_KEY`
- `XAI_API_KEY`
- `OPENROUTER_API_KEY`
- `ELEVENLABS_API_KEY`
- `HF_TOKEN`

### Run the livestream

```bash
python stream_url.py
```

### Run portrait mode

```bash
STREAM_ORIENTATION=portrait python stream_url.py
```

### Add a music-only break between bulletins

```bash
INTER_SEGMENT_MUSIC_SECONDS=20 python stream_url.py
```

`INTER_SEGMENT_DELAY_SECONDS` is still accepted as a compatibility alias.

### Use isolated browser capture

```bash
STREAM_CAPTURE_BACKEND=virtual-screen STREAM_FPS=25 python stream_url.py
```

`virtual-screen` is Linux-only and is the recommended mode for long-running container or VM deployment.

## Docker

The default [Dockerfile](/Users/sebastianboehler/Documents/GitHub/python_livestream/Dockerfile) is optimized for continuous streaming on lightweight Linux hosts:

- base image: `python:3.11-slim-bookworm`
- isolated Chromium capture via Xvfb
- Linux-safe `libx264` encoding by default
- only streaming/runtime dependencies installed

Build and run it:

```bash
docker build -t python-livestream .
docker run --env-file .env python-livestream
```

For persistent operation:

```bash
docker compose up -d
```

The included [docker-compose.yml](/Users/sebastianboehler/Documents/GitHub/python_livestream/docker-compose.yml) defaults `STREAM_CAPTURE_BACKEND` to `virtual-screen` and uses `restart: unless-stopped`.

### GPU image

If you want a heavier local-model image for GPU-backed TTS experiments, use [Dockerfile.gpu](/Users/sebastianboehler/Documents/GitHub/python_livestream/Dockerfile.gpu):

```bash
docker build -f Dockerfile.gpu -t python-livestream-gpu .
```

## Repository Layout

```text
broadcast/   streaming, capture backends, memory, intermissions
docs/        architecture notes
llm/         provider routing and prompt generation
tts/         TTS backends and chunking
tests/       unit tests for core streaming behavior
```

## Testing

Run the baseline checks before opening a PR:

```bash
python -m py_compile $(git ls-files '*.py')
python -m unittest discover -s tests -p 'test_*.py' -v
```

CI also builds the default Docker image to catch container regressions early.

## Contributing

See [CONTRIBUTING.md](/Users/sebastianboehler/Documents/GitHub/python_livestream/CONTRIBUTING.md) for workflow and expectations.

In short:

- keep changes modular
- avoid large files and duplicated logic
- add or update tests for behavioral changes
- document operator-facing config changes

## Security

If you discover a security issue, see [SECURITY.md](/Users/sebastianboehler/Documents/GitHub/python_livestream/SECURITY.md).

## License

This project is licensed under the MIT License. See [LICENSE](/Users/sebastianboehler/Documents/GitHub/python_livestream/LICENSE).
