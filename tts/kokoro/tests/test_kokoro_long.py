#!/usr/bin/env python3
"""
Test script for the Kokoro TTS system with longer text.
"""

import os
import time
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tts.kokoro_wrapper import KokoroTTS

def main():
    """Main test function."""
    print("Testing Kokoro TTS with longer text...")
    
    # Initialize the TTS system
    tts = KokoroTTS()
    
    # Print available voices
    print(f"Available voices: {', '.join(tts.list_available_voices())}")
    
    # Create output directory if it doesn't exist
    output_dir = Path("audio/tts")
    os.makedirs(output_dir, exist_ok=True)
    
    # Test text (longer paragraph)
    test_text = """
    Welcome to the demonstration of the Kokoro Text-to-Speech system. 
    This system is designed to convert written text into natural-sounding speech.
    It supports multiple voices and can handle long passages of text by automatically
    breaking them into manageable chunks. This feature is particularly useful for
    applications like audiobook creation, voice assistants, and accessibility tools.
    
    The system uses advanced deep learning models to generate human-like speech
    with appropriate intonation, rhythm, and emphasis. Different voices have their
    own unique characteristics, allowing you to choose the one that best fits your needs.
    
    Thank you for trying out the Kokoro TTS system. We hope you find it useful for your projects!
    """
    
    # Test with different voices
    voices = ["bella", "sarah", "george", "michael"]
    
    for voice in voices:
        output_file = output_dir / f"test_kokoro_long_{voice}.wav"
        print(f"\nGenerating long text with voice '{voice}' to {output_file}...")
        
        start_time = time.time()
        tts.speak_long_text(test_text, voice=voice, output_file=str(output_file))
        elapsed_time = time.time() - start_time
        
        print(f"Generation completed in {elapsed_time:.2f} seconds")
        print(f"You can play the audio with:\n  afplay {output_file}")
    
    print("\nLong text test complete!")

if __name__ == "__main__":
    main()
