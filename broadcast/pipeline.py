"""Buffered segment preparation."""

from __future__ import annotations

import time
from pathlib import Path

from broadcast.memory import BroadcastMemoryStore
from broadcast.models import PreparedSegment
from broadcast.studio_page import render_segment_page
from llm.prompts import build_system_instruction, build_user_prompt
from llm.router import generate_script_content
from shows.models import SegmentBrief, ShowConfig
from tts.chunked import synthesize_script_to_file
from utils import get_audio_duration


def prepare_segment(
    *,
    show_config: ShowConfig,
    brief: SegmentBrief,
    memory_store: BroadcastMemoryStore,
    tts_dir: str | Path,
    studio_pages_dir: str | Path,
    tts_generator,
    ffmpeg_path: str,
    tts_parallelism: int,
    tts_max_chars_per_chunk: int,
) -> PreparedSegment:
    memory_context = memory_store.build_prompt_context()
    generated_script = generate_script_content(
        system_instruction=build_system_instruction(show_config, brief),
        user_prompt=build_user_prompt(
            show_config=show_config,
            brief=brief,
            memory_context=memory_context,
        ),
    )
    segment_id = f"segment_{time.time_ns()}"
    audio_path = Path(tts_dir) / f"{segment_id}.wav"
    synthesize_script_to_file(
        script=generated_script.script,
        output_file=str(audio_path),
        tts_generator=tts_generator,
        ffmpeg_path=ffmpeg_path,
        parallelism=tts_parallelism,
        max_chars_per_chunk=tts_max_chars_per_chunk,
    )
    duration_seconds = get_audio_duration(str(audio_path), ffmpeg_path)
    summary = _summarize_script(generated_script.script)
    studio_page_path = render_segment_page(
        show_config=show_config,
        brief=brief,
        script=generated_script.script,
        summary=summary,
        output_path=Path(studio_pages_dir) / f"{segment_id}.html",
    )
    return PreparedSegment(
        segment_id=segment_id,
        kind=brief.segment_template.kind,
        title=brief.segment_template.label,
        summary=summary,
        script=generated_script.script,
        provider_name=generated_script.provider_name,
        audio_path=audio_path,
        target_duration_seconds=brief.target_duration_seconds,
        actual_audio_duration_seconds=duration_seconds,
        studio_page_path=studio_page_path,
    )


def _summarize_script(script: str) -> str:
    clean = " ".join(script.split())
    if not clean:
        return "Empty segment"
    for delimiter in (". ", "! ", "? "):
        if delimiter in clean:
            return clean.split(delimiter, 1)[0][:220].strip()
    return clean[:220].strip()


__all__ = ["prepare_segment"]
