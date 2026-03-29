"""Prompt helpers shared across provider implementations."""

from __future__ import annotations

from shows.models import SegmentBrief, ShowConfig, SourceSnapshot


DEFAULT_SPEECH_REQUIREMENTS = """
You are writing a spoken livestream script that will be converted to speech.

Requirements:
- Sound natural when spoken aloud
- Avoid markdown, bullet points, citations, timestamps, and formatting artifacts
- Prefer concrete developments over vague filler
- Do not repeat earlier coverage unless there is a meaningful update
- Keep transitions tight and easy to follow
- End with a brief sign-off or handoff that fits the show format
""".strip()


def build_system_instruction(show_config: ShowConfig, brief: SegmentBrief) -> str:
    return "\n\n".join(
        [
            show_config.llm_system_instruction.strip(),
            f"Show title: {show_config.title}",
            f"Host persona: {show_config.host_name}, {show_config.host_role}",
            f"Current segment type: {brief.segment_template.kind}",
            DEFAULT_SPEECH_REQUIREMENTS,
        ]
    )


def build_user_prompt(
    *,
    show_config: ShowConfig,
    brief: SegmentBrief,
    memory_context: str,
) -> str:
    target_words = max(120, int(brief.target_duration_seconds * 2.4))
    source_digest = _build_source_digest(brief.source_snapshots)
    context_block = memory_context.strip() or "No prior broadcast memory is available yet."
    return (
        f"{show_config.base_prompt}\n\n"
        f"Show description: {show_config.description}\n"
        f"Segment label: {brief.segment_template.label}\n"
        f"Segment instructions: {brief.segment_template.instructions}\n"
        f"Target spoken duration: about {brief.target_duration_seconds} seconds "
        f"({target_words} words maximum).\n\n"
        "Write one polished spoken segment for this show.\n"
        "Use the source digest below as the primary reporting context.\n\n"
        "Broadcast memory:\n"
        f"{context_block}\n\n"
        "Source digest:\n"
        f"{source_digest}"
    )


def _build_source_digest(source_snapshots: tuple[SourceSnapshot, ...]) -> str:
    lines: list[str] = []
    for snapshot in source_snapshots:
        hint_suffix = f" Hint: {snapshot.prompt_hint}." if snapshot.prompt_hint else ""
        lines.append(f"[{snapshot.name}] Source type: {snapshot.kind}.{hint_suffix}".strip())
        if not snapshot.items:
            lines.append("- No source items were retrieved.")
            lines.append("")
            continue
        for item in snapshot.items:
            detail_parts = [item.title]
            if item.summary:
                detail_parts.append(item.summary)
            if item.published_at:
                detail_parts.append(f"Published: {item.published_at}")
            if item.url:
                detail_parts.append(f"URL: {item.url}")
            lines.append(f"- {' | '.join(part for part in detail_parts if part)}")
        lines.append("")
    return "\n".join(lines).strip()


__all__ = ["build_system_instruction", "build_user_prompt"]
