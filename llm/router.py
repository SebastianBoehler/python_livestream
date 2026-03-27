"""Provider routing for news generation."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from llm import gemini as gemini_llm
from llm import grok as grok_llm
from llm import openrouter as openrouter_llm
from llm.prompts import build_news_user_prompt

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class GeneratedNews:
    script: str
    provider_name: str


def generate_news_content(
    base_prompt: str,
    memory_context: str,
    target_duration_seconds: int,
) -> GeneratedNews:
    prompt = build_news_user_prompt(base_prompt, memory_context, target_duration_seconds)
    errors: list[str] = []
    for provider_name in _provider_order():
        generator = _provider_generator(provider_name)
        logger.info("Generating news content with provider %s", provider_name)
        try:
            return GeneratedNews(script=generator(prompt), provider_name=provider_name)
        except Exception as error:
            logger.warning("Provider %s failed: %s", provider_name, error)
            errors.append(f"{provider_name}: {error}")
    joined_errors = "; ".join(errors) or "No providers configured"
    raise RuntimeError(f"All configured news providers failed: {joined_errors}")


def _provider_order() -> list[str]:
    configured = os.getenv("NEWS_LLM_PROVIDER_ORDER")
    if configured:
        providers = [item.strip() for item in configured.split(",") if item.strip()]
        if providers:
            return providers
    return [os.getenv("NEWS_LLM_PROVIDER", "xai").strip()]


def _provider_generator(provider_name: str):
    normalized = provider_name.lower()
    if normalized == "xai":
        return grok_llm.generate
    if normalized == "gemini":
        return gemini_llm.generate
    if normalized == "openrouter":
        return openrouter_llm.generate
    raise ValueError(f"Unsupported provider: {provider_name}")

