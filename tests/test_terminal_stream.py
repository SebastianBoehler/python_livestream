import tempfile
import unittest
from pathlib import Path

from broadcast.terminal_stream import (
    _browser_launch_kwargs,
    _minimal_child_environment,
    _validate_final_page_url,
)
from broadcast.terminal_stream_config import (
    TerminalStreamConfig,
    TerminalStreamConfigError,
    TerminalStreamRuntimeError,
    load_terminal_stream_config,
)
from broadcast.terminal_stream_ffmpeg import (
    build_ffmpeg_command,
    redact_ffmpeg_log_line,
    raise_for_ffmpeg_exit,
    safe_ffmpeg_command,
)


class TerminalStreamConfigTests(unittest.TestCase):
    def test_key_file_takes_precedence_over_direct_environment_value(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            key_path = Path(directory) / "youtube-key"
            key_path.write_text("file-key-123456\n", encoding="utf-8")

            config = load_terminal_stream_config(
                {
                    "STREAM_URL": "https://hb-capital.app/livestream",
                    "YOUTUBE_STREAM_KEY_FILE": str(key_path),
                    "YOUTUBE_STREAM_KEY": "environment-key-123456",
                }
            )

        self.assertEqual(
            config.output_url,
            "rtmps://a.rtmps.youtube.com/live2/file-key-123456",
        )
        self.assertNotIn("file-key-123456", repr(config))

    def test_empty_key_file_fails_closed_instead_of_using_environment_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            key_path = Path(directory) / "youtube-key"
            key_path.write_text("\n", encoding="utf-8")

            with self.assertRaisesRegex(TerminalStreamConfigError, "cannot be empty"):
                load_terminal_stream_config(
                    {
                        "STREAM_URL": "https://hb-capital.app/livestream",
                        "YOUTUBE_STREAM_KEY_FILE": str(key_path),
                        "YOUTUBE_STREAM_KEY": "environment-key-123456",
                    }
                )

    def test_loopback_rtmp_override_supports_local_smoke_tests(self) -> None:
        output_url = "rtmp://127.0.0.1:1935/live/test-stream"
        config = load_terminal_stream_config(
            {
                "STREAM_URL": "http://localhost:3000/livestream",
                "STREAM_OUTPUT_URL": output_url,
            }
        )
        self.assertEqual(config.output_url, output_url)

    def test_absolute_flv_output_supports_receiver_free_smoke_tests(self) -> None:
        config = load_terminal_stream_config(
            {
                "STREAM_URL": "http://localhost:3000/livestream",
                "STREAM_OUTPUT_FILE": "/tmp/terminal-smoke.flv",
                "YOUTUBE_STREAM_KEY": "unused-key-123456",
            }
        )

        self.assertEqual(config.output_file, Path("/tmp/terminal-smoke.flv"))
        self.assertEqual(config.output_target, "/tmp/terminal-smoke.flv")

    def test_output_file_is_absolute_flv_and_mutually_exclusive(self) -> None:
        base_environment = {"STREAM_URL": "http://localhost:3000/livestream"}
        for invalid_path in ("terminal.flv", "/tmp/terminal.mp4"):
            with self.subTest(invalid_path=invalid_path):
                with self.assertRaises(TerminalStreamConfigError):
                    load_terminal_stream_config(
                        {**base_environment, "STREAM_OUTPUT_FILE": invalid_path}
                    )
        with self.assertRaisesRegex(TerminalStreamConfigError, "mutually exclusive"):
            load_terminal_stream_config(
                {
                    **base_environment,
                    "STREAM_OUTPUT_FILE": "/tmp/terminal.flv",
                    "STREAM_OUTPUT_URL": "rtmp://localhost:1935/live/test",
                }
            )

    def test_plaintext_remote_urls_are_rejected(self) -> None:
        with self.assertRaises(TerminalStreamConfigError):
            load_terminal_stream_config(
                {
                    "STREAM_URL": "https://hb-capital.app/livestream",
                    "STREAM_OUTPUT_URL": "rtmp://example.com/live/key",
                }
            )
        with self.assertRaises(TerminalStreamConfigError):
            load_terminal_stream_config(
                {
                    "STREAM_URL": "http://hb-capital.app/livestream",
                    "STREAM_OUTPUT_URL": "rtmps://example.com/live/key",
                }
            )

    def test_example_placeholder_key_is_rejected(self) -> None:
        with self.assertRaisesRegex(TerminalStreamConfigError, "placeholder"):
            load_terminal_stream_config(
                {
                    "STREAM_URL": "https://hb-capital.app/livestream",
                    "YOUTUBE_STREAM_KEY": "your-stream-key-here",
                }
            )


class TerminalStreamCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.secret = "youtube-secret-key-123456"
        self.config = TerminalStreamConfig(
            stream_url="https://hb-capital.app/livestream",
            output_url=f"rtmps://a.rtmps.youtube.com/live2/{self.secret}?token=private",
            ffmpeg_path="ffmpeg",
            display=":99",
        )

    def test_command_uses_fixed_high_quality_low_latency_contract(self) -> None:
        command = build_ffmpeg_command(self.config)

        self.assertEqual(command[-1], self.config.output_url)
        self.assertIn("1920x1080", command)
        self.assertEqual(command[command.index("-framerate") + 1], "30")
        self.assertEqual(command[command.index("-profile:v") + 1], "high")
        self.assertEqual(command[command.index("-b:v") + 1], "10000k")
        self.assertEqual(command[command.index("-minrate") + 1], "10000k")
        self.assertEqual(command[command.index("-maxrate") + 1], "10000k")
        self.assertEqual(command[command.index("-g") + 1], "60")
        self.assertEqual(command[command.index("-bf") + 1], "2")
        self.assertEqual(command[command.index("-refs") + 1], "1")
        self.assertEqual(command[command.index("-b:a") + 1], "128k")
        self.assertIn("anullsrc=channel_layout=stereo:sample_rate=48000", command)
        self.assertNotIn("zerolatency", command)
        self.assertEqual(command[command.index("-stats_period") + 1], "5")
        self.assertEqual(command[command.index("-progress") + 1], "pipe:2")

    def test_safe_command_redacts_output_path_and_query(self) -> None:
        safe_command = safe_ffmpeg_command(build_ffmpeg_command(self.config))

        self.assertNotIn(self.secret, safe_command)
        self.assertNotIn("token=private", safe_command)
        self.assertIn("rtmps://a.rtmps.youtube.com/<redacted>", safe_command)

        ffmpeg_error = f"Failed to open {self.config.output_url}"
        safe_error = redact_ffmpeg_log_line(ffmpeg_error, self.config.output_target)
        self.assertNotIn(self.secret, safe_error)
        self.assertNotIn("token=private", safe_error)
        key_only_error = redact_ffmpeg_log_line(
            f"Authentication failed for {self.secret}",
            self.config.output_target,
        )
        self.assertNotIn(self.secret, key_only_error)

    def test_nonzero_ffmpeg_exit_is_surfaced(self) -> None:
        with self.assertRaisesRegex(TerminalStreamRuntimeError, "status 23"):
            raise_for_ffmpeg_exit(23)
        raise_for_ffmpeg_exit(0)


class TerminalStreamBrowserSecurityTests(unittest.TestCase):
    def test_browser_child_environment_excludes_application_secrets(self) -> None:
        environment = _minimal_child_environment(
            ":99",
            {
                "HOME": "/home/stream",
                "PATH": "/usr/bin",
                "LANG": "C.UTF-8",
                "YOUTUBE_STREAM_KEY": "must-not-leak",
                "GEMINI_API_KEY": "must-not-leak",
            },
        )

        self.assertEqual(
            environment,
            {
                "DISPLAY": ":99",
                "HOME": "/home/stream",
                "LANG": "C.UTF-8",
                "PATH": "/usr/bin",
            },
        )
        launch_args = _browser_launch_kwargs(environment)["args"]
        self.assertNotIn("--no-sandbox", launch_args)

    def test_unexpected_login_redirect_is_rejected(self) -> None:
        with self.assertRaisesRegex(TerminalStreamRuntimeError, "unexpected page"):
            _validate_final_page_url(
                "https://hb-capital.app/livestream",
                "https://hb-capital.app/login",
            )

    def test_canonical_www_redirect_is_allowed_for_the_same_https_page(self) -> None:
        _validate_final_page_url(
            "https://hb-capital.app/livestream",
            "https://www.hb-capital.app/livestream",
        )

        with self.assertRaises(TerminalStreamRuntimeError):
            _validate_final_page_url(
                "https://hb-capital.app/livestream",
                "https://www.hb-capital.app/login",
            )


if __name__ == "__main__":
    unittest.main()
