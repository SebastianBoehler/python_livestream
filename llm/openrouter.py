"""OpenRouter script generation helper."""

from __future__ import annotations

import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)


def generate(prompt: str, *, system_instruction: str | None = None) -> str:
    """Generate a spoken segment using OpenRouter's OpenAI-compatible API."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not found in environment variables")

    payload = _build_payload(prompt, system_instruction=system_instruction)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    site_url = os.getenv("OPENROUTER_SITE_URL")
    if site_url:
        headers["HTTP-Referer"] = site_url
    app_name = os.getenv("OPENROUTER_APP_NAME", "python-livestream")
    headers["X-OpenRouter-Title"] = app_name

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=90,
    )
    response.raise_for_status()
    data: Any = response.json()
    choices = data.get("choices")
    if not choices:
        raise ValueError("No choices returned from OpenRouter")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise ValueError("OpenRouter response did not include a message")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("OpenRouter response content was empty")
    logger.info("OpenRouter response generated successfully")
    return content.strip()


def _build_payload(prompt: str, *, system_instruction: str | None) -> dict[str, Any]:
    configured_models = _split_csv(os.getenv("OPENROUTER_MODELS"))
    model = configured_models[0] if configured_models else os.getenv("OPENROUTER_MODEL", "openrouter/auto")
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_instruction or ""},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
    }
    if len(configured_models) > 1:
        payload["models"] = configured_models
        payload["route"] = "fallback"

    plugins = _split_csv(os.getenv("OPENROUTER_PLUGINS"))
    if plugins:
        payload["plugins"] = [{"id": plugin} for plugin in plugins]

    provider = _build_provider_preferences()
    if provider:
        payload["provider"] = provider
    return payload


def _build_provider_preferences() -> dict[str, Any]:
    provider: dict[str, Any] = {}
    order = _split_csv(os.getenv("OPENROUTER_PROVIDER_ORDER"))
    only = _split_csv(os.getenv("OPENROUTER_PROVIDER_ONLY"))
    ignore = _split_csv(os.getenv("OPENROUTER_PROVIDER_IGNORE"))
    if order:
        provider["order"] = order
    if only:
        provider["only"] = only
    if ignore:
        provider["ignore"] = ignore
    allow_fallbacks = os.getenv("OPENROUTER_ALLOW_FALLBACKS")
    if allow_fallbacks is not None:
        provider["allow_fallbacks"] = allow_fallbacks.lower() == "true"
    max_latency = os.getenv("OPENROUTER_MAX_LATENCY_MS")
    if max_latency:
        provider["preferred_max_latency"] = int(max_latency)
    min_throughput = os.getenv("OPENROUTER_MIN_THROUGHPUT_TPS")
    if min_throughput:
        provider["preferred_min_throughput"] = int(min_throughput)
    max_price = os.getenv("OPENROUTER_MAX_PRICE_USD_PER_MTOK")
    if max_price:
        provider["max_price"] = {"prompt": float(max_price), "completion": float(max_price)}
    return provider


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]
