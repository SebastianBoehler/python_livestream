# Livestream Architecture

## Current Pipeline

The livestream uses a buffered producer-consumer flow:

1. Load a show profile from `shows/*.toml`
2. Fetch current source material through `shows/sources.py`
3. Build a segment brief through `shows/briefs.py`
4. Generate a spoken script through `llm/router.py`
5. Render chunked TTS audio through `tts/chunked.py`
6. Render a local HTML studio page through `broadcast/studio_page.py`
7. Queue the prepared segment through `broadcast/pipeline.py`
8. Stream continuously through `broadcast/streaming.py`

This keeps playout independent from upstream model or TTS latency as long as the queue stays filled.

## Show Layer

The generalization layer now lives in `shows/`:

- `config.py` loads TOML show profiles
- `sources.py` resolves `rss`, `webpage`, `json`, and `manual` sources
- `briefs.py` rotates through the configured segment rundown
- `models.py` defines the shared show, source, and brief data structures

Each show profile controls:

- editorial framing
- branding and studio labels
- a default studio layout mode, for example `split` or `overlay`
- per-segment scene overrides, for example `clean-feed` or `transition`
- TTS voice
- source adapters
- segment sequence and default durations

This makes the runtime reusable for multiple niches without changing the main code path.

## Studio Page

The stream no longer depends on capturing an arbitrary external page directly.

Instead, each prepared segment gets its own generated studio page with:

- show branding
- current segment label
- headline and key talking points
- source cards from the fetched digest
- a running ticker assembled from source headlines
- an optional iframe reference panel

The layout layer can now switch scene styles per segment. The current HB Capital profile uses:

- `overlay` for the branded desk composition
- `clean-feed` for the raw HB Capital livestream page without channel chrome
- `transition` for short branded handoffs and interstitial moments

The browser capture backend still handles the final visual feed, but the visual composition is now controlled locally.

## Memory Layer

Runtime memory is stored under `memory/<show_id>/`:

- `session_index.jsonl`: one line per aired segment
- `topic_state.json`: repeated-topic counters and last-seen timestamps
- `rolling_context.md`: operator-readable digest of recent coverage

This memory is injected back into prompts to reduce repetitive framing and to bias updates toward materially new developments.

## Provider Routing

Provider selection is controlled by `NEWS_LLM_PROVIDER_ORDER`.

Examples:

```dotenv
NEWS_LLM_PROVIDER_ORDER=xai
NEWS_LLM_PROVIDER_ORDER=openrouter
NEWS_LLM_PROVIDER_ORDER=xai,openrouter
```

OpenRouter can be tuned with:

```dotenv
OPENROUTER_MODEL=openrouter/auto
OPENROUTER_MODELS=anthropic/claude-3.7-sonnet,google/gemini-2.5-pro
OPENROUTER_PROVIDER_ORDER=openai,together
OPENROUTER_PLUGINS=web
```

The router now forwards both a system instruction and a user prompt so each show can define its own host persona and editorial rules.

## Throughput Tuning

These settings matter most:

- `SHOW_ID`: selects a bundled show profile
- default bundled show id: `hb_capital`
- `SHOW_CONFIG_PATH`: points to any custom TOML profile
- `NEWS_SEGMENT_SECONDS`: optional global duration override for all segment types
- `SEGMENT_BUFFER_SIZE`: larger queue increases resilience
- `INTER_SEGMENT_MUSIC_SECONDS`: inserts a music-only gap after each aired segment
- `TTS_PARALLELISM`: faster script-to-audio conversion
- `TTS_MAX_CHARS_PER_CHUNK`: smaller chunks reduce single-call latency
- `STREAM_FPS`: safe at `12` with Playwright capture on the current setup, higher for screen mode if the machine can sustain it
- `STREAM_CAPTURE_BACKEND`: `playwright`, `screen`, or `virtual-screen`
- `STREAM_ORIENTATION`: `landscape` or `portrait`

## Vertical / Portrait Streaming

Portrait output is supported directly:

```dotenv
STREAM_ORIENTATION=portrait
```

Default frame sizes:

- `landscape`: `1280x720`
- `portrait`: `1080x1920`

You can still override with explicit `STREAM_WIDTH` and `STREAM_HEIGHT`.

Examples:

```bash
STREAM_ORIENTATION=portrait STREAM_CAPTURE_BACKEND=playwright python stream_url.py
```

```bash
STREAM_ORIENTATION=portrait STREAM_CAPTURE_BACKEND=screen STREAM_FPS=25 python stream_url.py
```

```bash
STREAM_ORIENTATION=portrait STREAM_CAPTURE_BACKEND=virtual-screen STREAM_FPS=25 python stream_url.py
```

Current scope:

- single portrait stream output is supported in this repo
- true dual-orientation publishing to YouTube is not yet implemented here

## 25 FPS Path

The current Playwright screenshot backend is not the right long-term path for `25 FPS`, so the project includes two high-fps paths:

```dotenv
STREAM_CAPTURE_BACKEND=screen
STREAM_FPS=25
STREAM_WIDTH=1920
STREAM_HEIGHT=1080
SCREEN_CAPTURE_DEVICE=3
SCREEN_BROWSER_FULLSCREEN=true
```

macOS `screen` mode:

1. Chromium is launched visibly instead of headless
2. FFmpeg captures the display through `avfoundation`
3. Because it captures a display device, it will include the whole desktop on that display

Linux/container `virtual-screen` mode:

```dotenv
STREAM_CAPTURE_BACKEND=virtual-screen
STREAM_FPS=25
STREAM_WIDTH=1920
STREAM_HEIGHT=1080
VIRTUAL_DISPLAY=:99
VIRTUAL_DISPLAY_SCREEN=0
VIRTUAL_DISPLAY_COLOR_DEPTH=24
STREAM_VIDEO_ENCODER=libx264
```

1. Xvfb starts an isolated display
2. Chromium launches inside that display
3. FFmpeg captures only that virtual display with `x11grab`
4. The audio, memory, and buffered segment pipeline stay unchanged

This is the recommended path for 24/7 VM or container operation because it does not expose the host desktop and does not depend on macOS-only video tooling.
It is Linux-only and will fail fast on macOS.

## Inter-Segment Music

You can insert an explicit music-only break between prepared segments:

```dotenv
INTER_SEGMENT_MUSIC_SECONDS=20
```

Behavior:

1. the aired segment finishes
2. a short silent WAV is generated locally
3. a dedicated intermission studio page is rendered
4. that silent track is streamed while the regular background music continues
5. the next queued segment starts after the break

`INTER_SEGMENT_DELAY_SECONDS` is also accepted as a legacy alias, but `INTER_SEGMENT_MUSIC_SECONDS` is the clearer setting name.
