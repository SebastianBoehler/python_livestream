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
    browser_fullscreen: bool
    screen_device: str
    pixel_format: str
    screen_capture_cursor: bool
    virtual_display: str
    virtual_display_screen: int
    virtual_display_color_depth: int
    virtual_display_cursor: bool

    @property
    def uses_screen_capture(self) -> bool:
        return self.name in {"screen", "virtual-screen"}

    @property
    def uses_page_screenshots(self) -> bool:
        return self.name == "playwright"

    @property
    def uses_virtual_screen_capture(self) -> bool:
        return self.name == "virtual-screen"

    @property
    def is_vertical(self) -> bool:
        return self.height > self.width

    @property
    def aspect_ratio_label(self) -> str:
        return "9:16" if self.is_vertical else "16:9"


def load_capture_backend_config() -> CaptureBackendConfig:
    name = os.getenv("STREAM_CAPTURE_BACKEND", "playwright").strip().lower()
    if name not in {"playwright", "screen", "virtual-screen"}:
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
        browser_fullscreen=os.getenv("SCREEN_BROWSER_FULLSCREEN", "true").lower() == "true",
        screen_device=os.getenv("SCREEN_CAPTURE_DEVICE", "3"),
        pixel_format=os.getenv("SCREEN_CAPTURE_PIXEL_FORMAT", "bgr0"),
        screen_capture_cursor=os.getenv("SCREEN_CAPTURE_CURSOR", "false").lower() == "true",
        virtual_display=os.getenv("VIRTUAL_DISPLAY", ":99"),
        virtual_display_screen=int(os.getenv("VIRTUAL_DISPLAY_SCREEN", "0")),
        virtual_display_color_depth=int(os.getenv("VIRTUAL_DISPLAY_COLOR_DEPTH", "24")),
        virtual_display_cursor=os.getenv("VIRTUAL_DISPLAY_CURSOR", "false").lower() == "true",
    )


def browser_launch_kwargs(config: CaptureBackendConfig, *, browser_env: dict[str, str] | None = None) -> dict:
    if config.uses_screen_capture:
        args = [
            f"--window-size={config.width},{config.height}",
            "--window-position=0,0",
        ]
        if config.browser_fullscreen:
            args.append("--start-fullscreen")
        if config.uses_virtual_screen_capture:
            args.extend(["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"])
        launch_kwargs = {
            "headless": False,
            "args": args,
        }
        if browser_env:
            launch_kwargs["env"] = browser_env
        return launch_kwargs
    return {
        "headless": True,
        "args": ["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"],
    }


def ffmpeg_video_input_args(config: CaptureBackendConfig) -> list[str]:
    if config.name == "screen":
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
            "1" if config.screen_capture_cursor else "0",
            "-i",
            f"{config.screen_device}:none",
        ]
    if config.uses_virtual_screen_capture:
        return [
            "-f",
            "x11grab",
            "-thread_queue_size",
            "512",
            "-framerate",
            str(config.fps),
            "-video_size",
            f"{config.width}x{config.height}",
            "-draw_mouse",
            "1" if config.virtual_display_cursor else "0",
            "-i",
            f"{config.virtual_display}.{config.virtual_display_screen}+0,0",
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
