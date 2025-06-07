#!/usr/bin/env python3
import os
import subprocess
import time
import logging
from dotenv import load_dotenv
import torch
from chatterbox.tts import ChatterboxTTS
from llm import generate_news_content
from utils import get_audio_duration
from chatterbox_helper import generate_tts_audio

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)



def stream_segment(
    stream_key: str,
    image_path: str,
    background_music_path: str,
    news_text: str,
    available_time: float,
    ffmpeg_path: str = "ffmpeg",
    tts_model: ChatterboxTTS = None,
) -> float:
    """Stream a single news segment and filler background music."""

    if tts_model is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        tts_model = ChatterboxTTS.from_pretrained(device=device)

    tts_dir = os.path.join(os.getcwd(), "audio", "tts")
    os.makedirs(tts_dir, exist_ok=True)
    timestamp = int(time.time())
    tts_audio_path = os.path.join(tts_dir, f"news_{timestamp}.wav")

    start_time = time.time()
    generate_tts_audio(news_text, tts_audio_path, model=tts_model)
    tts_generation_time = time.time() - start_time

    segment_duration = get_audio_duration(tts_audio_path, ffmpeg_path)
    filler_duration = max(available_time - tts_generation_time - segment_duration, 0)
    total_duration = segment_duration + filler_duration

    fps = 30
    video_bitrate = "4500k"
    buffer_size = "9000k"  # 2x video bitrate for stability
    rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"

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

    safe_command = command.copy()
    safe_command[-1] = safe_command[-1].replace(stream_key, "STREAM_KEY_HIDDEN")
    logger.info("Starting FFmpeg segment:")
    logger.info(" ".join(safe_command))

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
        logger.info(f"Loaded YOUTUBE_STREAM_KEY: {os.getenv('YOUTUBE_STREAM_KEY')}\n")

        stream_key = os.getenv("YOUTUBE_STREAM_KEY")
        if not stream_key:
            logger.error("YOUTUBE_STREAM_KEY not found in .env file")
            return

        if len(stream_key) < 10:
            logger.error("Provided YouTube stream key seems invalid")
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

        device = "cuda" if torch.cuda.is_available() else "cpu"
        tts_model = ChatterboxTTS.from_pretrained(device=device)

        interval_minutes = int(os.getenv("NEWS_INTERVAL_MINUTES", "10"))

        news_topic = (
            "Latest news from the last 24h about crypto and blockchain."
            " From press releases of blockchain / fintech firm over politics and economics."
            " Be detailed and informative. Analyze relations between market moves and news events."
            " Use google search as a grounding for the news."
        )

        interval_seconds = interval_minutes * 60

        while True:
            loop_start = time.time()
            news_content = generate_news_content(news_topic)
            logger.info("Generated news text, starting segment...")
            pre_segment_time = time.time() - loop_start
            remaining_time = max(interval_seconds - pre_segment_time, 0)
            stream_segment(
                stream_key,
                image_path,
                background_music_path,
                news_content,
                available_time=remaining_time,
                ffmpeg_path=ffmpeg_path,
                tts_model=tts_model,
            )

    except Exception as e:
        logger.error(f"Error during livestream: {str(e)}")


if __name__ == "__main__":
    main()
