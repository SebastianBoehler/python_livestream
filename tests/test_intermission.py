import shutil
import tempfile
import unittest

from broadcast.intermission import prepare_intermission_segment


class IntermissionTests(unittest.TestCase):
    def test_prepare_intermission_segment_creates_audio_file(self) -> None:
        if shutil.which("ffmpeg") is None:
            self.skipTest("ffmpeg not available")

        with tempfile.TemporaryDirectory() as temp_dir:
            segment = prepare_intermission_segment(
                duration_seconds=2,
                tts_dir=temp_dir,
                ffmpeg_path="ffmpeg",
            )
            self.assertEqual(segment.kind, "intermission")
            self.assertTrue(segment.audio_path.exists())
            self.assertEqual(segment.target_duration_seconds, 2)


if __name__ == "__main__":
    unittest.main()
