import os
import unittest
from unittest.mock import patch

from broadcast.capture import browser_launch_kwargs, ffmpeg_video_input_args, load_capture_backend_config


class CaptureConfigTests(unittest.TestCase):
    def test_portrait_orientation_uses_vertical_defaults(self) -> None:
        with patch.dict(os.environ, {"STREAM_ORIENTATION": "portrait"}, clear=False):
            config = load_capture_backend_config()
        self.assertEqual(config.width, 1080)
        self.assertEqual(config.height, 1920)
        self.assertEqual(config.aspect_ratio_label, "9:16")

    def test_virtual_screen_uses_x11grab_input(self) -> None:
        env = {
            "STREAM_CAPTURE_BACKEND": "virtual-screen",
            "STREAM_WIDTH": "1920",
            "STREAM_HEIGHT": "1080",
            "STREAM_FPS": "25",
            "VIRTUAL_DISPLAY": ":99",
            "VIRTUAL_DISPLAY_SCREEN": "0",
        }
        with patch.dict(os.environ, env, clear=False):
            config = load_capture_backend_config()
            input_args = ffmpeg_video_input_args(config)
            launch_args = browser_launch_kwargs(config, browser_env={"DISPLAY": ":99"})

        self.assertIn("x11grab", input_args)
        self.assertIn(":99.0+0,0", input_args)
        self.assertFalse(launch_args["headless"])
        self.assertEqual(launch_args["env"]["DISPLAY"], ":99")


if __name__ == "__main__":
    unittest.main()
