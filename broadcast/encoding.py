"""FFmpeg video encoder selection."""

from __future__ import annotations

import os
import sys


def ffmpeg_video_encoder_args() -> list[str]:
    encoder = os.getenv("STREAM_VIDEO_ENCODER", "").strip().lower()
    if not encoder:
        capture_backend = os.getenv("STREAM_CAPTURE_BACKEND", "").strip().lower()
        if capture_backend == "virtual-screen":
            encoder = "libx264"
        else:
            encoder = "h264_videotoolbox" if sys.platform == "darwin" else "libx264"

    if encoder == "h264_videotoolbox":
        return ["-c:v", "h264_videotoolbox", "-realtime", "1"]
    if encoder == "libx264":
        preset = os.getenv("STREAM_X264_PRESET", "veryfast").strip()
        return ["-c:v", "libx264", "-preset", preset, "-tune", "zerolatency"]
    raise ValueError(f"Unsupported STREAM_VIDEO_ENCODER: {encoder}")
