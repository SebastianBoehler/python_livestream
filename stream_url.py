import asyncio
import logging
import os
import subprocess
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from queue import Queue, Full, Empty
from threading import Thread, Event

from dotenv import load_dotenv
from playwright.async_api import async_playwright

from llm.grok import generate as generate_news_content
from tts.gemini import generate as generate_tts_audio
from utils import get_audio_duration

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def _ffmpeg_writer(frame_queue: Queue, process: subprocess.Popen, stop_event: Event) -> None:
    """Separate thread to write frames to FFmpeg stdin from queue."""
    frames_written = 0
    while not stop_event.is_set() or not frame_queue.empty():
        try:
            frame = frame_queue.get(timeout=0.05)
            if frame is None:  # Poison pill
                break
            if process.stdin and process.poll() is None:
                process.stdin.write(frame)
                process.stdin.flush()
                frames_written += 1
                if frames_written % 100 == 0:
                    logger.info(f"Frames written: {frames_written}, queue size: {frame_queue.qsize()}")
        except Empty:
            if process.poll() is not None:
                break
            continue
        except Exception as e:
            logger.warning(f"Writer error: {e}")
            if process.poll() is not None:
                break


async def _capture_frames(page, frame_queue: Queue, stop_event: Event, fps: int) -> None:
    """Capture screenshots and put them in queue for separate writer thread."""
    frame_delay = 1 / fps
    frames_captured = 0
    frames_dropped = 0
    while not stop_event.is_set():
        try:
            # Capture with lower quality for speed
            screenshot = await page.screenshot(type="jpeg", quality=70)
            frames_captured += 1
            # Non-blocking put - drop frame if queue is full
            try:
                frame_queue.put_nowait(screenshot)
            except Full:
                frames_dropped += 1
                if frames_dropped % 50 == 0:
                    logger.warning(f"Dropped {frames_dropped} frames (queue full)")
        except Exception as e:
            if stop_event.is_set():
                break
            logger.warning(f"Screenshot error: {e}")
        await asyncio.sleep(frame_delay)


async def stream_segment(
    page,
    stream_key: str,
    background_music_path: str,
    tts_audio_path: str,
    available_time: float,
    fps: int,
    ffmpeg_path: str = "ffmpeg",
) -> float:
    """Stream a single news segment with the website video feed."""
    try:
        segment_duration = get_audio_duration(tts_audio_path, ffmpeg_path)
    except Exception as e:
        # If the TTS file is corrupted or unreadable, log the error, clean up the file, and
        # fall back to streaming only the background music for the full available_time.
        logger.error("Falling back to background-music-only segment due to audio duration error: %s", e)
        if os.path.exists(tts_audio_path):
            try:
                os.remove(tts_audio_path)
                logger.info("Removed faulty TTS file: %s", tts_audio_path)
            except OSError as rm_error:
                logger.warning("Could not remove faulty TTS file %s: %s", tts_audio_path, rm_error)
        # We cannot include the faulty TTS file in the FFmpeg command, so stream only background music.
        tts_audio_path = background_music_path  # reuse background music for the single input
        segment_duration = available_time  # stream the full interval with background music only
    filler_duration = max(available_time - segment_duration, 0)
    total_duration = segment_duration + filler_duration

    # threading can be tuned via env vars for performance
    ffmpeg_threads = os.getenv("FFMPEG_THREADS", "8")

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
        tts_audio_path,
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

    # Use queue + separate writer thread for better parallelism
    frame_queue = Queue(maxsize=90)  # Buffer ~3 seconds at 30fps
    stop_event = Event()
    
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    
    # Start writer thread (handles FFmpeg stdin writes)
    writer_thread = Thread(target=_ffmpeg_writer, args=(frame_queue, process, stop_event))
    writer_thread.start()
    
    # Start capture task (async screenshot capture)
    capture_task = asyncio.create_task(_capture_frames(page, frame_queue, stop_event, fps))
    
    # Wait for FFmpeg to finish
    await asyncio.to_thread(process.wait)
    
    # Signal stop and cleanup
    stop_event.set()
    frame_queue.put(None)  # Poison pill
    capture_task.cancel()
    try:
        await capture_task
    except asyncio.CancelledError:
        pass
    writer_thread.join(timeout=2)
    if process.stdin:
        process.stdin.close()

    # Clean up only if this was a generated TTS file (i.e. lives inside the tts directory)
    if os.path.dirname(tts_audio_path).endswith(os.path.join("audio", "tts")) and os.path.exists(tts_audio_path):
        try:
            os.remove(tts_audio_path)
            logger.info("Removed temporary TTS file: %s", tts_audio_path)
        except OSError as rm_err:
            logger.warning("Could not remove TTS file %s: %s", tts_audio_path, rm_err)

    logger.info("Segment finished")
    return total_duration


async def run_livestream() -> None:
    """Run continuous livestream of a website with scheduled news segments."""
    load_dotenv(override=True)
    stream_key = os.getenv("YOUTUBE_STREAM_KEY")
    url = os.getenv("STREAM_URL")
    fps = int(os.getenv("STREAM_FPS", "25"))
    interval_minutes = int(os.getenv("NEWS_INTERVAL_MINUTES", "15"))

    if not stream_key:
        logger.error("YOUTUBE_STREAM_KEY not provided")
        return
    if not url:
        logger.error("STREAM_URL not provided")
        return

    background_music_path = os.path.join(os.getcwd(), "audio", "song.mp3")
    if not os.path.exists(background_music_path):
        logger.error("Background music not found at %s", background_music_path)
        return

    ffmpeg_path = "ffmpeg"
    for possible in ["/opt/homebrew/bin/ffmpeg", "/usr/bin/ffmpeg"]:
        if os.path.exists(possible):
            ffmpeg_path = possible
            break

    interval_seconds = interval_minutes * 60
    tts_dir = os.path.join(os.getcwd(), "audio", "tts")
    os.makedirs(tts_dir, exist_ok=True)

    news_prompt = (
        "Latest news from the last 24h about crypto and blockchain." \
        " From press releases of blockchain / fintech firm over politics and economics." \
        " Be detailed and informative. Analyze relations between market moves and news events." \
        " Use google search as a grounding for the news."
    )

    executor = ThreadPoolExecutor(max_workers=1)
    loop = asyncio.get_running_loop()

    first_news = generate_news_content(news_prompt)
    audio_path = os.path.join(tts_dir, f"news_{int(time.time())}.wav")
    future = loop.run_in_executor(executor, generate_tts_audio, [first_news], audio_path)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True,
            args=["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = await browser.new_page(viewport={"width": 1280, "height": 720})
        print(f"Streaming from {url}")
        await page.goto(url)

        try:
            while True:
                tts_audio_path = await future
                next_news = generate_news_content(news_prompt)
                next_audio = os.path.join(tts_dir, f"news_{int(time.time())}.wav")
                future = loop.run_in_executor(executor, generate_tts_audio, [next_news], next_audio)

                await stream_segment(
                    page,
                    stream_key,
                    background_music_path,
                    tts_audio_path,
                    available_time=interval_seconds,
                    fps=fps,
                    ffmpeg_path=ffmpeg_path,
                )
        except KeyboardInterrupt:
            logger.info("Livestream stopped by user")
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(run_livestream())
