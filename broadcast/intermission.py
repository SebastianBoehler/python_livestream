"""Music-only intermission segment generation."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

from broadcast.models import PreparedSegment


def prepare_intermission_segment(
    *,
    duration_seconds: int,
    tts_dir: str | Path,
    ffmpeg_path: str,
) -> PreparedSegment:
    if duration_seconds <= 0:
        raise ValueError("Intermission duration must be positive")

    segment_id = f"intermission_{time.time_ns()}"
    audio_path = Path(tts_dir) / f"{segment_id}.wav"
    _generate_silence_file(audio_path=audio_path, duration_seconds=duration_seconds, ffmpeg_path=ffmpeg_path)
    return PreparedSegment(
        segment_id=segment_id,
        kind="intermission",
        script="",
        provider_name="music",
        audio_path=audio_path,
        target_duration_seconds=duration_seconds,
        actual_audio_duration_seconds=float(duration_seconds),
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
