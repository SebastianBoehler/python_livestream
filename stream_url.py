import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path

from dotenv import load_dotenv
from playwright.async_api import async_playwright

from broadcast.capture import browser_launch_kwargs, load_capture_backend_config
from broadcast.intermission import prepare_intermission_segment
from broadcast.memory import BroadcastMemoryStore
from broadcast.pipeline import prepare_segment
from broadcast.streaming import stream_segment
from broadcast.virtual_display import managed_virtual_display
from shows.briefs import build_segment_brief
from shows.config import load_show_config
from shows.sources import fetch_show_sources
from tts.gemini import generate_with_voice

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def _resolve_ffmpeg_path() -> str:
    for candidate in ("/opt/homebrew/bin/ffmpeg", "/usr/bin/ffmpeg"):
        if os.path.exists(candidate):
            return candidate
    return "ffmpeg"


def _resolve_inter_segment_seconds() -> int:
    configured_music_break = os.getenv("INTER_SEGMENT_MUSIC_SECONDS")
    if configured_music_break:
        return int(configured_music_break)
    return int(os.getenv("INTER_SEGMENT_DELAY_SECONDS", "0"))


def _resolve_default_segment_duration() -> int | None:
    configured_duration = os.getenv("NEWS_SEGMENT_SECONDS")
    if configured_duration:
        return int(configured_duration)
    configured_minutes = os.getenv("NEWS_INTERVAL_MINUTES")
    if configured_minutes:
        return int(configured_minutes) * 60
    return None


def _build_tts_generator(voice_name: str):
    return partial(generate_with_voice, voice_name=voice_name)


def _prepare_show_segment(
    *,
    show_config,
    segment_index: int,
    memory_store: BroadcastMemoryStore,
    tts_dir: Path,
    studio_pages_dir: Path,
    tts_generator,
    ffmpeg_path: str,
    default_segment_duration: int | None,
    tts_parallelism: int,
    tts_max_chars_per_chunk: int,
):
    source_snapshots = fetch_show_sources(show_config)
    brief = build_segment_brief(
        show_config=show_config,
        segment_index=segment_index,
        source_snapshots=source_snapshots,
        default_duration_seconds=default_segment_duration,
    )
    return prepare_segment(
        show_config=show_config,
        brief=brief,
        memory_store=memory_store,
        tts_dir=tts_dir,
        studio_pages_dir=studio_pages_dir,
        tts_generator=tts_generator,
        ffmpeg_path=ffmpeg_path,
        tts_parallelism=tts_parallelism,
        tts_max_chars_per_chunk=tts_max_chars_per_chunk,
    )


async def _produce_segments(
    *,
    show_config,
    segment_queue: asyncio.Queue,
    stop_event: asyncio.Event,
    executor: ThreadPoolExecutor,
    memory_store: BroadcastMemoryStore,
    tts_dir: Path,
    studio_pages_dir: Path,
    ffmpeg_path: str,
    default_segment_duration: int | None,
    tts_parallelism: int,
    tts_max_chars_per_chunk: int,
) -> None:
    loop = asyncio.get_running_loop()
    segment_index = 0
    tts_generator = _build_tts_generator(show_config.tts_voice)
    while not stop_event.is_set():
        if segment_queue.full():
            await asyncio.sleep(1)
            continue
        try:
            segment = await loop.run_in_executor(
                executor,
                lambda: _prepare_show_segment(
                    show_config=show_config,
                    segment_index=segment_index,
                    memory_store=memory_store,
                    tts_dir=tts_dir,
                    studio_pages_dir=studio_pages_dir,
                    tts_generator=tts_generator,
                    ffmpeg_path=ffmpeg_path,
                    default_segment_duration=default_segment_duration,
                    tts_parallelism=tts_parallelism,
                    tts_max_chars_per_chunk=tts_max_chars_per_chunk,
                ),
            )
            await segment_queue.put(segment)
            segment_index += 1
            logger.info(
                "Queued %s segment %s from %s (%ss audio). Queue size: %s",
                segment.kind,
                segment.segment_id,
                segment.provider_name,
                round(segment.actual_audio_duration_seconds, 1),
                segment_queue.qsize(),
            )
        except Exception as error:
            logger.error("Segment preparation failed: %s", error)
            await asyncio.sleep(5)


