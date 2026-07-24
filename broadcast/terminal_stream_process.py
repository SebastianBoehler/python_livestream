"""Long-running FFmpeg process supervision for the terminal stream."""

from __future__ import annotations

import asyncio
import logging
import subprocess
import time
from collections.abc import Mapping, Sequence
from contextlib import suppress
from typing import TextIO

from broadcast.terminal_stream_config import TerminalStreamRuntimeError
from broadcast.terminal_stream_ffmpeg import redact_ffmpeg_log_line

logger = logging.getLogger(__name__)

RECONNECT_DELAYS_SECONDS = (1, 2, 5, 10)
STABLE_SESSION_SECONDS = 300
FFMPEG_STOP_TIMEOUT_SECONDS = 10


def next_reconnect_delay(
    failure_count: int,
    *,
    session_duration_seconds: float,
) -> tuple[int, int]:
    """Return the next bounded delay and updated consecutive failure count."""
    if session_duration_seconds >= STABLE_SESSION_SECONDS:
        failure_count = 0
    delay_index = min(failure_count, len(RECONNECT_DELAYS_SECONDS) - 1)
    return RECONNECT_DELAYS_SECONDS[delay_index], failure_count + 1


def _forward_ffmpeg_stderr(stderr: TextIO, output_target: str) -> None:
    for raw_line in stderr:
        safe_line = redact_ffmpeg_log_line(raw_line.rstrip(), output_target)
        if safe_line:
            logger.info("FFmpeg: %s", safe_line)


async def _stop_ffmpeg(process: subprocess.Popen[str]) -> None:
    with suppress(ProcessLookupError):
        process.terminate()
    try:
        await asyncio.to_thread(process.wait, FFMPEG_STOP_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        logger.warning("FFmpeg did not stop within 10 seconds; killing it")
        with suppress(ProcessLookupError):
            process.kill()
        await asyncio.to_thread(process.wait)


async def _run_ffmpeg_once(
    command: Sequence[str],
    *,
    environment: Mapping[str, str],
    output_target: str,
) -> int:
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            env=environment,
        )
    except OSError as error:
        raise TerminalStreamRuntimeError("FFmpeg process could not start") from error

    if process.stderr is None:
        await _stop_ffmpeg(process)
        raise TerminalStreamRuntimeError("FFmpeg stderr monitor could not start")

    stderr_task = asyncio.create_task(
        asyncio.to_thread(
            _forward_ffmpeg_stderr,
            process.stderr,
            output_target,
        )
    )
    try:
        return await asyncio.to_thread(process.wait)
    except asyncio.CancelledError:
        await _stop_ffmpeg(process)
        raise
    finally:
        await stderr_task


async def run_ffmpeg_with_reconnect(
    command: Sequence[str],
    *,
    environment: Mapping[str, str],
    output_target: str,
) -> None:
    """Run FFmpeg indefinitely, reconnecting after every unexpected exit."""
    failure_count = 0
    while True:
        started_at = time.monotonic()
        return_code = await _run_ffmpeg_once(
            command,
            environment=environment,
            output_target=output_target,
        )
        session_duration_seconds = max(0, time.monotonic() - started_at)
        delay_seconds, failure_count = next_reconnect_delay(
            failure_count,
            session_duration_seconds=session_duration_seconds,
        )
        logger.warning(
            "FFmpeg exited unexpectedly with status %s after %.1f seconds; "
            "reconnecting in %s seconds",
            return_code,
            session_duration_seconds,
            delay_seconds,
        )
        await asyncio.sleep(delay_seconds)
