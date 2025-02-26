#!/usr/bin/env python3
"""
Example script demonstrating how to use the Kokoro TTS wrapper.
"""

import os
from kokoro_wrapper import KokoroTTS

def main():
    """Run a simple demonstration of the Kokoro TTS wrapper."""
    # Initialize the TTS system
    tts = KokoroTTS()
    
    # Create output directory if it doesn't exist
    os.makedirs("../audio/tts", exist_ok=True)
    
    # Simple example with default voice (bella)
    tts.speak(
        "Hello! This is a demonstration of the Kokoro TTS system.",
        output_file="../audio/tts/hello.wav"
    )
    
    # Example with a different voice
    tts.speak(
        "This is Sarah's voice. It sounds a bit different from Bella's voice.",
        voice="sarah",
        output_file="../audio/tts/hello_sarah.wav"
    )
    
    # Example with a long text
    long_text = """
    Text-to-speech (TTS) is a type of speech synthesis application that is used to create a spoken sound version of the text in a computer document, such as a help file or a Web page. TTS can enable the reading of computer display information for the visually challenged person, or may simply be used to augment the reading of a text message.
    
    Current TTS applications include voice-enabled e-mail and spoken prompts in voice response systems. Many computer operating systems have included speech synthesizers since the early 1990s.
    
    Kokoro is an advanced TTS system that provides high-quality, natural-sounding speech synthesis with support for multiple voices and languages. It uses deep learning techniques to generate speech that sounds more natural and expressive than traditional TTS systems.
    """
    
    tts.speak_long_text(
        long_text,
        voice="bella",
        output_file="../audio/tts/long_text.wav"
    )
    
    # List available voices
    print("Available voices:")
    for voice in tts.list_available_voices():
        print(f"- {voice}")


if __name__ == "__main__":
    main()
