"""Validated configuration for the continuous terminal stream."""

from __future__ import annotations

import ipaddress
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import SplitResult, urlsplit

STREAM_WIDTH = 1920
STREAM_HEIGHT = 1080
STREAM_FPS = 30
YOUTUBE_RTMPS_BASE_URL = "rtmps://a.rtmps.youtube.com/live2"
_STREAM_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,128}$")
_DISPLAY_PATTERN = re.compile(r"^:[0-9]+$")


class TerminalStreamConfigError(ValueError):
    """Raised when the terminal stream configuration is unsafe or incomplete."""


class TerminalStreamRuntimeError(RuntimeError):
    """Raised when browser capture or FFmpeg playout fails."""


@dataclass(frozen=True, slots=True)
class TerminalStreamConfig:
    stream_url: str = field(repr=False)
    output_url: str | None = field(default=None, repr=False)
    output_file: Path | None = field(default=None, repr=False)
    ffmpeg_path: str = "ffmpeg"
    display: str = ":99"

    def __post_init__(self) -> None:
        if (self.output_url is None) == (self.output_file is None):
            raise TerminalStreamConfigError(
                "Exactly one stream output target must be configured"
            )

    def __repr__(self) -> str:
        return (
            "TerminalStreamConfig(stream_url=<redacted>, output=<redacted>, "
            f"ffmpeg_path={self.ffmpeg_path!r}, display={self.display!r})"
        )

    @property
    def output_target(self) -> str:
        if self.output_file is not None:
            return str(self.output_file)
        if self.output_url is None:  # Guarded by __post_init__.
            raise TerminalStreamConfigError("Stream output target is missing")
        return self.output_url


def load_terminal_stream_config(
    environment: Mapping[str, str] | None = None,
) -> TerminalStreamConfig:
    values = os.environ if environment is None else environment
    stream_url = values.get("STREAM_URL", "").strip()
    if not stream_url:
        raise TerminalStreamConfigError("STREAM_URL is required")
    _validate_stream_url(stream_url)

    configured_output_url = values.get("STREAM_OUTPUT_URL", "").strip()
    configured_output_file = values.get("STREAM_OUTPUT_FILE", "").strip()
    if configured_output_url and configured_output_file:
        raise TerminalStreamConfigError(
            "STREAM_OUTPUT_URL and STREAM_OUTPUT_FILE are mutually exclusive"
        )
    output_file: Path | None = None
    if configured_output_file:
        output_url = None
        output_file = _validate_output_file(configured_output_file)
    elif configured_output_url:
        output_url = configured_output_url
        _validate_output_url(output_url)
    else:
        stream_key = _load_youtube_stream_key(values)
        output_url = f"{YOUTUBE_RTMPS_BASE_URL}/{stream_key}"

    ffmpeg_path = values.get("FFMPEG_PATH", "ffmpeg").strip()
    if not ffmpeg_path:
        raise TerminalStreamConfigError("FFMPEG_PATH cannot be empty")
    display = values.get("VIRTUAL_DISPLAY", ":99").strip()
    if not _DISPLAY_PATTERN.fullmatch(display):
        raise TerminalStreamConfigError("VIRTUAL_DISPLAY must look like :99")

    return TerminalStreamConfig(
        stream_url=stream_url,
        output_url=output_url,
        output_file=output_file,
        ffmpeg_path=ffmpeg_path,
        display=display,
    )


def _load_youtube_stream_key(environment: Mapping[str, str]) -> str:
    key_file = environment.get("YOUTUBE_STREAM_KEY_FILE", "").strip()
    if key_file:
        try:
            stream_key = Path(key_file).read_text(encoding="utf-8").strip()
        except OSError as error:
            detail = error.strerror or "read failed"
            raise TerminalStreamConfigError(
                f"Unable to read YOUTUBE_STREAM_KEY_FILE: {detail}"
            ) from None
    else:
        stream_key = environment.get("YOUTUBE_STREAM_KEY", "").strip()

    if not stream_key:
        source = "YOUTUBE_STREAM_KEY_FILE" if key_file else "YOUTUBE_STREAM_KEY"
        raise TerminalStreamConfigError(f"{source} is required and cannot be empty")
    if stream_key.lower() in {"changeme", "your-stream-key-here"}:
        raise TerminalStreamConfigError("YouTube stream key cannot be a placeholder")
    if not _STREAM_KEY_PATTERN.fullmatch(stream_key):
        raise TerminalStreamConfigError("YouTube stream key has an invalid format")
    return stream_key


def _validate_stream_url(value: str) -> None:
    parsed = _parse_url(value, "STREAM_URL")
    if parsed.scheme == "https":
        return
    if parsed.scheme == "http" and _is_loopback_host(parsed.hostname):
        return
    raise TerminalStreamConfigError(
        "STREAM_URL must use HTTPS, except for a loopback HTTP smoke test"
    )


def _validate_output_url(value: str) -> None:
    parsed = _parse_url(value, "STREAM_OUTPUT_URL")
    if parsed.scheme == "rtmps":
        return
    if parsed.scheme == "rtmp" and _is_loopback_host(parsed.hostname):
        return
    raise TerminalStreamConfigError(
        "STREAM_OUTPUT_URL must use RTMPS, except for a loopback RTMP smoke test"
    )


def _validate_output_file(value: str) -> Path:
    if "\x00" in value:
        raise TerminalStreamConfigError("STREAM_OUTPUT_FILE is not a valid path")
    output_file = Path(value)
    if not output_file.is_absolute() or output_file.suffix.lower() != ".flv":
        raise TerminalStreamConfigError(
            "STREAM_OUTPUT_FILE must be an absolute path ending in .flv"
        )
    return output_file


def _parse_url(value: str, variable_name: str) -> SplitResult:
    try:
        parsed = urlsplit(value)
        _ = parsed.port
    except ValueError:
        raise TerminalStreamConfigError(f"{variable_name} is not a valid URL") from None
    if not parsed.scheme or not parsed.hostname:
        raise TerminalStreamConfigError(f"{variable_name} must be an absolute URL")
    if parsed.username is not None or parsed.password is not None:
        raise TerminalStreamConfigError(f"{variable_name} cannot contain user information")
    if parsed.fragment:
        raise TerminalStreamConfigError(f"{variable_name} cannot contain a fragment")
    return parsed


def _is_loopback_host(hostname: str | None) -> bool:
    if hostname is None:
        return False
    if hostname.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False
