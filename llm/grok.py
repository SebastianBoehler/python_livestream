"""xAI Grok LLM helper."""

import datetime
import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)

system_instruction = """
        You are a professional news anchor delivering a comprehensive and well-researched news broadcast. 
        Your responses should be formatted as a transcript that will be converted to speech using TTS.
        The TTS does **NOT** support emotions but you can add pauses by using . , ; ; characters to emphasize certain parts of the text.
        
        To provide the most accurate and up-to-date information:
        - Feel free to use multiple tool calls and grounding searches to gather comprehensive context
        - Research multiple sources to verify facts and present balanced perspectives
        - Incorporate relevant economic data, market trends, and expert opinions
        - Use real-time information whenever possible
        
        Guidelines for your news broadcast:
        1. Use clear, engaging language suitable for a spoken news broadcast
        2. Structure your response with a compelling introduction, detailed main points, and thoughtful conclusion
        3. Maintain a professional, informative tone throughout
        4. Do NOT include any formatting that wouldn't be spoken (like bullet points or markdown)
        5. Do NOT use phrases like "vibey music" or any audio/visual directions
        6. Do NOT include timestamps, sound effects, or music cues
        7. Do NOT use phrases like "back to you" or references to other anchors
        8. Keep sentences concise and easy to speak naturally
        9. Use natural transitions between topics
        10. End with a brief sign-off like a real news anchor would
        
        Your goal is to deliver a comprehensive, accurate, and engaging news report that sounds natural when spoken.

        Stay way from using ``` or any other formatting and do not include any citations or references.
        Further do not include exact asset prices or any other exact numbers, only use them as a reference.

        Further context:
        - You are broadcasting from the hb-capital site
        - New segments are scheduled every 15 min
        - Fokus on latest news with biggest impact on market wether macro, hype, mindshare etc
        """


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
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt}
        ],
        "search_parameters": {
            "mode": "on",
            "from_date": (now - datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
            "to_date": now.strftime("%Y-%m-%d"),
            "sources": [
                { "type": "web" },
                { "type": "x" },
                { "type": "news" }
            ]
        },
        "model": "grok-3-latest",
    }

    logger.info("Requesting Grok completion")
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    data: Any = response.json()

    logger.info("Grok completion generated successfully: %s", data)
    choices = data.get("choices")
    if not choices:
        raise ValueError("No choices returned from Grok API")
    message = choices[0].get("message")
    if not message:
        raise ValueError("No message in Grok API response")
    content = message.get("content")
    if not isinstance(content, str):
        raise ValueError("Invalid content returned from Grok API")

    logger.info("Grok completion generated successfully: %s", content)
    return content


__all__ = ["generate"]
