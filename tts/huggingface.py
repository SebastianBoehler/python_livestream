import os
from typing import List
from huggingface_hub import InferenceClient

# models:
# "canopylabs/orpheus-3b-0.1-ft" orpheus supports many different languages
# "ResembleAI/chatterbox"

def get_client() -> InferenceClient:
    """Create an InferenceClient using the HF_TOKEN environment variable."""
    api_key = os.getenv("HF_TOKEN")
    if not api_key:
        raise ValueError("HF_TOKEN not found in environment variables")
    return InferenceClient(provider="fal-ai", api_key=api_key)


def generate(
    lines: List[str],
    output_file: str,
) -> str:
    """Generate speech using the Hugging Face Inference API."""
    model = "ResembleAI/chatterbox"
    client = get_client()
    text = " ".join(lines)
    audio_bytes = client.text_to_speech(text, model=model)
    with open(output_file, "wb") as f:
        f.write(audio_bytes)
    return output_file


__all__ = ["generate"]
