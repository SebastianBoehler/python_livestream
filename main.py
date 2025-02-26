#!/usr/bin/env python3
import os
import subprocess
import time
import tempfile
import logging
from dotenv import load_dotenv
from tts.kokoro_wrapper import KokoroTTS
from llm import generate_news_content

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_tts_audio(text, output_file, voice="bella"):
    """
    Generate TTS audio from text.
    
    Args:
        text: The text to convert to speech.
        output_file: Path to save the audio file.
        voice: The voice to use for synthesis.
    
    Returns:
        Path to the generated audio file.
    """
    logger.info(f"Generating TTS audio with voice '{voice}'...")
    
    # Initialize the TTS system
    tts = KokoroTTS()
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Generate audio
    if len(text) > 300:
        tts.speak_long_text(text, voice=voice, output_file=output_file)
    else:
        tts.speak(text, voice=voice, output_file=output_file)
    
    logger.info(f"TTS audio generated and saved to: {output_file}")
    return output_file

def main():
    """
    YouTube livestream script that generates news content, converts it to speech,
    mixes it with background music, and streams it to YouTube.
    """
    try:
        # Load environment variables from .env
        load_dotenv(override=True)
        logger.info(f"Loaded GEMINI_API_KEY: {os.getenv('GEMINI_API_KEY')}")
        logger.info(f"Loaded YOUTUBE_STREAM_KEY: {os.getenv('YOUTUBE_STREAM_KEY')}")
        
        # Get YouTube stream key from environment variables
        stream_key = os.getenv('YOUTUBE_STREAM_KEY')
        if not stream_key:
            logger.error("YOUTUBE_STREAM_KEY not found in .env file")
            return
        
        # Check if stream key looks valid
        if not stream_key or len(stream_key) < 10:
            logger.error(f"YouTube stream key appears invalid: '{stream_key}'")
            logger.error("Please check your .env file and ensure YOUTUBE_STREAM_KEY is set correctly")
            return
        else:
            logger.info(f"Using YouTube stream key (first 5 chars): {stream_key[:5]}...")
        
        # Define paths
        image_path = os.path.join(os.getcwd(), 'screenshot.png')
        background_music_path = os.path.join(os.getcwd(), 'audio', 'song.mp3')
        
        # Check if files exist
        if not os.path.exists(image_path):
            logger.error(f"Image file not found at {image_path}")
            return
        
        if not os.path.exists(background_music_path):
            logger.error(f"Background music file not found at {background_music_path}")
            return
        
        # Generate news content about crypto
        news_topic = """
            Latest news from the last 24h about crypto and blockchain. 
            From press releases of blockchain / fintech firm over politics and economics. 
            Be detailed and informative. Analyze relations between market moves and news events.

            Use google search as a grounding for the news.
            """
        news_content = generate_news_content(news_topic)
        
        # Print the generated news content
        logger.info("Generated News Content:")
        print("\n" + "="*80)
        print("GENERATED NEWS CONTENT:")
        print("="*80)
        print(news_content)
        print("="*80 + "\n")
        
        # Generate TTS audio from news content
        tts_dir = os.path.join(os.getcwd(), 'audio', 'tts')
        os.makedirs(tts_dir, exist_ok=True)
        timestamp = int(time.time())
        tts_audio_path = os.path.join(tts_dir, f"news_bella_{timestamp}.wav")
        generate_tts_audio(news_content, tts_audio_path, voice="bella")
        
        # No longer mixing audio - we'll use separate audio pipes in FFmpeg
        logger.info("Using separate audio pipes for news audio and background music...")
        
        # Determine FFmpeg path
        ffmpeg_path = 'ffmpeg'  # Default to ffmpeg in PATH
        for possible_path in ['/opt/homebrew/bin/ffmpeg', '/usr/bin/ffmpeg']:
            if os.path.exists(possible_path):
                ffmpeg_path = possible_path
                break
        
        logger.info(f"Using FFmpeg at: {ffmpeg_path}")
        
        # Set streaming parameters
        fps = 30
        video_bitrate = '4500k'
        buffer_size = '9000k'  # 2x video bitrate for stability
        rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
        
        logger.info(f"Streaming to URL: {rtmp_url[:30]}...")
        
        # Build a simplified FFmpeg command for debugging
        command = [
            ffmpeg_path,
            '-v', 'info',                    # Increased verbosity for debugging
            '-stats',                        # Show progress stats
            '-re',                           # Read input at native frame rate (important for streaming)
            '-loop', '1',                    # Loop the image
            '-i', image_path,                # Input image (index 0)
            '-i', tts_audio_path,            # Input TTS audio (index 1)
            '-stream_loop', '-1',            # Loop the background music indefinitely
            '-i', background_music_path,     # Input background music (index 2)
            
            # Basic video settings
            '-c:v', 'libx264',               # Video codec
            '-preset', 'veryfast',           # Encoding preset
            '-tune', 'zerolatency',          # Optimize for streaming
            '-pix_fmt', 'yuv420p',           # Pixel format for compatibility
            '-r', str(fps),                  # Output frame rate
            '-g', str(fps * 2),              # GOP size (2 seconds)
            '-b:v', video_bitrate,           # Video bitrate
            '-maxrate', video_bitrate,       # Maximum bitrate
            '-minrate', video_bitrate,       # Minimum bitrate (CBR mode)
            '-bufsize', buffer_size,         # Buffer size
            
            # Simplified audio filter - just mix the two audio streams with different volumes
            '-filter_complex',
            '[1:a]volume=1.0[news];[2:a]volume=0.04[bg];[news][bg]amix=inputs=2:duration=longest[aout]',
            
            # Map streams to output
            '-map', '0:v',                   # Map video from input 0 (image)
            '-map', '[aout]',                # Map audio from filter output
            
            # Configure audio codec and settings
            '-c:a', 'aac',                   # Audio codec
            '-b:a', '128k',                  # Audio bitrate
            '-ar', '44100',                  # Audio sample rate
            
            # Output to YouTube
            '-f', 'flv',                     # Output format
            rtmp_url                         # Output URL
        ]
        
        # Print the command for debugging (hide stream key)
        safe_command = command.copy()
        safe_command[-1] = safe_command[-1].replace(stream_key, "STREAM_KEY_HIDDEN")
        logger.info("Starting stream with command:")
        logger.info(" ".join(safe_command))
        
        # Start the FFmpeg process
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        logger.info("Stream started! Press Ctrl+C to stop.")
        
        # Monitor the process
        try:
            # Read stderr in real-time to capture FFmpeg output
            for line in process.stderr:
                # Log FFmpeg output for debugging
                if "error" in line.lower():
                    logger.error(f"FFmpeg ERROR: {line.strip()}")
                elif "warning" in line.lower():
                    logger.warning(f"FFmpeg WARNING: {line.strip()}")
                elif "speed" in line.lower() or "frame=" in line.lower():
                    # This is just progress info, log at info level
                    if "frame=" in line.lower():
                        logger.info(f"FFmpeg progress: {line.strip()}")
                else:
                    logger.info(f"FFmpeg: {line.strip()}")
                
                # Check if process is still running
                if process.poll() is not None:
                    logger.error("FFmpeg process terminated unexpectedly")
                    break
            
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt. Stopping stream...")
        finally:
            # Terminate the process gracefully
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
            
            logger.info("Stream stopped.")
            
            # Clean up temporary files
            if os.path.exists(tts_audio_path):
                os.remove(tts_audio_path)
                logger.info(f"Temporary file removed: {tts_audio_path}")
    
    except Exception as e:
        logger.error(f"Error during livestream: {str(e)}")

if __name__ == "__main__":
    main()
