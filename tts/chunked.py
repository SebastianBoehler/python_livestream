"""Chunked TTS generation for lower end-to-end latency."""

from __future__ import annotations

import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def synthesize_script_to_file(
    script: str,
    output_file: str,
    tts_generator,
    ffmpeg_path: str = "ffmpeg",
    parallelism: int = 3,
    max_chars_per_chunk: int = 450,
) -> str:
    chunks = _split_script(script, max_chars_per_chunk)
    if len(chunks) == 1 or parallelism <= 1:
        return tts_generator([script], output_file)

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="tts_chunks_", dir=output_path.parent) as temp_dir:
        temp_path = Path(temp_dir)
        chunk_paths = [temp_path / f"chunk_{index:03d}.wav" for index in range(len(chunks))]
        with ThreadPoolExecutor(max_workers=min(parallelism, len(chunks))) as executor:
            futures = [
                executor.submit(tts_generator, [chunk], str(chunk_path))
                for chunk, chunk_path in zip(chunks, chunk_paths, strict=True)
            ]
            for future in futures:
                future.result()
        concat_file = temp_path / "concat.txt"
        concat_lines = [f"file '{chunk_path.as_posix()}'" for chunk_path in chunk_paths]
        concat_file.write_text("\n".join(concat_lines) + "\n", encoding="utf-8")
        command = [
            ffmpeg_path,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c",
            "copy",
            str(output_path),
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg concat failed: {result.stderr}")
    return str(output_path)


def _split_script(script: str, max_chars_per_chunk: int) -> list[str]:
    paragraphs = [part.strip() for part in script.split("\n") if part.strip()]
    units = paragraphs or [script.strip()]
    chunks: list[str] = []
    current = ""
    for unit in units:
        if len(unit) > max_chars_per_chunk:
            sentences = [sentence.strip() for sentence in unit.split(". ") if sentence.strip()]
            for sentence in sentences:
                rebuilt = sentence if sentence.endswith((".", "!", "?")) else f"{sentence}."
                chunks.extend(_split_script(rebuilt, max_chars_per_chunk))
            continue
        candidate = unit if not current else f"{current}\n\n{unit}"
        if current and len(candidate) > max_chars_per_chunk:
            chunks.append(current)
            current = unit
        else:
            current = candidate
    if current:
        chunks.append(current)
    return [chunk for chunk in chunks if chunk]

