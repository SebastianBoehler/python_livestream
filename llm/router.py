"""Provider routing for script generation."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from llm import gemini as gemini_llm
from llm import grok as grok_llm
from llm import openrouter as openrouter_llm

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class GeneratedScript:
    script: str
    provider_name: str


def generate_script_content(
    *,
    system_instruction: str,
    user_prompt: str,
) -> GeneratedScript:
    errors: list[str] = []
    for provider_name in _provider_order():
        generator = _provider_generator(provider_name)
        logger.info("Generating segment with provider %s", provider_name)
        try:
            return GeneratedScript(
                script=generator(user_prompt, system_instruction=system_instruction),
                provider_name=provider_name,
            )
        except Exception as error:
            logger.warning("Provider %s failed: %s", provider_name, error)
            errors.append(f"{provider_name}: {error}")
    joined_errors = "; ".join(errors) or "No providers configured"
    raise RuntimeError(f"All configured script providers failed: {joined_errors}")


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


__all__ = ["GeneratedScript", "generate_script_content"]
