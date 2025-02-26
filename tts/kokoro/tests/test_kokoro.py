#!/usr/bin/env python3
"""
Test script for Kokoro TTS installation.
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tts.kokoro_wrapper import KokoroTTS

def main():
    """Test the Kokoro TTS installation."""
    print("Testing Kokoro TTS installation...")
    
    # Create output directory
    output_dir = Path("audio/tts")
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize TTS
    tts = KokoroTTS()
    
    # Test with a simple message
    test_text = "Hello! This is a test of the Kokoro TTS system. If you can hear this message, the installation was successful."
    output_file = output_dir / "test_kokoro.wav"
    
    print(f"Generating test audio to {output_file}...")
    tts.speak(test_text, output_file=str(output_file))
    
    print(f"Test complete! Audio saved to {output_file}")
    print("You can play the audio with:")
    print(f"  afplay {output_file}")
    
    # Play the audio
    os.system(f"afplay {output_file}")

if __name__ == "__main__":
    main()
