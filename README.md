# Python Livestream Toolkit

Python Livestream Toolkit automates a YouTube livestream by collecting topic-specific source material, generating spoken scripts with an LLM, rendering narration with TTS, composing a branded local studio page, and publishing continuously through FFmpeg.

The runtime is built around a buffered producer-consumer pipeline so research, narration, and playout can overlap cleanly. It now supports reusable show profiles, which makes it useful for crypto, AI, creator economy, or any niche that can be expressed as a set of sources plus an editorial format.

## What It Does

- Loads a reusable show profile from `shows/*.toml`
- Pulls source material from `rss`, `webpage`, `json`, or `manual` adapters
- Builds a local browser-based studio page with headline, source cards, ticker, and branding
- Buffers prepared audio segments ahead of playout
- Persists rolling memory per show to reduce repetition
- Routes script generation across xAI, Gemini, or OpenRouter
- Supports stable screenshot capture, macOS screen capture, and isolated virtual-display capture for containers
- Mixes continuous background music under narrated segments
- Supports optional music-only breaks between segments

## Show Profiles

Each show profile defines:

- topic and editorial framing
- host voice and branding
- source adapters
- studio labels and optional iframe reference panel
- segment rundown, for example headline, deep dive, and recap

Included examples:

- `shows/hb_capital.toml`
- `shows/crypto_markets.toml`
- `shows/ai_roundup.toml`
- `shows/creator_watch.toml`

## Capture Modes

| Backend | Best for | Notes |
| --- | --- | --- |
| `playwright` | stability | Default path, typically around `12 FPS` |
| `screen` | local macOS experiments | Captures an entire display via `avfoundation` |
| `virtual-screen` | Docker or Linux VM | Captures only an isolated Xvfb-hosted Chromium session |

If you do not want to stream your real desktop, use `virtual-screen` on Linux or in the provided container image.

## Architecture

The runtime is split into small modules:

1. `shows/` loads show configs, source adapters, and segment briefs
2. `llm/` builds prompts and routes script generation
3. `tts/` renders narration
4. `broadcast/pipeline.py` prepares queued segments and local studio pages
5. `broadcast/streaming.py` handles FFmpeg playout
6. `broadcast/memory.py` records prior coverage context per show

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
SHOW_ID=hb_capital
STREAM_URL=https://example.com
SEGMENT_BUFFER_SIZE=3
STREAM_CAPTURE_BACKEND=playwright
STREAM_ORIENTATION=landscape
STREAM_FPS=12
INTER_SEGMENT_MUSIC_SECONDS=0
NEWS_LLM_PROVIDER_ORDER=xai
```

Notes:

- `SHOW_ID` selects a profile in `shows/`
- `SHOW_CONFIG_PATH` can point to any custom TOML file
- `STREAM_URL` is only required if your selected show profile references it
- `NEWS_SEGMENT_SECONDS` is still supported as a global duration override
- `hb_capital` uses an overlay-first studio layout built to keep the HB livestream page visible on program

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

### Switch to a different show

```bash
SHOW_ID=ai_roundup python stream_url.py
```

### Use a custom show file

```bash
SHOW_CONFIG_PATH=/absolute/path/to/my_show.toml python stream_url.py
```

### Run portrait mode

```bash
STREAM_ORIENTATION=portrait python stream_url.py
```

### Add a music-only break between segments

```bash
INTER_SEGMENT_MUSIC_SECONDS=20 python stream_url.py
```

`INTER_SEGMENT_DELAY_SECONDS` is still accepted as a compatibility alias.

### Use isolated browser capture

```bash
STREAM_CAPTURE_BACKEND=virtual-screen STREAM_FPS=25 python stream_url.py
```

`virtual-screen` is Linux-only and is the recommended mode for long-running container or VM deployment.

## Show Config Example

```toml
show_id = "my_show"
title = "Niche Desk"
tagline = "Automated coverage for one clear audience."
host_name = "Desk"
host_role = "Operator anchor"
description = "Explain what changed and why it matters."
base_prompt = "Cover the most relevant developments from the last 24 hours."
llm_system_instruction = "You are a sharp and concise anchor."
tts_voice = "Charon"

[branding]
primary_color = "#93f5d8"
accent_color = "#f6c35c"
background_start = "#04141a"
background_end = "#11172a"
card_background = "rgba(8, 18, 31, 0.78)"
text_color = "#f4f7fb"
muted_text_color = "#9bb4c8"

[studio]
label = "Live Desk"
strapline = "Source-driven coverage"
ticker_prefix = "Radar"
iframe_url = ""
layout_mode = "split"

[[sources]]
kind = "rss"
name = "Google News Topic"
url = "https://news.google.com/rss/search?q=my+topic+when:1d&hl=en-US&gl=US&ceid=US:en"
limit = 5

[[sources]]
kind = "manual"
name = "Editorial Guardrails"
text = "Stay concrete and explain implications."

[[segments]]
kind = "headline"
label = "Top Setup"
instructions = "Open with the biggest development."
duration_seconds = 180
```

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
broadcast/   streaming, capture backends, memory, intermissions, studio pages
docs/        architecture notes
llm/         provider routing and prompt generation
shows/       show configs, source adapters, segment brief helpers
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
