"""Runtime metrics for ffmpeg streaming segments."""

from __future__ import annotations

import logging
import re
import subprocess
import threading
import time

logger = logging.getLogger(__name__)

_PROGRESS_KEY_PATTERN = re.compile(r"^([a-z_]+)=(.*)$")


class FfmpegRuntimeMonitor:
    """Collects coarse runtime metrics from ffmpeg progress output and process stats."""

    def __init__(self, process: subprocess.Popen, interval_seconds: float = 5.0) -> None:
        self.process = process
        self.interval_seconds = interval_seconds
        self._stop_event = threading.Event()
        self._progress_thread = threading.Thread(target=self._read_progress, daemon=True)
        self._cpu_thread = threading.Thread(target=self._poll_cpu, daemon=True)
        self._segment_started_at = time.perf_counter()
        self._progress: dict[str, str] = {}

    def start(self) -> None:
        self._progress_thread.start()
        self._cpu_thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._progress_thread.join(timeout=2)
        self._cpu_thread.join(timeout=2)

    def _read_progress(self) -> None:
        if not self.process.stderr:
            return
        while not self._stop_event.is_set():
            line = self.process.stderr.readline()
            if not line:
                if self.process.poll() is not None:
                    break
                continue
            if isinstance(line, bytes):
                line = line.decode("utf-8", errors="ignore")
            line = line.strip()
            match = _PROGRESS_KEY_PATTERN.match(line)
            if not match:
                continue
            key, value = match.groups()
            self._progress[key] = value
            if key == "progress":
                self._log_progress_snapshot()
                if value == "end":
                    break

    def _log_progress_snapshot(self) -> None:
        encoded_seconds = int(self._progress.get("out_time_us", "0")) / 1_000_000
        wall_seconds = time.perf_counter() - self._segment_started_at
        latency_seconds = wall_seconds - encoded_seconds
        logger.info(
            "FFmpeg progress: frame=%s fps=%s speed=%s encoded=%.2fs wall=%.2fs latency=%.2fs",
            self._progress.get("frame", "?"),
            self._progress.get("fps", "?"),
            self._progress.get("speed", "?"),
            encoded_seconds,
            wall_seconds,
            latency_seconds,
        )

    def _poll_cpu(self) -> None:
        while not self._stop_event.wait(self.interval_seconds):
            if self.process.poll() is not None:
                break
            result = subprocess.run(
                ["ps", "-o", "%cpu=,rss=", "-p", str(self.process.pid)],
                capture_output=True,
                text=True,
                check=False,
            )
            output = result.stdout.strip()
            if not output:
                continue
            cpu_percent, rss_kb = output.split(None, 1)
            logger.info(
                "FFmpeg process stats: cpu=%s%% rss=%.1fMB pid=%s",
                cpu_percent,
                int(rss_kb) / 1024,
                self.process.pid,
            )
