"""Music-only intermission segment generation."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

from broadcast.models import PreparedSegment
from broadcast.studio_page import render_intermission_page
from shows.models import ShowConfig


def prepare_intermission_segment(
    *,
    duration_seconds: int,
    tts_dir: str | Path,
    ffmpeg_path: str,
    show_config: ShowConfig | None = None,
    studio_pages_dir: str | Path | None = None,
) -> PreparedSegment:
    if duration_seconds <= 0:
        raise ValueError("Intermission duration must be positive")

    segment_id = f"intermission_{time.time_ns()}"
    audio_path = Path(tts_dir) / f"{segment_id}.wav"
    _generate_silence_file(audio_path=audio_path, duration_seconds=duration_seconds, ffmpeg_path=ffmpeg_path)
    studio_page_path = None
    if show_config is not None and studio_pages_dir is not None:
        studio_page_path = render_intermission_page(
            show_config=show_config,
            duration_seconds=duration_seconds,
            output_path=Path(studio_pages_dir) / f"{segment_id}.html",
        )
    return PreparedSegment(
        segment_id=segment_id,
        kind="intermission",
        title="Music Break",
        summary=f"Music-only reset for about {duration_seconds} seconds.",
        script="",
        provider_name="music",
        audio_path=audio_path,
        target_duration_seconds=duration_seconds,
        actual_audio_duration_seconds=float(duration_seconds),
        studio_page_path=studio_page_path,
    )


def _generate_silence_file(*, audio_path: Path, duration_seconds: int, ffmpeg_path: str) -> None:
    command = [
        ffmpeg_path,
        "-y",
        "-f",
        "lavfi",
        "-i",
        "anullsrc=r=24000:cl=mono",
        "-t",
        str(duration_seconds),
        "-c:a",
        "pcm_s16le",
        str(audio_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Intermission audio generation failed: {result.stderr}")
