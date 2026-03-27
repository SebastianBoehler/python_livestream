"""Video capture and FFmpeg playout."""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import time
from queue import Empty, Full, Queue
from threading import Event, Thread

from broadcast.models import PreparedSegment

logger = logging.getLogger(__name__)


def _ffmpeg_writer(frame_queue: Queue, process: subprocess.Popen, stop_event: Event) -> None:
    frames_written = 0
    while not stop_event.is_set() or not frame_queue.empty():
        try:
            frame = frame_queue.get(timeout=0.05)
            if frame is None:
                break
            if process.stdin and process.poll() is None:
                process.stdin.write(frame)
                process.stdin.flush()
                frames_written += 1
                if frames_written % 100 == 0:
                    logger.info("Frames written: %s, queue size: %s", frames_written, frame_queue.qsize())
        except Empty:
            if process.poll() is not None:
                break
        except Exception as error:
            logger.warning("Writer error: %s", error)
            if process.poll() is not None:
                break


async def _capture_frames(page, frame_queue: Queue, stop_event: Event, fps: int) -> None:
    frame_delay = 1 / fps
    frames_captured = 0
    frames_dropped = 0
    capture_started_at = time.perf_counter()
    next_capture_at = capture_started_at
    while not stop_event.is_set():
        try:
            screenshot = await page.screenshot(type="jpeg", quality=70)
            frames_captured += 1
            try:
                frame_queue.put_nowait(screenshot)
            except Full:
                frames_dropped += 1
                if frames_dropped % 50 == 0:
                    logger.warning("Dropped %s frames (queue full)", frames_dropped)
            if frames_captured % 100 == 0:
                elapsed = time.perf_counter() - capture_started_at
                effective_fps = frames_captured / elapsed if elapsed > 0 else 0
                logger.info(
                    "Frames captured: %s, effective capture fps: %.2f, dropped: %s",
                    frames_captured,
                    effective_fps,
                    frames_dropped,
                )
        except Exception as error:
            if stop_event.is_set():
                break
            logger.warning("Screenshot error: %s", error)
        next_capture_at += frame_delay
        sleep_duration = next_capture_at - time.perf_counter()
        if sleep_duration > 0:
            await asyncio.sleep(sleep_duration)
        else:
            next_capture_at = time.perf_counter()


async def stream_segment(
    *,
    page,
    stream_key: str,
    background_music_path: str,
    segment: PreparedSegment,
    fps: int,
    ffmpeg_path: str = "ffmpeg",
) -> float:
    filler_duration = max(segment.target_duration_seconds - segment.actual_audio_duration_seconds, 0)
    total_duration = segment.actual_audio_duration_seconds + filler_duration
    rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
    command = [
        ffmpeg_path,
        "-v",
        "info",
        "-stats",
        "-f",
        "image2pipe",
        "-thread_queue_size",
        "512",
        "-r",
        str(fps),
        "-i",
        "-",
        "-i",
        str(segment.audio_path),
        "-stream_loop",
        "-1",
        "-i",
        background_music_path,
        "-c:v",
        "h264_videotoolbox",
        "-pix_fmt",
        "yuv420p",
        "-r",
        str(fps),
        "-g",
        str(fps * 2),
        "-b:v",
        "4500k",
        "-maxrate",
        "5000k",
        "-bufsize",
        "10000k",
        "-profile:v",
        "baseline",
        "-realtime",
        "1",
        "-filter_complex",
        "[1:a]apad,volume=1.0[news];[2:a]volume=0.04[bg];[news][bg]amix=inputs=2:duration=longest[aout]",
        "-map",
        "0:v",
        "-map",
        "[aout]",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-ar",
        "44100",
        "-t",
        str(total_duration),
        "-f",
        "flv",
        rtmp_url,
    ]
    safe_command = command.copy()
    safe_command[-1] = safe_command[-1].replace(stream_key, "STREAM_KEY_HIDDEN")
    logger.info("Starting FFmpeg segment:")
    logger.info(" ".join(safe_command))

    frame_queue = Queue(maxsize=90)
    stop_event = Event()
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    writer_thread = Thread(target=_ffmpeg_writer, args=(frame_queue, process, stop_event))
    writer_thread.start()
    capture_task = asyncio.create_task(_capture_frames(page, frame_queue, stop_event, fps))
    await asyncio.to_thread(process.wait)
    stop_event.set()
    frame_queue.put(None)
    capture_task.cancel()
    try:
        await capture_task
    except asyncio.CancelledError:
        pass
    writer_thread.join(timeout=2)
    if process.stdin:
        process.stdin.close()
    if segment.audio_path.exists():
        segment.audio_path.unlink()
    logger.info("Segment finished")
    return total_duration

