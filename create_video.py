#!/usr/bin/env python3
"""Generate a news voiceover video."""

import argparse
import logging
import os
import subprocess
import time

from dotenv import load_dotenv

from llm import generate as generate_news_content
from tts.gemini import generate as generate_tts_audio

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def mix_audio_with_video(video_path: str, tts_audio_path: str, output_path: str, ffmpeg_path: str = "ffmpeg") -> None:
    """Overlay TTS audio over a video and save the result."""
    command = [
        ffmpeg_path,
        "-i",
        video_path,
        "-i",
        tts_audio_path,
        "-filter_complex",
        "[0:a][1:a]amix=inputs=2:duration=first[aout]",
        "-map",
        "0:v",
        "-map",
        "[aout]",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-shortest",
        output_path,
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("FFmpeg failed: %s", result.stderr)
        raise RuntimeError("FFmpeg command failed")
    logger.info("Video saved to %s", output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a video with news voiceover")
    parser.add_argument("video", help="Path to the input video file")
    parser.add_argument(
        "--output",
        default="output_with_news.mp4",
        help="Path for the output video",
    )
    parser.add_argument(
        "--prompt",
        default=(
            "Latest news from the last 24h about crypto and blockchain."
        ),
        help="Prompt for news generation",
    )
    args = parser.parse_args()

    load_dotenv(override=True)

    ffmpeg_path = "ffmpeg"
    for possible in ["/opt/homebrew/bin/ffmpeg", "/usr/bin/ffmpeg"]:
        if os.path.exists(possible):
            ffmpeg_path = possible
            break

    if not os.path.exists(args.video):
        logger.error("Video file not found at %s", args.video)
        return

    tts_dir = os.path.join(os.getcwd(), "audio", "tts")
    os.makedirs(tts_dir, exist_ok=True)
    tts_audio_path = os.path.join(tts_dir, f"news_{int(time.time())}.wav")

    news_text = generate_news_content(args.prompt)
    generate_tts_audio([news_text], tts_audio_path)

    try:
        mix_audio_with_video(args.video, tts_audio_path, args.output, ffmpeg_path)
    finally:
        if os.path.exists(tts_audio_path):
            os.remove(tts_audio_path)
            logger.info("Removed temporary file: %s", tts_audio_path)


if __name__ == "__main__":
    main()
