"""xAI Grok LLM helper."""

import datetime
import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)


def generate(
    prompt: str = "latest finance and crypto news and macro economic landscape",
) -> str:
    """Generate a response using the xAI Grok API."""
    api_key = os.getenv("XAI_API_KEY")
    if not api_key:
        raise ValueError("XAI_API_KEY not found in environment variables")

    url = "https://api.x.ai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    now = datetime.datetime.utcnow()
    payload = {
        "messages": [{"role": "user", "content": prompt}],
        "search_parameters": {
            "mode": "auto",
            "from_date": (now - datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
            "to_date": now.strftime("%Y-%m-%d"),
        },
        "model": "grok-3-latest",
    }

    logger.info("Requesting Grok completion")
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    data: Any = response.json()

    choices = data.get("choices")
    if not choices:
        raise ValueError("No choices returned from Grok API")
    message = choices[0].get("message")
    if not message:
        raise ValueError("No message in Grok API response")
    content = message.get("content")
    if not isinstance(content, str):
        raise ValueError("Invalid content returned from Grok API")

    logger.info("Grok completion generated successfully")
    return content


__all__ = ["generate"]
