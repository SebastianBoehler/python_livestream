import unittest
from unittest.mock import Mock, patch

from shows.models import ShowBranding, ShowConfig, SegmentTemplate, SourceConfig, StudioConfig
from shows.sources import fetch_show_sources


class SourceAdapterTests(unittest.TestCase):
    def test_manual_and_json_sources_are_loaded(self) -> None:
        show_config = ShowConfig(
            show_id="test",
            title="Test",
            tagline="Tagline",
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
            sources=(
                SourceConfig(kind="manual", name="Editorial", text="Keep it tight."),
                SourceConfig(
                    kind="json",
                    name="API Feed",
                    url="https://example.com/feed.json",
                    items_path="items",
                    title_field="headline",
                    summary_field="detail",
                    url_field="url",
                ),
            ),
            segment_plan=(
                SegmentTemplate(kind="headline", label="Top Setup", instructions="Lead", duration_seconds=120),
            ),
        )
        mocked_response = Mock()
        mocked_response.raise_for_status.return_value = None
        mocked_response.json.return_value = {
            "items": [
                {"headline": "First item", "detail": "Fresh summary", "url": "https://example.com/1"},
            ]
        }

        with patch("shows.sources.requests.get", return_value=mocked_response) as mocked_get:
            snapshots = fetch_show_sources(show_config)

        self.assertEqual(snapshots[0].items[0].summary, "Keep it tight.")
        self.assertEqual(snapshots[1].items[0].title, "First item")
        mocked_get.assert_called_once_with(
            "https://example.com/feed.json",
            headers={"User-Agent": "python-livestream/2.0 (+https://github.com/SebastianBoehler/python_livestream)"},
            timeout=20,
        )


if __name__ == "__main__":
    unittest.main()
