"""Continuous Xvfb/Chromium capture of one terminal page."""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import shutil
import subprocess
from collections.abc import Mapping
from contextlib import suppress
from typing import TextIO
from urllib.parse import urlsplit

from broadcast.capture import CaptureBackendConfig
from broadcast.terminal_stream_config import (
    STREAM_FPS,
    STREAM_HEIGHT,
    STREAM_WIDTH,
    TerminalStreamConfig,
    TerminalStreamConfigError,
    TerminalStreamRuntimeError,
    load_terminal_stream_config,
)
from broadcast.terminal_stream_ffmpeg import (
    build_ffmpeg_command,
    redact_ffmpeg_log_line,
    raise_for_ffmpeg_exit,
    safe_ffmpeg_command,
)
from broadcast.virtual_display import managed_virtual_display

logger = logging.getLogger(__name__)


def _capture_backend(config: TerminalStreamConfig) -> CaptureBackendConfig:
    return CaptureBackendConfig(
        name="virtual-screen",
        orientation="landscape",
        fps=STREAM_FPS,
        width=STREAM_WIDTH,
        height=STREAM_HEIGHT,
        browser_fullscreen=True,
        screen_device="",
        pixel_format="",
        screen_capture_cursor=False,
        virtual_display=config.display,
        virtual_display_screen=0,
        virtual_display_color_depth=24,
        virtual_display_cursor=False,
    )


def _minimal_child_environment(
    display: str,
    process_environment: Mapping[str, str] | None = None,
) -> dict[str, str]:
    source = os.environ if process_environment is None else process_environment
    allowed_names = (
        "HOME",
        "LANG",
        "LC_ALL",
        "PATH",
        "TZ",
        "XDG_RUNTIME_DIR",
    )
    environment = {
        name: source[name]
        for name in allowed_names
        if source.get(name)
    }
    environment["DISPLAY"] = display
    return environment


def _browser_launch_kwargs(browser_environment: dict[str, str]) -> dict:
    return {
        "headless": False,
        "env": browser_environment,
        "args": [
            f"--window-size={STREAM_WIDTH},{STREAM_HEIGHT}",
            "--window-position=0,0",
            "--kiosk",
            "--hide-scrollbars",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--no-first-run",
            "--no-default-browser-check",
        ],
    }


def _forward_ffmpeg_stderr(stderr: TextIO, output_target: str) -> None:
    for raw_line in stderr:
        safe_line = redact_ffmpeg_log_line(raw_line.rstrip(), output_target)
        if safe_line:
            logger.info("FFmpeg: %s", safe_line)


def _validate_final_page_url(expected: str, actual: str) -> None:
    expected_url = urlsplit(expected)
    actual_url = urlsplit(actual)
    expected_host = expected_url.hostname or ""
    actual_host = actual_url.hostname or ""
    host_is_expected = actual_host == expected_host
    host_is_canonical_www = (
        expected_host == "hb-capital.app"
        and actual_host == "www.hb-capital.app"
        and expected_url.scheme == "https"
        and actual_url.scheme == "https"
    )
    same_page = (
        actual_url.scheme == expected_url.scheme
        and actual_url.port == expected_url.port
        and actual_url.path.rstrip("/") == expected_url.path.rstrip("/")
    )
    if not same_page or not (host_is_expected or host_is_canonical_www):
        raise TerminalStreamRuntimeError(
            "STREAM_URL redirected to an unexpected page; refusing to broadcast"
        )


async def run_terminal_stream(config: TerminalStreamConfig) -> None:
    """Navigate once, then keep one FFmpeg process attached to the display."""
    ffmpeg_executable = shutil.which(config.ffmpeg_path)
    if ffmpeg_executable is None:
        raise TerminalStreamRuntimeError("FFmpeg executable was not found")
    command = build_ffmpeg_command(config)
    command[0] = ffmpeg_executable
    capture_backend = _capture_backend(config)

    child_environment = _minimal_child_environment(config.display)
    with managed_virtual_display(
        capture_backend,
        process_environment=child_environment,
    ) as virtual_display:
        if virtual_display is None:
            raise TerminalStreamRuntimeError("Virtual display did not start")
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(
                    **_browser_launch_kwargs(child_environment)
                )
                try:
                    page = await browser.new_page(
                        viewport={"width": STREAM_WIDTH, "height": STREAM_HEIGHT},
                        device_scale_factor=1,
                    )
                    response = await page.goto(
                        config.stream_url,
                        wait_until="domcontentloaded",
                        timeout=60_000,
                    )
                    if response is None or not response.ok:
                        raise TerminalStreamRuntimeError(
                            "STREAM_URL did not return a successful browser response"
                        )
                    _validate_final_page_url(config.stream_url, page.url)
                    await page.wait_for_selector("body", state="visible", timeout=30_000)
                    await page.wait_for_timeout(5_000)

                    logger.info(
                        "Starting 1920x1080@30 terminal stream with command: %s",
                        safe_ffmpeg_command(command),
                    )
                    process = subprocess.Popen(
                        command,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                        text=True,
                        env=child_environment,
                    )
                    if process.stderr is None:
                        process.terminate()
                        raise TerminalStreamRuntimeError(
                            "FFmpeg stderr monitor could not start"
                        )
                    stderr_task = asyncio.create_task(
                        asyncio.to_thread(
                            _forward_ffmpeg_stderr,
                            process.stderr,
                            config.output_target,
                        )
                    )
                    try:
                        return_code = await asyncio.to_thread(process.wait)
                    except asyncio.CancelledError:
                        process.terminate()
                        try:
                            await asyncio.to_thread(process.wait, 10)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            await asyncio.to_thread(process.wait)
                        raise
                    finally:
                        await stderr_task
                    raise_for_ffmpeg_exit(return_code)
                finally:
                    await browser.close()
        except TerminalStreamRuntimeError:
            raise
        except Exception as error:
            raise TerminalStreamRuntimeError(
                "Browser capture failed before or during streaming"
            ) from error


async def run_terminal_stream_until_stopped(config: TerminalStreamConfig) -> None:
    """Run until FFmpeg exits or the container receives SIGINT/SIGTERM."""
    loop = asyncio.get_running_loop()
    stop_requested = asyncio.Event()
    registered_signals: list[signal.Signals] = []
    for signal_number in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signal_number, stop_requested.set)
            registered_signals.append(signal_number)
        except NotImplementedError:
            continue

    stream_task = asyncio.create_task(run_terminal_stream(config))
    stop_task = asyncio.create_task(stop_requested.wait())
    try:
        completed, _ = await asyncio.wait(
            {stream_task, stop_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        if stream_task in completed:
            stop_task.cancel()
            await stream_task
            return

        logger.info("Stream shutdown requested; finalizing FFmpeg output")
        stream_task.cancel()
        try:
            await stream_task
        except asyncio.CancelledError:
            pass
    finally:
        stop_task.cancel()
        with suppress(asyncio.CancelledError):
            await stop_task
        if not stream_task.done():
            stream_task.cancel()
            with suppress(asyncio.CancelledError):
                await stream_task
        for signal_number in registered_signals:
            loop.remove_signal_handler(signal_number)


__all__ = [
    "TerminalStreamConfigError",
    "TerminalStreamRuntimeError",
    "load_terminal_stream_config",
    "run_terminal_stream",
    "run_terminal_stream_until_stopped",
]
