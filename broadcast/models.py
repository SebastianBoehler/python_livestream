from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class PreparedSegment:
    """Audio-backed segment ready for playout."""

    segment_id: str
    kind: str
    script: str
    provider_name: str
    audio_path: Path
    target_duration_seconds: int
    actual_audio_duration_seconds: float
