#!/usr/bin/env python3
import os
import subprocess
import tempfile
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_audio_duration(audio_path, ffmpeg_path='ffmpeg'):
    """
    Get the duration of an audio file in seconds.
    
    Args:
        audio_path (str): Path to the audio file
        ffmpeg_path (str): Path to the FFmpeg executable
        
    Returns:
        float: Duration of the audio file in seconds
    """
    try:
        # Use FFmpeg to get the duration
        command = [
            ffmpeg_path,
            '-i', audio_path,
            '-hide_banner'
        ]
        
        # FFmpeg outputs to stderr for file info
        result = subprocess.run(
            command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            check=False  # Don't raise exception on non-zero exit
        )
        
        # Parse the output to find duration
        stderr_output = result.stderr.decode('utf-8')
        
        # Look for Duration: HH:MM:SS.MS
        for line in stderr_output.split('\n'):
            if 'Duration:' in line:
                time_str = line.split('Duration:')[1].split(',')[0].strip()
                h, m, s = time_str.split(':')
                duration = float(h) * 3600 + float(m) * 60 + float(s)
                return duration
                
        # If we couldn't find duration, raise an exception
        raise ValueError(f"Could not determine duration from FFmpeg output: {stderr_output}")
        
    except Exception as e:
        logger.error(f"Error getting audio duration: {str(e)}")
        raise
