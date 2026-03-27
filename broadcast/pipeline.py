"""Buffered segment preparation."""

from __future__ import annotations

import time
from pathlib import Path

from broadcast.memory import BroadcastMemoryStore
from broadcast.models import PreparedSegment
from llm.router import generate_news_content
from tts.chunked import synthesize_script_to_file
from utils import get_audio_duration


def prepare_segment(
    *,
    news_prompt: str,
    memory_store: BroadcastMemoryStore,
    tts_dir: str | Path,
    tts_generator,
    ffmpeg_path: str,
    target_duration_seconds: int,
    tts_parallelism: int,
    tts_max_chars_per_chunk: int,
) -> PreparedSegment:
    memory_context = memory_store.build_prompt_context()
    generated_news = generate_news_content(
        base_prompt=news_prompt,
        memory_context=memory_context,
        target_duration_seconds=target_duration_seconds,
    )
    segment_id = f"segment_{int(time.time())}"
    audio_path = Path(tts_dir) / f"{segment_id}.wav"
    synthesize_script_to_file(
        script=generated_news.script,
        output_file=str(audio_path),
        tts_generator=tts_generator,
        ffmpeg_path=ffmpeg_path,
        parallelism=tts_parallelism,
        max_chars_per_chunk=tts_max_chars_per_chunk,
    )
    duration_seconds = get_audio_duration(str(audio_path), ffmpeg_path)
    return PreparedSegment(
        segment_id=segment_id,
        script=generated_news.script,
        provider_name=generated_news.provider_name,
        audio_path=audio_path,
        target_duration_seconds=target_duration_seconds,
        actual_audio_duration_seconds=duration_seconds,
    )

