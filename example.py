#!/usr/bin/env python3
import torch
import torchaudio as ta
from chatterbox.tts import ChatterboxTTS
from tts.chatterbox import get_device


def main() -> None:
    # Chatterbox TTS
    device = get_device()
    model = ChatterboxTTS.from_pretrained(device=device)
    text = "Hello! This is Chatterbox speaking."
    wav = model.generate(text, cfg_weight=0.4, exaggeration=0.5)
    ta.save("example.wav", wav, model.sr)

    # other examples

if __name__ == "__main__":
    main()

