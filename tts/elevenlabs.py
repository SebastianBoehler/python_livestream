"""ElevenLabs TTS helper."""

import os
from typing import List

from elevenlabs import ElevenLabs


def generate(lines: List[str], output_file: str) -> str:
    """Generate speech using the ElevenLabs API."""
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY not found in environment variables")

    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
    model_id = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")

    client = ElevenLabs(api_key=api_key)
    text = " ".join(lines)
    audio_stream = client.text_to_speech.convert(
        voice_id=voice_id,
        text=text,
        model_id=model_id,
        output_format="mp3_44100_128",
    )
    audio_bytes = b"".join(audio_stream)
    with open(output_file, "wb") as f:
        f.write(audio_bytes)
    return output_file


if __name__ == "__main__":
    generate(["Hello from ElevenLabs."], "example.wav")

__all__ = ["generate"]
