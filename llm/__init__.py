"""Convenience exports for LLM script generation."""

from __future__ import annotations

from llm.router import GeneratedScript, generate_script_content


def generate_news_content(prompt: str, *, system_instruction: str = "") -> str:
    return generate_script_content(
        system_instruction=system_instruction,
        user_prompt=prompt,
    ).script


def generate(prompt: str, system_instruction: str = "") -> str:
    return generate_news_content(prompt, system_instruction=system_instruction)


__all__ = ["GeneratedScript", "generate", "generate_news_content", "generate_script_content"]
