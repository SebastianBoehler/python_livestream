import os
import unittest
from unittest.mock import patch

from broadcast.encoding import ffmpeg_video_encoder_args


class EncodingTests(unittest.TestCase):
    def test_virtual_screen_defaults_to_libx264(self) -> None:
        with patch.dict(os.environ, {"STREAM_CAPTURE_BACKEND": "virtual-screen"}, clear=False):
            args = ffmpeg_video_encoder_args()
        self.assertEqual(args[:2], ["-c:v", "libx264"])

    def test_explicit_encoder_override_is_respected(self) -> None:
        with patch.dict(os.environ, {"STREAM_VIDEO_ENCODER": "libx264"}, clear=False):
            args = ffmpeg_video_encoder_args()
        self.assertEqual(args[:2], ["-c:v", "libx264"])
        self.assertIn("zerolatency", args)


if __name__ == "__main__":
    unittest.main()
