#!/usr/bin/env python3
"""Simple example demonstrating Chatterbox TTS usage."""
import torch
import torchaudio as ta
from chatterbox.tts import ChatterboxTTS
from chatterbox_helper import get_device  # Also patches torch.load globally


def main() -> None:
    # Device selection is handled by get_device(), which prefers 'cuda', then 'mps', else 'cpu'
    device = get_device()
    model = ChatterboxTTS.from_pretrained(device=device)
    text = "Hello! This is Chatterbox speaking."
    wav = model.generate(text, cfg_weight=0.4, exaggeration=0.5)
    ta.save("example.wav", wav, model.sr)

if __name__ == "__main__":
    main()

