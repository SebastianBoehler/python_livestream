#!/usr/bin/env python3
"""Simple example demonstrating Chatterbox TTS usage."""
import torch
import torchaudio as ta
from chatterbox.tts import ChatterboxTTS

def main() -> None:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = ChatterboxTTS.from_pretrained(device=device)
    text = "Hello! This is Chatterbox speaking."
    wav = model.generate(text)
    ta.save("example.wav", wav, model.sr)

if __name__ == "__main__":
    main()

