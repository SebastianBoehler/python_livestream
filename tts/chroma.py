"""FlashLabs Chroma-4B TTS helper.

Chroma is a multimodal model capable of text-to-speech with voice cloning.
It supports multiple languages including German and various dialects.

Requirements:
- HF_TOKEN environment variable must be set (model is gated)
- transformers and torch packages
"""

import os
from pathlib import Path
from typing import List, Optional

import numpy as np
import requests
import torch
import torchaudio as ta

from utils import get_device

REFERENCE_AUDIO_URL = "https://huggingface.co/FlashLabs/Chroma-4B/resolve/main/assets/reference_audio.wav"
DEFAULT_REFERENCE_TEXT = "The quick brown fox jumps over the lazy dog."

MODEL_ID = "FlashLabs/Chroma-4B"
SAMPLE_RATE = 24000  # Chroma uses Mimi codec at 24kHz


def _get_default_reference_audio() -> str:
    """Download default reference audio if not exists, return path."""
    cache_dir = Path(os.getenv("HF_HOME", Path.home() / ".cache" / "huggingface"))
    ref_audio_path = cache_dir / "chroma_reference_audio.wav"
    
    if not ref_audio_path.exists():
        ref_audio_path.parent.mkdir(parents=True, exist_ok=True)
        hf_token = os.getenv("HF_TOKEN")
        headers = {"Authorization": f"Bearer {hf_token}"} if hf_token else {}
        response = requests.get(REFERENCE_AUDIO_URL, headers=headers)
        response.raise_for_status()
        ref_audio_path.write_bytes(response.content)
    
    return str(ref_audio_path)


def _load_model_and_processor(device: str):
    """Load the Chroma model and processor."""
    from transformers import AutoModelForCausalLM, AutoProcessor

    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        raise ValueError("HF_TOKEN not found in environment variables (required for gated model)")

    # Load model - requires ~22GB VRAM, use CUDA GPU
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        trust_remote_code=True,
        device_map="auto",
        token=hf_token,
        torch_dtype=torch.float16,
    )
    processor = AutoProcessor.from_pretrained(
        MODEL_ID,
        trust_remote_code=True,
        token=hf_token,
    )
    return model, processor


def generate(
    lines: List[str],
    output_file: str,
    reference_audio: Optional[str] = None,
    reference_text: Optional[str] = None,
    max_new_tokens: int = 2048,
    temperature: float = 0.7,
    top_p: float = 0.9,
) -> str:
    """Generate speech using FlashLabs Chroma-4B with voice cloning.

    NOTE: Chroma-4B is a voice cloning model. If no reference audio is provided,
    a default reference from HuggingFace will be downloaded and used.

    Args:
        lines: List of text segments to synthesize.
        output_file: Path to save the output audio file.
        reference_audio: Path to reference audio for voice cloning (optional, uses default if not provided).
        reference_text: Text corresponding to reference audio (optional, uses default if not provided).
        max_new_tokens: Maximum tokens to generate.
        temperature: Sampling temperature.
        top_p: Top-p sampling parameter.

    Returns:
        Path to the generated audio file.
    """
    # Use default reference audio if not provided
    if not reference_audio:
        reference_audio = _get_default_reference_audio()
    if not reference_text:
        reference_text = DEFAULT_REFERENCE_TEXT

    device = get_device()
    model, processor = _load_model_and_processor(device)

    text = " ".join(lines)

    # Build conversation format
    system_prompt = (
        "You are a professional voice narrator. "
        "Read the following text clearly and naturally."
    )

    conversation = [[
        {
            "role": "system",
            "content": [{"type": "text", "text": system_prompt}],
        },
        {
            "role": "user",
            "content": [{"type": "text", "text": text}],
        },
    ]]

    # Prepare reference audio/text for voice cloning
    prompt_audio = [reference_audio]
    prompt_text = [reference_text]

    # Process inputs
    inputs = processor(
        conversation,
        add_generation_prompt=True,
        tokenize=False,
        prompt_audio=prompt_audio,
        prompt_text=prompt_text,
    )

    # Move inputs to device
    inputs = {k: v.to(model.device) if hasattr(v, "to") else v for k, v in inputs.items()}

    # Generate
    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=temperature,
            top_p=top_p,
            use_cache=True,
        )

    # Decode audio using the codec model
    audio_values = model.codec_model.decode(output.permute(0, 2, 1)).audio_values
    audio_np = audio_values[0].cpu().detach().numpy()

    # Convert to tensor for torchaudio
    if audio_np.ndim == 1:
        audio_tensor = torch.from_numpy(audio_np).unsqueeze(0)
    else:
        audio_tensor = torch.from_numpy(audio_np)

    # Save audio
    ta.save(output_file, audio_tensor, SAMPLE_RATE)
    return output_file


def generate_with_cloning(
    lines: List[str],
    output_file: str,
    reference_audio: str,
    reference_text: str,
    **kwargs,
) -> str:
    """Generate speech with voice cloning from reference audio.

    Args:
        lines: List of text segments to synthesize.
        output_file: Path to save the output audio file.
        reference_audio: Path to reference audio for voice cloning.
        reference_text: Text corresponding to reference audio.
        **kwargs: Additional arguments passed to generate().

    Returns:
        Path to the generated audio file.
    """
    return generate(
        lines,
        output_file,
        reference_audio=reference_audio,
        reference_text=reference_text,
        **kwargs,
    )


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    # Uses default reference audio from HuggingFace
    generate(
        ["Hallo, das ist ein Test auf Deutsch."],
        "chroma_test.wav",
    )


__all__ = ["generate", "generate_with_cloning", "SAMPLE_RATE"]
