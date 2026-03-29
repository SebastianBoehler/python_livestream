import tempfile
import unittest
from pathlib import Path

from broadcast.memory import BroadcastMemoryStore
from broadcast.models import PreparedSegment


class MemoryStoreTests(unittest.TestCase):
    def test_intermission_segments_are_not_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = BroadcastMemoryStore(temp_dir)
            segment = PreparedSegment(
                segment_id="intermission_1",
                kind="intermission",
                title="Music Break",
                summary="Music-only reset.",
                script="",
                provider_name="music",
                audio_path=Path(temp_dir) / "gap.wav",
                target_duration_seconds=10,
                actual_audio_duration_seconds=10.0,
            )
            store.record_segment(segment)
            session_index = store.session_index_path.read_text(encoding="utf-8")
        self.assertEqual(session_index, "")

    def test_news_segments_are_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = BroadcastMemoryStore(temp_dir)
            segment = PreparedSegment(
                segment_id="segment_1",
                kind="headline",
                title="Top Setup",
                summary="Markets moved on fresh macro headlines.",
                script="Markets moved on fresh macro headlines.",
                provider_name="xai",
                audio_path=Path(temp_dir) / "news.wav",
                target_duration_seconds=60,
                actual_audio_duration_seconds=55.0,
            )
            store.record_segment(segment)
            session_index = store.session_index_path.read_text(encoding="utf-8")
        self.assertIn("segment_1", session_index)
        self.assertIn("xai", session_index)


if __name__ == "__main__":
    unittest.main()
