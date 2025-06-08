"""Sesame CSM based TTS helper."""

from typing import List

from transformers import AutoProcessor, CsmForConditionalGeneration

from utils import get_device


def generate(lines: List[str], output_file: str) -> str:
    """Generate speech using Sesame CSM."""
    model_id = "sesame/csm-1b"
    device = get_device()
    processor = AutoProcessor.from_pretrained(model_id)
    model = CsmForConditionalGeneration.from_pretrained(model_id, device_map=device)

    text = " ".join(lines)
    inputs = processor(text, add_special_tokens=True).to(device)
    audio = model.generate(**inputs, output_audio=True)
    processor.save_audio(audio, output_file)
    return output_file


if __name__ == "__main__":
    generate(["Hello from Sesame."], "example.wav")

__all__ = ["generate"]

