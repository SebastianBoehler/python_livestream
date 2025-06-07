import torch
import torchaudio as ta
from typing import List
from chatterbox.tts import ChatterboxTTS
from utils import get_device  # re-exported for convenience

MAX_CHARS = 300

def synthesize_long_text(text: str, model: ChatterboxTTS) -> torch.Tensor:
    """Generate audio for text longer than Chatterbox's limit."""
    segments = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + MAX_CHARS, length)
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

def generate(lines: List[str], output_file: str) -> str:
    """Generate a single audio file from multiple text segments."""
    device = get_device()
    model = ChatterboxTTS.from_pretrained(device=device)
    text = " ".join(lines)
    waveform = synthesize_long_text(text, model)
    ta.save(output_file, waveform, model.sr)
    return output_file


__all__ = ["generate"]
