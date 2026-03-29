"""xAI Grok LLM helper."""

import datetime
import logging
import os
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_INSTRUCTION = """
You are writing a spoken livestream segment.
Keep the copy natural for TTS, avoid markdown and citations, and prioritize concrete developments over filler.
Use search tools when they materially improve accuracy.
"""


def generate(
    prompt: str = "latest finance and crypto news and macro economic landscape",
    *,
    system_instruction: str | None = None,
) -> str:
    """Generate a response using the xAI Responses API with built-in search tools."""
    api_key = os.getenv("XAI_API_KEY")
    if not api_key:
        raise ValueError("XAI_API_KEY not found in environment variables")

    url = "https://api.x.ai/v1/responses"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    now = datetime.datetime.now(datetime.UTC)
    model_name = os.getenv("XAI_MODEL", "grok-4.20-reasoning")
    payload = {
        "instructions": system_instruction or DEFAULT_SYSTEM_INSTRUCTION,
        "input": [
            {
                "role": "user",
                "content": (
                    f"{prompt}\n\n"
                    f"Current UTC time: {now.isoformat()}. "
                    "Focus on developments from the last 24 hours."
                ),
            }
        ],
        "model": model_name,
        "temperature": 0.4,
        "tools": [
            {"type": "web_search"},
            {"type": "x_search"},
        ],
    }

    max_attempts = int(os.getenv("XAI_MAX_RETRIES", "4"))
    response: requests.Response | None = None
    for attempt in range(1, max_attempts + 1):
        logger.info("Requesting Grok response with model %s (attempt %s/%s)", model_name, attempt, max_attempts)
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        if response.ok:
            break
        status_code = response.status_code
        if status_code < 500 and status_code != 429:
            response.raise_for_status()
        logger.warning(
            "Transient xAI error %s on attempt %s/%s: %s",
            status_code,
            attempt,
            max_attempts,
            response.text[:300],
        )
        if attempt == max_attempts:
            response.raise_for_status()
        time.sleep(min(2 ** (attempt - 1), 8))

    if response is None:
        raise RuntimeError("xAI request was not attempted")
    data: Any = response.json()

    output_items = data.get("output")
    if not isinstance(output_items, list):
        raise ValueError("No output returned from xAI Responses API")

    text_chunks: list[str] = []
    for item in output_items:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for content_part in item.get("content", []):
            if (
                isinstance(content_part, dict)
                and content_part.get("type") == "output_text"
                and isinstance(content_part.get("text"), str)
            ):
                text_chunks.append(content_part["text"])

    content = "\n".join(chunk.strip() for chunk in text_chunks if chunk.strip())
    if not content:
        raise ValueError("No text content returned from xAI Responses API")

    logger.info("Grok response generated successfully")
    return content


__all__ = ["generate"]
