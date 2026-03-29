import tempfile
import unittest
from pathlib import Path

from shows.config import load_show_config


class ShowConfigTests(unittest.TestCase):
    def test_load_show_config_expands_environment_variables(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            shows_dir = project_root / "shows"
            shows_dir.mkdir()
            config_path = shows_dir / "test_show.toml"
            config_path.write_text(
                """
show_id = "test_show"
title = "Test Show"
tagline = "Tagline"
host_name = "Host"
host_role = "Anchor"
description = "Description"
base_prompt = "Prompt"
llm_system_instruction = "System"
tts_voice = "Charon"

[branding]
primary_color = "#000000"
accent_color = "#111111"
background_start = "#222222"
background_end = "#333333"
card_background = "#444444"
text_color = "#ffffff"
muted_text_color = "#cccccc"

[studio]
label = "Desk"
strapline = "Signals"
ticker_prefix = "Ticker"
iframe_url = "${STREAM_URL}"

[[sources]]
kind = "manual"
name = "Guide"
text = "${EDITORIAL_NOTE}"

[[segments]]
kind = "headline"
label = "Top Setup"
instructions = "Lead"
duration_seconds = 120
scene_mode = "transition"
""".strip(),
                encoding="utf-8",
            )
            env = {
                "SHOW_CONFIG_PATH": str(config_path),
                "STREAM_URL": "https://example.com",
                "EDITORIAL_NOTE": "Stay concrete.",
            }
            config = load_show_config(project_root=project_root, env=env)

        self.assertEqual(config.studio.iframe_url, "https://example.com")
        self.assertEqual(config.sources[0].text, "Stay concrete.")
        self.assertEqual(config.segment_plan[0].duration_seconds, 120)
        self.assertEqual(config.segment_plan[0].scene_mode, "transition")


if __name__ == "__main__":
    unittest.main()
