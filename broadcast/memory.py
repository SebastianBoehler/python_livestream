"""Simple persistent memory for prior broadcast coverage."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from hashlib import sha1
from pathlib import Path
from typing import Any

from broadcast.models import PreparedSegment


class BroadcastMemoryStore:
    """Persists recent coverage for prompt grounding and operator review."""

    def __init__(self, root_dir: str | Path) -> None:
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.session_index_path = self.root_dir / "session_index.jsonl"
        self.topic_state_path = self.root_dir / "topic_state.json"
        self.rolling_context_path = self.root_dir / "rolling_context.md"
        self._ensure_files()

    def build_prompt_context(self, max_recent_segments: int = 5) -> str:
        entries = self._load_recent_entries(max_recent_segments)
        topic_state = self._load_topic_state()
        if not entries:
            return ""

        repeated_topics = sorted(
            topic_state.values(),
            key=lambda item: (item["times_mentioned"], item["last_seen"]),
            reverse=True,
        )[:3]
        context_lines = [
            "Recent coverage to avoid repeating verbatim unless there is a material update:",
        ]
        for entry in entries:
            context_lines.append(
                f"- {entry['aired_at']}: {entry['summary']} (provider={entry['provider_name']})"
            )
        if repeated_topics:
            context_lines.append("")
            context_lines.append("Recurring topics to revisit only with new substance:")
            for topic in repeated_topics:
                context_lines.append(
                    f"- {topic['summary']} (mentions={topic['times_mentioned']}, last_seen={topic['last_seen']})"
                )
        return "\n".join(context_lines)

    def record_segment(self, segment: PreparedSegment) -> None:
        if segment.kind != "news":
            return
        aired_at = datetime.now(UTC).isoformat()
        summary = self._summarize_script(segment.script)
        entry = {
            "segment_id": segment.segment_id,
            "aired_at": aired_at,
            "provider_name": segment.provider_name,
            "summary": summary,
            "script_hash": sha1(segment.script.encode("utf-8")).hexdigest(),
            "audio_path": str(segment.audio_path),
            "target_duration_seconds": segment.target_duration_seconds,
            "actual_audio_duration_seconds": round(segment.actual_audio_duration_seconds, 2),
        }
        with self.session_index_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=True) + "\n")
        self._update_topic_state(entry)
        self._write_rolling_context()

    def _ensure_files(self) -> None:
        if not self.session_index_path.exists():
            self.session_index_path.write_text("", encoding="utf-8")
        if not self.topic_state_path.exists():
            self.topic_state_path.write_text("{}", encoding="utf-8")
        if not self.rolling_context_path.exists():
            self.rolling_context_path.write_text(
                "# Rolling Coverage Context\n\nNo segments have been aired yet.\n",
                encoding="utf-8",
            )

    def _load_recent_entries(self, max_recent_segments: int) -> list[dict[str, Any]]:
        lines = self.session_index_path.read_text(encoding="utf-8").splitlines()
        entries = [json.loads(line) for line in lines if line.strip()]
        return entries[-max_recent_segments:]

    def _load_topic_state(self) -> dict[str, dict[str, Any]]:
        return json.loads(self.topic_state_path.read_text(encoding="utf-8"))

    def _update_topic_state(self, entry: dict[str, Any]) -> None:
        topic_state = self._load_topic_state()
        topic_id = sha1(entry["summary"].lower().encode("utf-8")).hexdigest()[:12]
        current = topic_state.get(
            topic_id,
            {
                "topic_id": topic_id,
                "summary": entry["summary"],
                "times_mentioned": 0,
                "first_seen": entry["aired_at"],
            },
        )
        current["summary"] = entry["summary"]
        current["times_mentioned"] += 1
        current["last_seen"] = entry["aired_at"]
        topic_state[topic_id] = current
        self.topic_state_path.write_text(json.dumps(topic_state, indent=2), encoding="utf-8")

    def _write_rolling_context(self) -> None:
        entries = self._load_recent_entries(8)
        topic_state = self._load_topic_state()
        lines = [
            "# Rolling Coverage Context",
            "",
            f"Last updated: {datetime.now(UTC).isoformat()}",
            "",
            "## Recently aired segments",
        ]
        if entries:
            for entry in entries:
                lines.append(
                    f"- {entry['aired_at']} [{entry['provider_name']}] {entry['summary']}"
                )
        else:
            lines.append("- No segments have been aired yet.")

        lines.extend(["", "## Topic memory"])
        topics = sorted(
            topic_state.values(),
            key=lambda item: (item["times_mentioned"], item["last_seen"]),
            reverse=True,
        )
        if topics:
            for topic in topics[:8]:
                lines.append(
                    f"- {topic['summary']} (mentions={topic['times_mentioned']}, last_seen={topic['last_seen']})"
                )
        else:
            lines.append("- No recurring topics tracked yet.")
        self.rolling_context_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    @staticmethod
    def _summarize_script(script: str) -> str:
        clean = " ".join(script.split())
        if not clean:
            return "Empty segment"
        for delimiter in (". ", "! ", "? "):
            if delimiter in clean:
                return clean.split(delimiter, 1)[0][:220].strip()
        return clean[:220].strip()
