"""Google Gemini based TTS helper."""

import mimetypes
import os
import struct
from typing import List

from google import genai
from google.genai import types

def generate(lines: List[str], output_file: str) -> str:
    """Generate speech using Google Gemini TTS."""
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    text = " ".join(lines)
    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=text)],
        )
    ]
    generate_config = types.GenerateContentConfig(
        temperature=1.0,
        response_modalities=["audio"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Charon")
            )
        ),
    )

    audio_data = bytearray()
    mime_type = "audio/wav"
    for chunk in client.models.generate_content_stream(
        model="gemini-2.5-flash-preview-tts",
        contents=contents,
        config=generate_config,
    ):
        if (
            chunk.candidates
            and chunk.candidates[0].content
            and chunk.candidates[0].content.parts
        ):
            part = chunk.candidates[0].content.parts[0]
            if part.inline_data and part.inline_data.data:
                mime_type = part.inline_data.mime_type or mime_type
                audio_data.extend(part.inline_data.data)

    if mime_type != "audio/wav":
        audio_data = convert_to_wav(bytes(audio_data), mime_type)
    with open(output_file, "wb") as f:
        f.write(audio_data)
    return output_file

def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """Generates a WAV file header for the given audio data and parameters.

    Args:
        audio_data: The raw audio data as a bytes object.
        mime_type: Mime type of the audio data.

    Returns:
        A bytes object representing the WAV file header.
    """
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters["bits_per_sample"]
    sample_rate = parameters["rate"]
    num_channels = 1
    data_size = len(audio_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size  # 36 bytes for header fields before data chunk size

    # http://soundfile.sapp.org/doc/WaveFormat/

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",          # ChunkID
        chunk_size,       # ChunkSize (total file size - 8 bytes)
        b"WAVE",          # Format
        b"fmt ",          # Subchunk1ID
        16,               # Subchunk1Size (16 for PCM)
        1,                # AudioFormat (1 for PCM)
        num_channels,     # NumChannels
        sample_rate,      # SampleRate
        byte_rate,        # ByteRate
        block_align,      # BlockAlign
        bits_per_sample,  # BitsPerSample
        b"data",          # Subchunk2ID
        data_size         # Subchunk2Size (size of audio data)
    )
    return header + audio_data

def parse_audio_mime_type(mime_type: str) -> dict[str, int | None]:
    """Parses bits per sample and rate from an audio MIME type string.

    Assumes bits per sample is encoded like "L16" and rate as "rate=xxxxx".

    Args:
        mime_type: The audio MIME type string (e.g., "audio/L16;rate=24000").

    Returns:
        A dictionary with "bits_per_sample" and "rate" keys. Values will be
        integers if found, otherwise None.
    """
    bits_per_sample = 16
    rate = 24000

    # Extract rate from parameters
    parts = mime_type.split(";")
    for param in parts: # Skip the main type part
        param = param.strip()
        if param.lower().startswith("rate="):
            try:
                rate_str = param.split("=", 1)[1]
                rate = int(rate_str)
            except (ValueError, IndexError):
                # Handle cases like "rate=" with no value or non-integer value
                pass # Keep rate as default
        elif param.startswith("audio/L"):
            try:
                bits_per_sample = int(param.split("L", 1)[1])
            except (ValueError, IndexError):
                pass # Keep bits_per_sample as default if conversion fails

    return {"bits_per_sample": bits_per_sample, "rate": rate}


if __name__ == "__main__":
    generate(["Hello from Gemini."], "example.wav")

__all__ = ["generate"]
