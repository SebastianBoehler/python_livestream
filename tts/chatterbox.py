import torch
import torchaudio as ta
from typing import List
from chatterbox.tts import ChatterboxTTS
from utils import get_device  # re-exported for convenience

MAX_CHARS = 300

def synthesize_long_text(text: str, model: ChatterboxTTS, max_chars: int = MAX_CHARS) -> torch.Tensor:
    """Generate audio for text longer than Chatterbox's limit."""
    segments = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + max_chars, length)
        if end < length:
            space_pos = text.rfind(" ", start, end)
            if space_pos > start:
                end = space_pos
        segment = text[start:end].strip()
        if segment:
            wav = model.generate(segment, cfg_weight=0.4, exaggeration=0.5) #cfg controls speed
            segments.append(wav)
        start = end
        while start < length and text[start] == " ":
            start += 1
    if not segments:
        return torch.empty(0)
    return torch.cat(segments, dim=1)

def generate(lines: List[str], output_file: str, model: ChatterboxTTS, max_chars: int = MAX_CHARS) -> str:
    """Generate a single audio file from multiple text segments."""
    text = " ".join(lines)
    waveform = synthesize_long_text(text, model, max_chars)
    ta.save(output_file, waveform, model.sr)
    return output_file


__all__ = ["generate", "synthesize_long_text", "MAX_CHARS", "get_device"]
