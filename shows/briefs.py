"""Segment briefing helpers."""

from __future__ import annotations

from shows.models import SegmentBrief, ShowConfig, SourceSnapshot


def build_segment_brief(
    *,
    show_config: ShowConfig,
    segment_index: int,
    source_snapshots: tuple[SourceSnapshot, ...],
    default_duration_seconds: int | None = None,
) -> SegmentBrief:
    segment_template = show_config.segment_plan[segment_index % len(show_config.segment_plan)]
    target_duration_seconds = default_duration_seconds or segment_template.duration_seconds
    return SegmentBrief(
        segment_template=segment_template,
        segment_index=segment_index,
        target_duration_seconds=target_duration_seconds,
        source_snapshots=source_snapshots,
    )


__all__ = ["build_segment_brief"]
