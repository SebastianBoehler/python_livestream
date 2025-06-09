#!/usr/bin/env python3
import os
import subprocess
import time
import logging
from concurrent.futures import ThreadPoolExecutor, Future
from dotenv import load_dotenv
from llm import generate as generate_news_content
from utils import get_audio_duration, get_rtmp_url
from tts.gemini import generate as generate_tts_audio

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def stream_segment(
    stream_key: str,
    image_path: str,
    background_music_path: str,
    tts_audio_path: str,
    available_time: float,
    ffmpeg_path: str = "ffmpeg",
    platform: str = "youtube",
) -> float:
    """Stream a pre-generated news segment and filler background music."""

    segment_duration = get_audio_duration(tts_audio_path, ffmpeg_path)
    filler_duration = max(available_time - segment_duration, 0)
    total_duration = segment_duration + filler_duration

    fps = 30
    video_bitrate = "6800k"  # YouTube recommends ~6.8 Mbps for 1080p
    buffer_size = "13600k"  # 2x video bitrate for stability
    rtmp_url = get_rtmp_url(stream_key, platform)

    command = [
        ffmpeg_path,
        "-v",
        "info",
        "-stats",
        "-re",
        "-loop",
        "1",
        "-i",
        image_path,
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
        "-b:v",
        video_bitrate,
        "-maxrate",
        video_bitrate,
        "-minrate",
        video_bitrate,
        "-bufsize",
        buffer_size,
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

    logger.info("Starting FFmpeg segment:")

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )

    try:
        for line in process.stderr:
            if "error" in line.lower():
                logger.error(f"FFmpeg ERROR: {line.strip()}")
            elif "warning" in line.lower():
                logger.warning(f"FFmpeg WARNING: {line.strip()}")
            elif "frame=" in line.lower():
                logger.info(f"FFmpeg: {line.strip()}")
    except KeyboardInterrupt:
        logger.info("Segment interrupted by user")
        process.terminate()
    finally:
        if process.poll() is None:
            process.wait()

    if os.path.exists(tts_audio_path):
        os.remove(tts_audio_path)
        logger.info(f"Removed temporary file: {tts_audio_path}")

    logger.info("Segment finished")
    return total_duration


def main():
    """Run continuous livestream with scheduled news segments."""

    try:
        load_dotenv(override=True)
        logger.info(f"Loaded GEMINI_API_KEY: {os.getenv('GEMINI_API_KEY')}")
        platform = os.getenv("STREAM_PLATFORM", "youtube").lower()
        if platform == "twitch":
            stream_key = os.getenv("TWITCH_STREAM_KEY")
        else:
            stream_key = os.getenv("YOUTUBE_STREAM_KEY")

        logger.info("Streaming platform: %s", platform)

        if not stream_key:
            logger.error("No stream key found for platform %s", platform)
            return

        if len(stream_key) < 10:
            logger.error("Provided stream key seems invalid")
            return

        image_path = os.path.join(os.getcwd(), "screenshot.png")
        background_music_path = os.path.join(os.getcwd(), "audio", "song.mp3")

        if not os.path.exists(image_path) or not os.path.exists(background_music_path):
            logger.error("Required image or background music is missing")
            return

        ffmpeg_path = "ffmpeg"
        for possible_path in ["/opt/homebrew/bin/ffmpeg", "/usr/bin/ffmpeg"]:
            if os.path.exists(possible_path):
                ffmpeg_path = possible_path
                break

        interval_minutes = int(os.getenv("NEWS_INTERVAL_MINUTES", "30"))

        news_topic = (
            "Latest news from the last 24h about crypto and blockchain."
            " From press releases of blockchain / fintech firm over politics and economics."
            " Be detailed and informative. Analyze relations between market moves and news events."
            " Use google search as a grounding for the news."
        )

        interval_seconds = interval_minutes * 60

        tts_dir = os.path.join(os.getcwd(), "audio", "tts")
        os.makedirs(tts_dir, exist_ok=True)

        executor = ThreadPoolExecutor(max_workers=1)

        # Pre-generate the first segment
        first_news = generate_news_content(news_topic)
        audio_path = os.path.join(tts_dir, f"news_{int(time.time())}.wav")
        future: Future[str] = executor.submit(generate_tts_audio, [first_news], audio_path)

        while True:
            # start_loop = time.time() was unused

            # Wait for the prepared audio
            tts_audio_path = future.result()

            # Kick off generation for the next segment
            next_news = generate_news_content(news_topic)
            next_audio = os.path.join(tts_dir, f"news_{int(time.time())}.wav")
            future = executor.submit(generate_tts_audio, [next_news], next_audio)

            stream_segment(
                stream_key,
                image_path,
                background_music_path,
                tts_audio_path,
                available_time=interval_seconds,
                ffmpeg_path=ffmpeg_path,
                platform=platform,
            )

    except Exception as e:
        logger.error(f"Error during livestream: {str(e)}")


if __name__ == "__main__":
    main()
