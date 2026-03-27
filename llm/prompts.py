"""Prompt helpers shared across provider implementations."""

NEWS_SYSTEM_INSTRUCTION = """
You are a professional news anchor delivering a concise and well-researched market bulletin.
Your responses will be converted to speech using TTS.

Requirements:
- Sound natural when spoken aloud
- Avoid markdown, bullet points, citations, timestamps, and formatting artifacts
- Focus on the last 24 hours
- Prefer consequential developments over generic summaries
- Do not repeat earlier coverage unless there is a meaningful update
- End with a brief sign-off
""".strip()


def build_news_user_prompt(
    base_prompt: str,
    memory_context: str,
    target_duration_seconds: int,
) -> str:
    target_words = max(140, int(target_duration_seconds * 2.5))
    context_block = memory_context.strip() or "No prior broadcast memory is available yet."
    return (
        f"{base_prompt}\n\n"
        f"Target spoken duration: about {target_duration_seconds} seconds "
        f"({target_words} words maximum).\n\n"
        "Keep the bulletin dense, concrete, and easy to read aloud.\n\n"
        "Broadcast memory:\n"
        f"{context_block}"
    )

