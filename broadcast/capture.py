"""Capture backend selection and browser launch settings."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True)
class CaptureBackendConfig:
    name: str
    orientation: str
    fps: int
    width: int
    height: int
    screen_device: str
    pixel_format: str
    capture_cursor: bool

    @property
    def uses_screen_capture(self) -> bool:
        return self.name == "screen"

    @property
    def uses_page_screenshots(self) -> bool:
        return self.name == "playwright"

    @property
    def is_vertical(self) -> bool:
        return self.height > self.width

    @property
    def aspect_ratio_label(self) -> str:
        return "9:16" if self.is_vertical else "16:9"


def load_capture_backend_config() -> CaptureBackendConfig:
    name = os.getenv("STREAM_CAPTURE_BACKEND", "playwright").strip().lower()
    if name not in {"playwright", "screen"}:
        raise ValueError(f"Unsupported STREAM_CAPTURE_BACKEND: {name}")
    orientation = os.getenv("STREAM_ORIENTATION", "landscape").strip().lower()
    if orientation not in {"landscape", "portrait"}:
        raise ValueError(f"Unsupported STREAM_ORIENTATION: {orientation}")
    fps = int(os.getenv("STREAM_FPS", "12"))
    width, height = _resolve_dimensions(orientation)
    return CaptureBackendConfig(
        name=name,
        orientation=orientation,
        fps=fps,
        width=width,
        height=height,
        screen_device=os.getenv("SCREEN_CAPTURE_DEVICE", "3"),
        pixel_format=os.getenv("SCREEN_CAPTURE_PIXEL_FORMAT", "bgr0"),
        capture_cursor=os.getenv("SCREEN_CAPTURE_CURSOR", "false").lower() == "true",
    )


def browser_launch_kwargs(config: CaptureBackendConfig) -> dict:
    if config.uses_screen_capture:
        args = [
            f"--window-size={config.width},{config.height}",
            "--window-position=0,0",
        ]
        if os.getenv("SCREEN_BROWSER_FULLSCREEN", "true").lower() == "true":
            args.append("--start-fullscreen")
        return {
            "headless": False,
            "args": args,
        }
    return {
        "headless": True,
        "args": ["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"],
    }


def ffmpeg_video_input_args(config: CaptureBackendConfig) -> list[str]:
    if config.uses_screen_capture:
        return [
            "-f",
            "avfoundation",
            "-thread_queue_size",
            "512",
            "-framerate",
            str(config.fps),
            "-pixel_format",
            config.pixel_format,
            "-video_size",
            f"{config.width}x{config.height}",
            "-capture_cursor",
            "1" if config.capture_cursor else "0",
            "-i",
            f"{config.screen_device}:none",
        ]
    return [
        "-f",
        "image2pipe",
        "-thread_queue_size",
        "512",
        "-r",
        str(config.fps),
        "-i",
        "-",
    ]


def _resolve_dimensions(orientation: str) -> tuple[int, int]:
    width_override = os.getenv("STREAM_WIDTH")
    height_override = os.getenv("STREAM_HEIGHT")
    if width_override and height_override:
        return int(width_override), int(height_override)
    if orientation == "portrait":
        return 1080, 1920
    return 1280, 720
