import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor

from dotenv import load_dotenv
from playwright.async_api import async_playwright

from broadcast.capture import browser_launch_kwargs, load_capture_backend_config
from broadcast.memory import BroadcastMemoryStore
from broadcast.pipeline import prepare_segment
from broadcast.streaming import stream_segment
from tts.gemini import generate as generate_tts_audio

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def _resolve_ffmpeg_path() -> str:
    for candidate in ("/opt/homebrew/bin/ffmpeg", "/usr/bin/ffmpeg"):
        if os.path.exists(candidate):
            return candidate
    return "ffmpeg"


def _news_prompt() -> str:
    return (
        "Latest news from the last 24h about crypto and blockchain."
        " Cover macro, policy, market structure, major company actions, and mindshare shifts."
        " Be analytical and focus on what matters for markets."
    )


async def _produce_segments(
    *,
    segment_queue: asyncio.Queue,
    stop_event: asyncio.Event,
    executor: ThreadPoolExecutor,
    memory_store: BroadcastMemoryStore,
    tts_dir: str,
    ffmpeg_path: str,
    target_duration_seconds: int,
    tts_parallelism: int,
    tts_max_chars_per_chunk: int,
) -> None:
    loop = asyncio.get_running_loop()
    while not stop_event.is_set():
        if segment_queue.full():
            await asyncio.sleep(1)
            continue
        try:
            segment = await loop.run_in_executor(
                executor,
                lambda: prepare_segment(
                    news_prompt=_news_prompt(),
                    memory_store=memory_store,
                    tts_dir=tts_dir,
                    tts_generator=generate_tts_audio,
                    ffmpeg_path=ffmpeg_path,
                    target_duration_seconds=target_duration_seconds,
                    tts_parallelism=tts_parallelism,
                    tts_max_chars_per_chunk=tts_max_chars_per_chunk,
                ),
            )
            await segment_queue.put(segment)
            logger.info(
                "Queued segment %s from %s (%ss audio). Queue size: %s",
                segment.segment_id,
                segment.provider_name,
                round(segment.actual_audio_duration_seconds, 1),
                segment_queue.qsize(),
            )
        except Exception as error:
            logger.error("Segment preparation failed: %s", error)
            await asyncio.sleep(5)


async def run_livestream() -> None:
    load_dotenv(override=False)
    stream_key = os.getenv("YOUTUBE_STREAM_KEY")
    url = os.getenv("STREAM_URL")
    capture_backend = load_capture_backend_config()
    segment_duration_seconds = int(
        os.getenv("NEWS_SEGMENT_SECONDS", str(int(os.getenv("NEWS_INTERVAL_MINUTES", "15")) * 60))
    )
    segment_buffer_size = int(os.getenv("SEGMENT_BUFFER_SIZE", "3"))
    tts_parallelism = int(os.getenv("TTS_PARALLELISM", "3"))
    tts_max_chars_per_chunk = int(os.getenv("TTS_MAX_CHARS_PER_CHUNK", "450"))

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

    ffmpeg_path = _resolve_ffmpeg_path()
    tts_dir = os.path.join(os.getcwd(), "audio", "tts")
    os.makedirs(tts_dir, exist_ok=True)
    memory_store = BroadcastMemoryStore(os.path.join(os.getcwd(), "memory"))

    segment_queue: asyncio.Queue = asyncio.Queue(maxsize=segment_buffer_size)
    stop_event = asyncio.Event()
    executor = ThreadPoolExecutor(max_workers=1)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(**browser_launch_kwargs(capture_backend))
        page = await browser.new_page(viewport={"width": capture_backend.width, "height": capture_backend.height})
        logger.info(
            "Streaming from %s with capture backend=%s orientation=%s aspect=%s fps=%s size=%sx%s",
            url,
            capture_backend.name,
            capture_backend.orientation,
            capture_backend.aspect_ratio_label,
            capture_backend.fps,
            capture_backend.width,
            capture_backend.height,
        )
        print(f"Streaming from {url}")
        await page.goto(url)
        await page.bring_to_front()
        producer_task = asyncio.create_task(
            _produce_segments(
                segment_queue=segment_queue,
                stop_event=stop_event,
                executor=executor,
                memory_store=memory_store,
                tts_dir=tts_dir,
                ffmpeg_path=ffmpeg_path,
                target_duration_seconds=segment_duration_seconds,
                tts_parallelism=tts_parallelism,
                tts_max_chars_per_chunk=tts_max_chars_per_chunk,
            )
        )

        try:
            while True:
                segment = await segment_queue.get()
                logger.info("Starting playout for segment %s", segment.segment_id)
                await stream_segment(
                    page=page,
                    stream_key=stream_key,
                    background_music_path=background_music_path,
                    segment=segment,
                    capture_backend=capture_backend,
                    ffmpeg_path=ffmpeg_path,
                )
                memory_store.record_segment(segment)
                segment_queue.task_done()
        except KeyboardInterrupt:
            logger.info("Livestream stopped by user")
        finally:
            stop_event.set()
            producer_task.cancel()
            try:
                await producer_task
            except asyncio.CancelledError:
                pass
            executor.shutdown(wait=False, cancel_futures=True)
            try:
                await browser.close()
            except Exception as error:
                logger.warning("Browser shutdown raised after interruption: %s", error)


if __name__ == "__main__":
    asyncio.run(run_livestream())
