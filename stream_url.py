import asyncio
import logging
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor

from dotenv import load_dotenv
from playwright.async_api import async_playwright

from llm import generate as generate_news_content
from tts.gemini import generate as generate_tts_audio
from utils import get_audio_duration

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def _capture_frames(page, process: subprocess.Popen, fps: int) -> None:
    """Capture screenshots and write them to FFmpeg's stdin."""
    frame_delay = 1 / fps
    while process.poll() is None:
        screenshot = await page.screenshot(type="png")
        try:
            if process.stdin:
                process.stdin.write(screenshot)
                process.stdin.flush()
        except BrokenPipeError:
            break
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
    segment_duration = get_audio_duration(tts_audio_path, ffmpeg_path)
    filler_duration = max(available_time - segment_duration, 0)
    total_duration = segment_duration + filler_duration

    rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"

    command = [
        ffmpeg_path,
        "-v",
        "info",
        "-stats",
        "-f",
        "image2pipe",
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
        "libx264",
        "-preset",
        "veryfast",
        "-tune",
        "zerolatency",
        "-pix_fmt",
        "yuv420p",
        "-r",
        str(fps),
        "-g",
        str(fps * 2),
        "-filter_complex",
        "[1:a]apad,volume=1.0[news];[2:a]volume=0.04[bg];[news][bg]amix=inputs=2:duration=longest[aout]",
        "-map",
        "0:v",
        "-map",
        "[aout]",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
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

    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    capture_task = asyncio.create_task(_capture_frames(page, process, fps))
    await asyncio.to_thread(process.wait)
    capture_task.cancel()
    if process.stdin:
        process.stdin.close()
    await capture_task

    if os.path.exists(tts_audio_path):
        os.remove(tts_audio_path)
        logger.info("Removed temporary file: %s", tts_audio_path)

    logger.info("Segment finished")
    return total_duration


async def run_livestream() -> None:
    """Run continuous livestream of a website with scheduled news segments."""
    load_dotenv()
    stream_key = os.getenv("YOUTUBE_STREAM_KEY")
    url = os.getenv("STREAM_URL")
    fps = int(os.getenv("STREAM_FPS", "1"))
    interval_minutes = int(os.getenv("NEWS_INTERVAL_MINUTES", "30"))

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
        browser = await playwright.chromium.launch()
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        print(f"Straming from {url}")
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
