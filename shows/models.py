"""Show configuration models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ShowBranding:
    primary_color: str
    accent_color: str
    background_start: str
    background_end: str
    card_background: str
    text_color: str
    muted_text_color: str


@dataclass(slots=True)
class StudioConfig:
    label: str
    strapline: str
    ticker_prefix: str
    iframe_url: str = ""


@dataclass(slots=True)
class SourceConfig:
    kind: str
    name: str
    url: str = ""
    text: str = ""
    limit: int = 5
    max_chars: int = 1400
    items_path: str = ""
    title_field: str = "title"
    summary_field: str = "summary"
    url_field: str = "url"
    prompt_hint: str = ""


@dataclass(slots=True)
class SegmentTemplate:
    kind: str
    label: str
    instructions: str
    duration_seconds: int


@dataclass(slots=True)
class ShowConfig:
    show_id: str
    title: str
    tagline: str
    host_name: str
    host_role: str
    description: str
    base_prompt: str
    llm_system_instruction: str
    tts_voice: str
    branding: ShowBranding
    studio: StudioConfig
    sources: tuple[SourceConfig, ...]
    segment_plan: tuple[SegmentTemplate, ...]


@dataclass(slots=True)
class SourceItem:
    title: str
    summary: str
    url: str = ""
    published_at: str = ""


@dataclass(slots=True)
class SourceSnapshot:
    name: str
    kind: str
    prompt_hint: str
    items: tuple[SourceItem, ...] = field(default_factory=tuple)


@dataclass(slots=True)
class SegmentBrief:
    segment_template: SegmentTemplate
    segment_index: int
    target_duration_seconds: int
    source_snapshots: tuple[SourceSnapshot, ...]

    @property
    def ticker_items(self) -> tuple[str, ...]:
        items: list[str] = []
        for snapshot in self.source_snapshots:
            for source_item in snapshot.items:
                if source_item.title:
                    items.append(source_item.title)
        return tuple(items[:8])
