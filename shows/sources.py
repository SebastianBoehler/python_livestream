"""Source adapters for reusable livestream shows."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from typing import Any

import requests

from shows.models import ShowConfig, SourceConfig, SourceItem, SourceSnapshot


USER_AGENT = "python-livestream/2.0 (+https://github.com/SebastianBoehler/python_livestream)"


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._suppress_depth = 0
        self._text_chunks: list[str] = []
        self.title = ""
        self._inside_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._suppress_depth += 1
        elif tag == "title":
            self._inside_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._suppress_depth > 0:
            self._suppress_depth -= 1
        elif tag == "title":
            self._inside_title = False

    def handle_data(self, data: str) -> None:
        if self._suppress_depth > 0:
            return
        cleaned = " ".join(data.split())
        if not cleaned:
            return
        if self._inside_title and not self.title:
            self.title = cleaned
            return
        self._text_chunks.append(cleaned)

    @property
    def text(self) -> str:
        return " ".join(self._text_chunks)


def fetch_show_sources(show_config: ShowConfig, *, timeout_seconds: int = 20) -> tuple[SourceSnapshot, ...]:
    snapshots: list[SourceSnapshot] = []
    for source in show_config.sources:
        snapshots.append(_fetch_source(source, timeout_seconds=timeout_seconds))
    return tuple(snapshots)


def _fetch_source(source: SourceConfig, *, timeout_seconds: int) -> SourceSnapshot:
    normalized_kind = source.kind.strip().lower()
    if normalized_kind == "rss":
        return _fetch_rss_source(source, timeout_seconds=timeout_seconds)
    if normalized_kind == "webpage":
        return _fetch_webpage_source(source, timeout_seconds=timeout_seconds)
    if normalized_kind == "json":
        return _fetch_json_source(source, timeout_seconds=timeout_seconds)
    if normalized_kind == "manual":
        return _fetch_manual_source(source)
    raise ValueError(f"Unsupported source type: {source.kind}")


def _fetch_rss_source(source: SourceConfig, *, timeout_seconds: int) -> SourceSnapshot:
    response = requests.get(
        source.url,
        headers={"User-Agent": USER_AGENT},
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    root = ET.fromstring(response.text)
    items = root.findall(".//item")
    if not items:
        items = root.findall(".//{http://www.w3.org/2005/Atom}entry")

    parsed_items: list[SourceItem] = []
    for item in items[: source.limit]:
        title = _find_xml_text(item, "title")
        summary = _find_xml_text(item, "description") or _find_xml_text(item, "summary")
        link = _find_xml_text(item, "link")
        if not link:
            link = item.findtext("{http://www.w3.org/2005/Atom}link")
            if not link:
                atom_link = item.find("{http://www.w3.org/2005/Atom}link")
                if atom_link is not None:
                    link = atom_link.attrib.get("href", "")
        published_at = (
            _find_xml_text(item, "pubDate")
            or _find_xml_text(item, "published")
            or _find_xml_text(item, "updated")
        )
        parsed_items.append(
            SourceItem(
                title=_compact_text(title, max_chars=180),
                summary=_compact_text(summary, max_chars=source.max_chars),
                url=link.strip(),
                published_at=published_at.strip(),
            )
        )
    return SourceSnapshot(name=source.name, kind=source.kind, prompt_hint=source.prompt_hint, items=tuple(parsed_items))


def _fetch_webpage_source(source: SourceConfig, *, timeout_seconds: int) -> SourceSnapshot:
    response = requests.get(
        source.url,
        headers={"User-Agent": USER_AGENT},
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    parser = _VisibleTextParser()
    parser.feed(response.text)
    body_text = _compact_text(parser.text, max_chars=source.max_chars)
    title = parser.title or source.name
    item = SourceItem(
        title=_compact_text(title, max_chars=180),
        summary=body_text,
        url=source.url,
    )
    return SourceSnapshot(name=source.name, kind=source.kind, prompt_hint=source.prompt_hint, items=(item,))


def _fetch_json_source(source: SourceConfig, *, timeout_seconds: int) -> SourceSnapshot:
    response = requests.get(
        source.url,
        headers={"User-Agent": USER_AGENT},
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    payload = response.json()
    items = _resolve_items_path(payload, source.items_path)
    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list):
        raise ValueError(f"JSON source {source.name} did not resolve to a list of items")

    parsed_items: list[SourceItem] = []
    for item in items[: source.limit]:
        if not isinstance(item, dict):
            continue
        title = str(item.get(source.title_field, "")).strip()
        summary = str(item.get(source.summary_field, "")).strip()
        url = str(item.get(source.url_field, "")).strip()
        parsed_items.append(
            SourceItem(
                title=_compact_text(title, max_chars=180),
                summary=_compact_text(summary, max_chars=source.max_chars),
                url=url,
            )
        )
    return SourceSnapshot(name=source.name, kind=source.kind, prompt_hint=source.prompt_hint, items=tuple(parsed_items))


def _fetch_manual_source(source: SourceConfig) -> SourceSnapshot:
    item = SourceItem(
        title=source.name,
        summary=_compact_text(source.text, max_chars=source.max_chars),
    )
    return SourceSnapshot(name=source.name, kind=source.kind, prompt_hint=source.prompt_hint, items=(item,))


def _find_xml_text(element: ET.Element, tag_name: str) -> str:
    match = element.find(tag_name)
    if match is not None and match.text:
        return match.text.strip()
    for child in element:
        if child.tag.endswith(tag_name) and child.text:
            return child.text.strip()
    return ""


def _resolve_items_path(payload: Any, items_path: str) -> Any:
    current = payload
    if not items_path:
        return current
    for part in items_path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def _compact_text(value: str, *, max_chars: int) -> str:
    normalized = re.sub(r"\s+", " ", value or "").strip()
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 1].rstrip() + "…"


__all__ = ["fetch_show_sources"]
