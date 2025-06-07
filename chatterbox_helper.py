import torch
import torchaudio as ta
from chatterbox.tts import ChatterboxTTS

MAX_CHARS = 300


def get_device() -> str:
    """Detect and return the best available device for torch: 'cuda', then 'mps', else 'cpu'."""
    if torch.cuda.is_available():
        return "cuda"
    elif torch.backends.mps.is_available():
        return "mps"
    else:
        return "cpu"


def get_map_location():
    """Returns the torch.device object for loading models on the detected device."""
    return torch.device(get_device())

# Expose and patch torch.load to always use the correct map_location unless overridden
# Usage: torch_load_original(..., map_location=get_map_location())
torch_load_original = torch.load

def patched_torch_load(*args, **kwargs):
    """Patched torch.load that uses the correct map_location unless overridden."""
    if 'map_location' not in kwargs:
        kwargs['map_location'] = get_map_location()
    return torch_load_original(*args, **kwargs)

torch.load = patched_torch_load

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

def generate_tts_audio(text: str, output_file: str, model: ChatterboxTTS, max_chars: int = MAX_CHARS) -> str:
    """Generate a single audio file from potentially long text."""
    waveform = synthesize_long_text(text, model, max_chars)
    ta.save(output_file, waveform, model.sr)
    return output_file
