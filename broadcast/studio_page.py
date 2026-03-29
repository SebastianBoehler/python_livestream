"""Local studio page rendering for browser capture."""

from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path
from typing import Any

from shows.models import SegmentBrief, ShowConfig, SourceSnapshot


TEMPLATE_PATH = Path(__file__).parent / "templates" / "studio.html"
STYLE_TEMPLATE_PATH = Path(__file__).parent / "templates" / "studio.css"
PREVIEW_INDEX_TEMPLATE_PATH = Path(__file__).parent / "templates" / "preview_index.html"


def render_segment_page(
    *,
    show_config: ShowConfig,
    brief: SegmentBrief,
    script: str,
    summary: str,
    output_path: str | Path,
) -> Path:
    headline = summary or brief.segment_template.label
    scene_mode = brief.segment_template.scene_mode or show_config.studio.layout_mode
    return _write_page(
        show_config=show_config,
        segment_kind=brief.segment_template.kind,
        segment_label=brief.segment_template.label,
        headline=headline,
        key_points=_script_sentences(script)[:3],
        source_cards=_render_source_cards(brief.source_snapshots),
        ticker_items=brief.ticker_items or (headline,),
        iframe_markup=_render_iframe(show_config.studio.iframe_url, scene_mode),
        scene_mode=scene_mode,
        output_path=output_path,
    )


def render_intermission_page(
    *,
    show_config: ShowConfig,
    duration_seconds: int,
    output_path: str | Path,
) -> Path:
    return _write_page(
        show_config=show_config,
        segment_kind="intermission",
        segment_label="Music Break",
        headline=f"Resetting the rundown for the next segment in about {duration_seconds} seconds.",
        key_points=(
            "Fresh sources are being collected for the next pass.",
            "The stream stays live while the next package is prepared.",
            "Use this window to refresh titles, thumbnails, or pinned links if needed.",
        ),
        source_cards="<div class='source-card compact'>Intermission visuals active.</div>",
        ticker_items=("Music break", "Collecting fresh sources", "Preparing next segment"),
        iframe_markup="",
        scene_mode="transition",
        output_path=output_path,
    )


def render_preview_index(
    *,
    preview_manifest: tuple[dict[str, Any], ...],
    output_path: str | Path,
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    template = PREVIEW_INDEX_TEMPLATE_PATH.read_text(encoding="utf-8")
    html = template.replace("{{PREVIEW_DATA_JSON}}", escape(json.dumps(preview_manifest), quote=False))
    output.write_text(html, encoding="utf-8")
    return output


def _write_page(
    *,
    show_config: ShowConfig,
    segment_kind: str,
    segment_label: str,
    headline: str,
    key_points: tuple[str, ...],
    source_cards: str,
    ticker_items: tuple[str, ...],
    iframe_markup: str,
    scene_mode: str,
    output_path: str | Path,
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    style_block = STYLE_TEMPLATE_PATH.read_text(encoding="utf-8")
    ticker_track = _ticker_track(ticker_items)
    segment_kind_class = _slug(segment_kind) if segment_kind else "segment"
    layout_mode = _normalize_layout_mode(scene_mode)
    replacements = {
        "{{PAGE_TITLE}}": escape(f"{show_config.title} Studio"),
        "{{STYLE_BLOCK}}": style_block,
        "{{BODY_CLASS}}": f"layout-{layout_mode} segment-{segment_kind_class}",
        "{{PRIMARY_COLOR}}": show_config.branding.primary_color,
        "{{ACCENT_COLOR}}": show_config.branding.accent_color,
        "{{BACKGROUND_START}}": show_config.branding.background_start,
        "{{BACKGROUND_END}}": show_config.branding.background_end,
        "{{CARD_BACKGROUND}}": show_config.branding.card_background,
        "{{TEXT_COLOR}}": show_config.branding.text_color,
        "{{MUTED_TEXT_COLOR}}": show_config.branding.muted_text_color,
        "{{SHOW_LABEL}}": escape(show_config.studio.label),
        "{{SHOW_TITLE}}": escape(show_config.title),
        "{{SHOW_STRAPLINE}}": escape(show_config.studio.strapline or show_config.tagline),
        "{{HOST_NAME}}": escape(show_config.host_name),
        "{{HOST_ROLE}}": escape(show_config.host_role),
        "{{HOST_INITIALS}}": escape(_initials(show_config.host_name)),
        "{{SEGMENT_LABEL}}": escape(segment_label),
        "{{HEADLINE}}": escape(headline),
        "{{POINTS_MARKUP}}": "".join(f"<li>{escape(point)}</li>" for point in key_points if point),
        "{{SOURCE_CARDS}}": source_cards,
        "{{TICKER_PREFIX}}": escape(show_config.studio.ticker_prefix),
        "{{TICKER_TRACK}}": ticker_track,
        "{{IFRAME_MARKUP}}": iframe_markup,
    }
    html = template
    for token, value in replacements.items():
        html = html.replace(token, value)
    output.write_text(html, encoding="utf-8")
    return output


def _ticker_track(ticker_items: tuple[str, ...]) -> str:
    ticker_markup = " <span class='ticker-divider'>//</span> ".join(
        escape(item) for item in ticker_items if item
    )
    return f"{ticker_markup} <span class='ticker-divider'>//</span> {ticker_markup}"


def _render_source_cards(source_snapshots: tuple[SourceSnapshot, ...]) -> str:
    parts: list[str] = []
    for snapshot in source_snapshots[:4]:
        if not snapshot.items:
            continue
        lead = snapshot.items[0]
        parts.extend(
            [
                "<div class='source-card'>",
                f"<div class='name'>{escape(snapshot.name)}</div>",
                f"<div class='item-title'>{escape(lead.title or snapshot.name)}</div>",
                f"<div class='item-summary'>{escape(lead.summary or 'Fresh items collected for this segment.')}</div>",
                "</div>",
            ]
        )
    if not parts:
        return "<div class='source-card compact'>No source cards available.</div>"
    return "\n".join(parts)


def _render_iframe(iframe_url: str, layout_mode: str) -> str:
    if not iframe_url or _normalize_layout_mode(layout_mode) == "transition":
        return ""
    escaped_url = escape(iframe_url, quote=True)
    return (
        "<div class='iframe-shell'>"
        f"<iframe src='{escaped_url}' title='Studio reference panel'></iframe>"
        "</div>"
    )


def _normalize_layout_mode(value: str) -> str:
    normalized = (value or "split").strip().lower().replace("_", "-").replace(" ", "-")
    if normalized in {"overlay", "split", "clean-feed", "transition"}:
        return normalized
    return "split"


def _initials(value: str) -> str:
    parts = [part[0].upper() for part in value.split() if part]
    return "".join(parts[:2]) or "HB"


def _script_sentences(script: str) -> tuple[str, ...]:
    cleaned = " ".join(script.split())
    if not cleaned:
        return ()
    for delimiter in (". ", "! ", "? "):
        if delimiter not in cleaned:
            continue
        fragments = [fragment.strip() for fragment in cleaned.split(delimiter) if fragment.strip()]
        return tuple(
            fragment if fragment.endswith((".", "!", "?")) else f"{fragment}."
            for fragment in fragments
        )
    return (cleaned,)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")


__all__ = ["render_intermission_page", "render_preview_index", "render_segment_page"]
