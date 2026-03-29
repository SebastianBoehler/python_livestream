import tempfile
import unittest
from pathlib import Path

from broadcast.studio_page import render_intermission_page, render_segment_page
from shows.models import (
    SegmentBrief,
    SegmentTemplate,
    ShowBranding,
    ShowConfig,
    SourceItem,
    SourceSnapshot,
    StudioConfig,
)


def _build_show_config() -> ShowConfig:
    return ShowConfig(
        show_id="test",
        title="Test Show",
        tagline="Signals",
        host_name="Host",
        host_role="Anchor",
        description="Description",
        base_prompt="Prompt",
        llm_system_instruction="System",
        tts_voice="Charon",
        branding=ShowBranding(
            primary_color="#000",
            accent_color="#111",
            background_start="#222",
            background_end="#333",
            card_background="#444",
            text_color="#fff",
            muted_text_color="#ccc",
        ),
        studio=StudioConfig(label="Desk", strapline="Signals", ticker_prefix="Ticker"),
        sources=(),
        segment_plan=(),
    )


class StudioPageTests(unittest.TestCase):
    def test_render_segment_page_writes_key_content(self) -> None:
        brief = SegmentBrief(
            segment_template=SegmentTemplate(
                kind="headline",
                label="Top Setup",
                instructions="Lead",
                duration_seconds=120,
            ),
            segment_index=0,
            target_duration_seconds=120,
            source_snapshots=(
                SourceSnapshot(
                    name="Feed",
                    kind="manual",
                    prompt_hint="",
                    items=(SourceItem(title="Fresh headline", summary="Fresh summary"),),
                ),
            ),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "segment.html"
            render_segment_page(
                show_config=_build_show_config(),
                brief=brief,
                script="Fresh headline. Detail one. Detail two.",
                summary="Fresh headline",
                output_path=output_path,
            )
            html = output_path.read_text(encoding="utf-8")

        self.assertIn("Fresh headline", html)
        self.assertIn("Top Setup", html)
        self.assertIn("Source Radar", html)

    def test_render_intermission_page_mentions_music_break(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "intermission.html"
            render_intermission_page(
                show_config=_build_show_config(),
                duration_seconds=30,
                output_path=output_path,
            )
            html = output_path.read_text(encoding="utf-8")

        self.assertIn("Music Break", html)
        self.assertIn("30 seconds", html)


if __name__ == "__main__":
    unittest.main()
