import os
import unittest
from unittest.mock import MagicMock, patch

from broadcast.capture import browser_launch_kwargs, ffmpeg_video_input_args, load_capture_backend_config
from broadcast.virtual_display import managed_virtual_display


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

    def test_virtual_display_accepts_a_secret_free_process_environment(self) -> None:
        with patch.dict(
            os.environ,
            {"STREAM_CAPTURE_BACKEND": "virtual-screen"},
            clear=False,
        ):
            config = load_capture_backend_config()
        process = MagicMock()
        process.poll.return_value = 0
        child_environment = {"DISPLAY": ":99", "PATH": "/usr/bin"}

        with (
            patch("broadcast.virtual_display.sys.platform", "linux"),
            patch("broadcast.virtual_display.Path.exists", return_value=False),
            patch("broadcast.virtual_display.shutil.which", return_value="/usr/bin/Xvfb"),
            patch("broadcast.virtual_display.subprocess.Popen", return_value=process) as popen,
            patch("broadcast.virtual_display._wait_until_ready"),
        ):
            with managed_virtual_display(
                config,
                process_environment=child_environment,
            ):
                pass

        self.assertEqual(popen.call_args.kwargs["env"], child_environment)


if __name__ == "__main__":
    unittest.main()
