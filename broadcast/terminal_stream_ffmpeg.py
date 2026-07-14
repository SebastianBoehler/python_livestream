"""FFmpeg command construction for the continuous terminal stream."""

from __future__ import annotations

import shlex
from urllib.parse import parse_qsl, urlsplit

from broadcast.terminal_stream_config import (
    STREAM_FPS,
    STREAM_HEIGHT,
    STREAM_WIDTH,
    TerminalStreamConfig,
    TerminalStreamRuntimeError,
)


def build_ffmpeg_command(config: TerminalStreamConfig) -> list[str]:
    """Build the fixed 1080p30 low-latency YouTube ingest command."""
    return [
        config.ffmpeg_path,
        "-hide_banner",
        "-nostdin",
        "-loglevel",
        "warning",
        "-stats_period",
        "5",
        "-progress",
        "pipe:2",
        "-thread_queue_size",
        "1024",
        "-f",
        "x11grab",
        "-draw_mouse",
        "0",
        "-framerate",
        str(STREAM_FPS),
        "-video_size",
        f"{STREAM_WIDTH}x{STREAM_HEIGHT}",
        "-i",
        f"{config.display}.0+0,0",
        "-f",
        "lavfi",
        "-i",
        "anullsrc=channel_layout=stereo:sample_rate=48000",
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-profile:v",
        "high",
        "-level:v",
        "4.2",
        "-pix_fmt",
        "yuv420p",
        "-r",
        str(STREAM_FPS),
        "-fps_mode",
        "cfr",
        "-g",
        str(STREAM_FPS * 2),
        "-keyint_min",
        str(STREAM_FPS * 2),
        "-bf",
        "2",
        "-refs",
        "1",
        "-sc_threshold",
        "0",
        "-b:v",
        "10000k",
        "-minrate",
        "10000k",
        "-maxrate",
        "10000k",
        "-bufsize",
        "20000k",
        "-x264-params",
        "nal-hrd=cbr:force-cfr=1",
        "-colorspace",
        "bt709",
        "-color_primaries",
        "bt709",
        "-color_trc",
        "bt709",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-ar",
        "48000",
        "-ac",
        "2",
        "-flvflags",
        "no_duration_filesize",
        "-f",
        "flv",
        config.output_target,
    ]


def safe_ffmpeg_command(command: list[str]) -> str:
    """Format an FFmpeg command without exposing the ingest path or query."""
    if not command:
        return ""
    safe_parts = [*command[:-1], _redact_output_url(command[-1])]
    return shlex.join(safe_parts)


def _redact_output_url(value: str) -> str:
    parsed = urlsplit(value)
    if not parsed.scheme:
        return value
    host = parsed.hostname or "endpoint"
    if ":" in host:
        host = f"[{host}]"
    if parsed.port is not None:
        host = f"{host}:{parsed.port}"
    return f"{parsed.scheme}://{host}/<redacted>"


def redact_ffmpeg_log_line(line: str, output_target: str) -> str:
    """Redact the ingest target if FFmpeg repeats it in progress or errors."""
    parsed = urlsplit(output_target)
    if not parsed.scheme:
        return line
    redacted = line.replace(output_target, _redact_output_url(output_target))
    if parsed.path:
        redacted = redacted.replace(parsed.path, "/<redacted>")
        for path_part in parsed.path.split("/"):
            if len(path_part) >= 8:
                redacted = redacted.replace(path_part, "<redacted>")
    if parsed.query:
        redacted = redacted.replace(parsed.query, "<redacted>")
        for _, query_value in parse_qsl(parsed.query, keep_blank_values=True):
            if query_value:
                redacted = redacted.replace(query_value, "<redacted>")
    return redacted


def raise_for_ffmpeg_exit(return_code: int) -> None:
    if return_code != 0:
        raise TerminalStreamRuntimeError(f"FFmpeg exited with status {return_code}")
