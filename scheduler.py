#!/usr/bin/env python3
"""
Scheduler for periodic TTS segments and live streaming with FFmpeg using a dynamic playlist.
"""
import os
import sys
import time
import logging
import threading
import subprocess
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

# Import existing project functions
from llm import generate_news_content
from main import generate_tts_audio
from utils import prepare_livestream_audio

# Configure logging
tlogging = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AudioScheduler:
    def __init__(self,
                 audio_dir: str = "audio/tts",
                 bg_music: str = "audio/song.mp3",
                 playlist_file: str = "playlist.txt",
                 image_file: str = "screenshot.png",
                 interval_minutes: int = 15):
        """
        Initialize scheduler.
        - Generates TTS audio and mixes with background music every interval
        - Updates a concat playlist for FFmpeg
        - Starts FFmpeg streaming with the playlist
        """
        load_dotenv(override=True)
        stream_key = os.getenv('YOUTUBE_STREAM_KEY')
        if not stream_key:
            logging.error('YOUTUBE_STREAM_KEY not found in environment')
            sys.exit(1)
        self.stream_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
        
        self.audio_dir = Path(audio_dir)
        self.bg_music = Path(bg_music)
        self.playlist = Path(playlist_file)
        self.image = Path(image_file)
        self.interval = interval_minutes
        self.scheduler = BackgroundScheduler()
        self.ffmpeg_process = None
        
        # Ensure directories and initial playlist
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self._init_playlist()

    def _init_playlist(self):
        # Create initial playlist with just background music
        with open(self.playlist, 'w') as f:
            f.write(f"file '{self.bg_music.resolve()}'\n")
        logging.info(f"Initialized playlist: {self.playlist}")

    def _update_playlist(self, segment_file: Path):
        # Append a new segment entry atomically
        temp = self.playlist.with_suffix('.tmp')
        with open(temp, 'w') as out:
            with open(self.playlist) as src:
                out.write(src.read())
            out.write(f"file '{segment_file.resolve()}'\n")
        os.replace(temp, self.playlist)
        logging.info(f"Appended segment to playlist: {segment_file}")

    def generate_and_update(self):
        try:
            logging.info("Generating news content for scheduled segment...")
            content = generate_news_content()
            wav_path = self.audio_dir / f"tts_{int(time.time())}.wav"
            generate_tts_audio(content, str(wav_path))
            mp3_path = self.audio_dir / f"segment_{int(time.time())}.mp3"
            prepare_livestream_audio(str(wav_path), str(self.bg_music), str(mp3_path))
            wav_path.unlink(missing_ok=True)
            self._update_playlist(mp3_path)
        except Exception as e:
            logging.error(f"Scheduled segment generation failed: {e}")

    def start_scheduler(self):
        self.scheduler.add_job(
            self.generate_and_update,
            'interval',
            minutes=self.interval,
            next_run_time=datetime.now()
        )
        self.scheduler.start()
        logging.info(f"Started scheduler: interval={self.interval} min")

    def _monitor_ffmpeg(self):
        # Log FFmpeg output
        while self.ffmpeg_process and self.ffmpeg_process.poll() is None:
            line = self.ffmpeg_process.stderr.readline()
            if not line:
                break
            if 'error' in line.lower():
                logging.error(f"FFmpeg: {line.strip()}")
            else:
                logging.info(f"FFmpeg: {line.strip()}")
        if self.ffmpeg_process:
            logging.error(f"FFmpeg exited with code {self.ffmpeg_process.returncode}")

    def start_stream(self):
        # Prevent multiple FFmpeg instances
        if self.ffmpeg_process and self.ffmpeg_process.poll() is None:
            logging.warning("FFmpeg stream already running, skipping start")
            return
        # Build FFmpeg command reading playlist and looping image
        cmd = [
            'ffmpeg', '-hide_banner', '-loglevel', 'error',
            '-re',
            '-f', 'concat',
            '-safe', '0',
            '-i', str(self.playlist.resolve()),
            '-loop', '1',
            '-i', str(self.image.resolve()),
            # Map video from image and audio from playlist
            '-map', '1:v',
            '-map', '0:a',
            '-c:v', 'libx264',
            '-preset', 'veryfast',
            '-tune', 'zerolatency',
            '-pix_fmt', 'yuv420p',
            '-r', '30',
            '-g', '60',
            '-b:v', '3000k',
            '-maxrate', '3000k',
            '-minrate', '3000k',
            '-bufsize', '6000k',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-ar', '44100',
            '-shortest',
            '-f', 'flv',
            self.stream_url
        ]
        logging.info(f"Starting FFmpeg stream: {' '.join(cmd)}")
        self.ffmpeg_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        threading.Thread(target=self._monitor_ffmpeg, daemon=True).start()

    def stop(self):
        logging.info("Stopping scheduler and FFmpeg...")
        self.scheduler.shutdown(wait=False)
        if self.ffmpeg_process and self.ffmpeg_process.poll() is None:
            self.ffmpeg_process.terminate()
            try:
                self.ffmpeg_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.ffmpeg_process.kill()

if __name__ == '__main__':
    scheduler = AudioScheduler()
    scheduler.start_scheduler()
    scheduler.start_stream()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.stop()
