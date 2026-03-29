#!/usr/bin/env python3
"""Generate local preview pages for bundled show profiles."""

from __future__ import annotations

import re
import os
from pathlib import Path

from dotenv import load_dotenv

from broadcast.studio_page import (
    render_intermission_page,
    render_preview_index,
    render_segment_page,
)
from shows.briefs import build_segment_brief
from shows.config import load_show_config
from shows.models import ShowConfig, SourceItem, SourceSnapshot


PROJECT_ROOT = Path(__file__).resolve().parent
PREVIEW_ROOT = PROJECT_ROOT / "runtime" / "studio_preview"


def main() -> None:
    load_dotenv(override=False)
    show_configs = tuple(_load_show_configs())
    PREVIEW_ROOT.mkdir(parents=True, exist_ok=True)
    sample_snapshots = _sample_snapshots()
    preview_manifest = []

    for show_config in show_configs:
        preview_manifest.append(_generate_show_preview(show_config, sample_snapshots))

    render_preview_index(
        preview_manifest=tuple(preview_manifest),
        output_path=PREVIEW_ROOT / "index.html",
    )
    print(PREVIEW_ROOT)


def _load_show_configs() -> list[ShowConfig]:
    configs: list[ShowConfig] = []
    for show_file in sorted((PROJECT_ROOT / "shows").glob("*.toml")):
        env = dict(os.environ)
        env["SHOW_CONFIG_PATH"] = str(show_file)
        env.setdefault("STREAM_URL", "https://example.com")
        configs.append(
            load_show_config(
                project_root=PROJECT_ROOT,
                env=env,
            )
        )
    return configs


def _generate_show_preview(
    show_config: ShowConfig,
    sample_snapshots: tuple[SourceSnapshot, ...],
) -> dict[str, object]:
    show_dir = PREVIEW_ROOT / show_config.show_id
    show_dir.mkdir(parents=True, exist_ok=True)
    queue_items: list[dict[str, object]] = []

    for segment_index, segment_template in enumerate(show_config.segment_plan):
        brief = build_segment_brief(
            show_config=show_config,
            segment_index=segment_index,
            source_snapshots=sample_snapshots,
            default_duration_seconds=segment_template.duration_seconds,
        )
        preview_filename = f"segment-{segment_index + 1:02d}-{_slug(segment_template.label)}.html"
        preview_path = show_dir / preview_filename
        summary = f"{show_config.title}: {segment_template.label}"
        render_segment_page(
            show_config=show_config,
            brief=brief,
            script=(
                f"{segment_template.label} opens the rundown for {show_config.title}. "
                "Second line expands the implication for the audience. "
                "Third line closes the frame and points to what matters next."
            ),
            summary=summary,
            output_path=preview_path,
        )
        queue_items.append(
            {
                "id": f"{show_config.show_id}-{segment_index + 1}",
                "kind": segment_template.kind,
                "label": segment_template.label,
                "duration_seconds": segment_template.duration_seconds,
                "summary": segment_template.instructions,
                "preview_path": f"./{show_config.show_id}/{preview_filename}",
                "status": "live" if segment_index == 0 else "queued",
            }
        )

    intermission_filename = "intermission.html"
    render_intermission_page(
        show_config=show_config,
        duration_seconds=20,
        output_path=show_dir / intermission_filename,
    )
    queue_items.append(
        {
            "id": f"{show_config.show_id}-intermission",
            "kind": "intermission",
            "label": "Music Break",
            "duration_seconds": 20,
            "summary": "Short reset block between prepared segments while the next package is assembled.",
            "preview_path": f"./{show_config.show_id}/{intermission_filename}",
            "status": "queued",
        }
    )
    return {
        "show_id": show_config.show_id,
        "title": show_config.title,
        "tagline": show_config.tagline,
        "description": show_config.description,
        "host_name": show_config.host_name,
        "host_role": show_config.host_role,
        "studio_label": show_config.studio.label,
        "studio_strapline": show_config.studio.strapline,
        "primary_color": show_config.branding.primary_color,
        "accent_color": show_config.branding.accent_color,
        "card_background": show_config.branding.card_background,
        "queue_items": queue_items,
    }


def _sample_snapshots() -> tuple[SourceSnapshot, ...]:
    return (
        SourceSnapshot(
            name="Google News",
            kind="rss",
            prompt_hint="Use this for the latest developments.",
            items=(
                SourceItem(
                    title="Lead story rotates into focus",
                    summary="A fresh source item is summarized here so the preview reflects the card layout and spacing.",
                    url="https://example.com/story-1",
                    published_at="2026-03-29T09:00:00Z",
                ),
                SourceItem(
                    title="Secondary angle adds context",
                    summary="Another source headline appears in the ticker and source digest.",
                    url="https://example.com/story-2",
                    published_at="2026-03-29T09:20:00Z",
                ),
            ),
        ),
        SourceSnapshot(
            name="Operator Notes",
            kind="manual",
            prompt_hint="These are editorial instructions.",
            items=(
                SourceItem(
                    title="Editorial Guardrails",
                    summary="Stay analytical, avoid filler, and explain why the current setup matters.",
                ),
            ),
        ),
    )


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")


if __name__ == "__main__":
    main()
