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
- `STREAM_FPS`: safe at `12` with Playwright capture on the current setup

## 25 FPS Path

The current Playwright screenshot backend is not the right long-term path for `25 FPS`.

To reach that territory, add a separate capture backend:

1. visible Chromium window
2. native screen capture through FFmpeg (`avfoundation` on macOS)
3. same audio/buffering pipeline
4. runtime switch such as `STREAM_CAPTURE_BACKEND=playwright|screen`

That preserves the new buffering and memory layers while replacing only the visual capture path.
