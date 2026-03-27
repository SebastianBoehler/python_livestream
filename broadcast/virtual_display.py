"""Lifecycle management for an isolated Xvfb display."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from broadcast.capture import CaptureBackendConfig


@dataclass(slots=True)
class VirtualDisplayHandle:
    display: str
    process: subprocess.Popen | None

    @property
    def browser_env(self) -> dict[str, str]:
        environment = os.environ.copy()
        environment["DISPLAY"] = self.display
        return environment

    def stop(self) -> None:
        if self.process is None:
            return
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)


@contextmanager
def managed_virtual_display(
    config: CaptureBackendConfig,
) -> VirtualDisplayHandle | None:
    if not config.uses_virtual_screen_capture:
        yield None
        return
    if not sys.platform.startswith("linux"):
        raise RuntimeError("STREAM_CAPTURE_BACKEND=virtual-screen requires Linux with X11/Xvfb")

    socket_path = Path("/tmp/.X11-unix") / f"X{config.virtual_display.lstrip(':')}"
    if socket_path.exists():
        yield VirtualDisplayHandle(display=config.virtual_display, process=None)
        return

    xvfb_path = shutil.which("Xvfb")
    if xvfb_path is None:
        raise RuntimeError("Xvfb is required for STREAM_CAPTURE_BACKEND=virtual-screen")

    command = [
        xvfb_path,
        config.virtual_display,
        "-screen",
        str(config.virtual_display_screen),
        f"{config.width}x{config.height}x{config.virtual_display_color_depth}",
        "-ac",
        "-nolisten",
        "tcp",
    ]
    process = subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    _wait_until_ready(process, socket_path)
    handle = VirtualDisplayHandle(display=config.virtual_display, process=process)
    try:
        yield handle
    finally:
        handle.stop()


def _wait_until_ready(process: subprocess.Popen, socket_path: Path) -> None:
    deadline = time.time() + 5
    while time.time() < deadline:
        if process.poll() is not None:
            error_output = ""
            if process.stderr is not None:
                error_output = process.stderr.read().strip()
            raise RuntimeError(f"Xvfb failed to start: {error_output or 'no stderr output'}")
        if socket_path.exists():
            return
        time.sleep(0.1)
    raise RuntimeError(f"Timed out waiting for virtual display socket {socket_path}")