async def _load_segment_page(page, studio_page_path: Path | None) -> None:
    if studio_page_path is None:
        return
    await page.goto(studio_page_path.resolve().as_uri(), wait_until="load")
    await page.bring_to_front()


async def run_livestream() -> None:
    load_dotenv(override=False)
    project_root = Path.cwd()
    stream_key = os.getenv("YOUTUBE_STREAM_KEY")
    show_config = load_show_config(project_root=project_root)
    capture_backend = load_capture_backend_config()
    default_segment_duration = _resolve_default_segment_duration()
    segment_buffer_size = int(os.getenv("SEGMENT_BUFFER_SIZE", "3"))
    tts_parallelism = int(os.getenv("TTS_PARALLELISM", "3"))
    tts_max_chars_per_chunk = int(os.getenv("TTS_MAX_CHARS_PER_CHUNK", "450"))
    inter_segment_seconds = _resolve_inter_segment_seconds()

    if not stream_key:
        logger.error("YOUTUBE_STREAM_KEY not provided")
        return

    background_music_path = project_root / "audio" / "song.mp3"
    if not background_music_path.exists():
        logger.error("Background music not found at %s", background_music_path)
        return

    ffmpeg_path = _resolve_ffmpeg_path()
    tts_dir = project_root / "audio" / "tts"
    studio_pages_dir = project_root / "runtime" / "studio_pages" / show_config.show_id
    memory_store = BroadcastMemoryStore(project_root / "memory" / show_config.show_id)
    tts_dir.mkdir(parents=True, exist_ok=True)
    studio_pages_dir.mkdir(parents=True, exist_ok=True)

    segment_queue: asyncio.Queue = asyncio.Queue(maxsize=segment_buffer_size)
    stop_event = asyncio.Event()
    executor = ThreadPoolExecutor(max_workers=1)

    display_context = managed_virtual_display(capture_backend)
    with display_context as virtual_display:
        browser_env = virtual_display.browser_env if virtual_display is not None else None
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                **browser_launch_kwargs(capture_backend, browser_env=browser_env)
            )
            page = await browser.new_page(viewport={"width": capture_backend.width, "height": capture_backend.height})
            logger.info(
                "Running show=%s (%s) with capture backend=%s orientation=%s aspect=%s fps=%s size=%sx%s",
                show_config.title,
                show_config.show_id,
                capture_backend.name,
                capture_backend.orientation,
                capture_backend.aspect_ratio_label,
                capture_backend.fps,
                capture_backend.width,
                capture_backend.height,
            )
            if virtual_display is not None:
                logger.info("Using isolated virtual display %s", virtual_display.display)

            producer_task = asyncio.create_task(
                _produce_segments(
                    show_config=show_config,
                    segment_queue=segment_queue,
                    stop_event=stop_event,
                    executor=executor,
                    memory_store=memory_store,
                    tts_dir=tts_dir,
                    studio_pages_dir=studio_pages_dir,
                    ffmpeg_path=ffmpeg_path,
                    default_segment_duration=default_segment_duration,
                    tts_parallelism=tts_parallelism,
                    tts_max_chars_per_chunk=tts_max_chars_per_chunk,
                )
            )

            try:
                while True:
                    segment = await segment_queue.get()
                    logger.info("Starting playout for segment %s", segment.segment_id)
                    await _load_segment_page(page, segment.studio_page_path)
                    await stream_segment(
                        page=page,
                        stream_key=stream_key,
                        background_music_path=str(background_music_path),
                        segment=segment,
                        capture_backend=capture_backend,
                        ffmpeg_path=ffmpeg_path,
                    )
                    memory_store.record_segment(segment)
                    segment_queue.task_done()
                    if inter_segment_seconds > 0:
                        logger.info(
                            "Starting %ss music intermission after segment %s",
                            inter_segment_seconds,
                            segment.segment_id,
                        )
                        intermission_segment = prepare_intermission_segment(
                            duration_seconds=inter_segment_seconds,
                            tts_dir=tts_dir,
                            ffmpeg_path=ffmpeg_path,
                            show_config=show_config,
                            studio_pages_dir=studio_pages_dir,
                        )
                        await _load_segment_page(page, intermission_segment.studio_page_path)
                        await stream_segment(
                            page=page,
                            stream_key=stream_key,
                            background_music_path=str(background_music_path),
                            segment=intermission_segment,
                            capture_backend=capture_backend,
                            ffmpeg_path=ffmpeg_path,
                        )
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
