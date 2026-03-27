# Livestream Architecture

## Current Pipeline

The livestream now uses a buffered producer-consumer flow:

1. Research + script generation through `llm/router.py`
2. Chunked TTS generation through `tts/chunked.py`
3. Prepared segment buffering through `broadcast/pipeline.py`
4. Continuous playout through `broadcast/streaming.py`
5. Coverage memory persistence through `broadcast/memory.py`

This keeps playout independent from upstream model or TTS latency as long as the queue stays filled.

## Memory Layer

Runtime memory is stored under `memory/`:

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

## ADK Scaffold

`broadcast/adk_newsroom.py` contains an optional `google-adk` workflow scaffold:

- `ParallelAgent` for research desks
- `SequentialAgent` for dedupe, ranking, and script writing

Install ADK when you want to move from the current lightweight router to explicit multi-agent orchestration:

```bash
pip install google-adk
```

## Throughput Tuning

These settings matter most:

- `NEWS_SEGMENT_SECONDS`: shorter segments increase freshness
- `SEGMENT_BUFFER_SIZE`: larger queue increases resilience
- `TTS_PARALLELISM`: faster script-to-audio conversion
- `TTS_MAX_CHARS_PER_CHUNK`: smaller chunks reduce single-call latency
- `STREAM_FPS`: safe at `12` with Playwright capture on the current setup, higher for screen mode if the machine can sustain it
- `STREAM_CAPTURE_BACKEND`: `playwright` or `screen`

## 25 FPS Path

The current Playwright screenshot backend is not the right long-term path for `25 FPS`, so the project now includes a second capture mode:

```dotenv
STREAM_CAPTURE_BACKEND=screen
STREAM_FPS=25
STREAM_WIDTH=1920
STREAM_HEIGHT=1080
SCREEN_CAPTURE_DEVICE=3
SCREEN_BROWSER_FULLSCREEN=true
```

How it works:

1. Chromium is launched visibly instead of headless
2. FFmpeg captures the display through `avfoundation`
3. The audio, memory, and buffered segment pipeline stay unchanged

List available screen devices on macOS:

```bash
ffmpeg -f avfoundation -list_devices true -i ""
```

Recommended comparison workflow:

1. Run the stable path

```bash
STREAM_CAPTURE_BACKEND=playwright STREAM_FPS=12 python stream_url.py
```

2. Run the high-fps path

```bash
STREAM_CAPTURE_BACKEND=screen STREAM_FPS=25 python stream_url.py
```

3. Compare the logs:

- `FFmpeg progress: ... speed=... latency=...`
- `FFmpeg process stats: cpu=... rss=...`
- `Frames captured: ...` for the Playwright backend

Interpretation:

- `speed >= 1.0x` means FFmpeg is keeping up with realtime
- lower `latency` is better
- lower CPU at the same quality is better
- if `screen` mode holds `25 FPS` with `speed >= 1.0x`, it is the better ingest path
