import torch
import torchaudio as ta
from chatterbox.tts import ChatterboxTTS

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
            wav = model.generate(segment)
            segments.append(wav)
        start = end
        while start < length and text[start] == " ":
            start += 1
    if not segments:
        return torch.empty(0)
    return torch.cat(segments, dim=1)

def generate_tts_audio(text: str, output_file: str, model: ChatterboxTTS, max_chars: int = MAX_CHARS) -> str:
    """Generate a single audio file from potentially long text."""
    waveform = synthesize_long_text(text, model, max_chars)
    ta.save(output_file, waveform, model.sr)
    return output_file
