"""Show configuration loading."""

from __future__ import annotations

import os
from pathlib import Path
from string import Template
from typing import Any

import tomllib

from shows.models import SegmentTemplate, ShowBranding, ShowConfig, SourceConfig, StudioConfig


DEFAULT_SHOW_ID = "hb_capital"


def load_show_config(*, project_root: str | Path, env: dict[str, str] | None = None) -> ShowConfig:
    resolved_env = env or dict(os.environ)
    root = Path(project_root)
    config_path = _resolve_show_config_path(root, resolved_env)
    data = _load_toml_file(config_path)
    expanded = _expand_env_templates(data, resolved_env)
    return _build_show_config(expanded, config_path)


def _resolve_show_config_path(project_root: Path, env: dict[str, str]) -> Path:
    configured_path = env.get("SHOW_CONFIG_PATH")
    if configured_path:
        return Path(configured_path).expanduser().resolve()
    show_id = env.get("SHOW_ID", DEFAULT_SHOW_ID).strip()
    return (project_root / "shows" / f"{show_id}.toml").resolve()


def _load_toml_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Show config not found: {path}")
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _expand_env_templates(value: Any, env: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {key: _expand_env_templates(item, env) for key, item in value.items()}
    if isinstance(value, list):
        return [_expand_env_templates(item, env) for item in value]
    if isinstance(value, str):
        try:
            return Template(value).substitute(env)
        except KeyError as error:
            missing_key = error.args[0]
            raise ValueError(f"Missing environment variable referenced by show config: {missing_key}") from error
    return value


def _build_show_config(data: dict[str, Any], config_path: Path) -> ShowConfig:
    try:
        branding = ShowBranding(**data["branding"])
        studio = StudioConfig(**data["studio"])
        sources = tuple(SourceConfig(**item) for item in data["sources"])
        segment_plan = tuple(SegmentTemplate(**item) for item in data["segments"])
    except KeyError as error:
        raise ValueError(f"Missing required show config section in {config_path}: {error}") from error

    if not sources:
        raise ValueError(f"Show config {config_path} does not define any sources")
    if not segment_plan:
        raise ValueError(f"Show config {config_path} does not define any segments")

    required_fields = [
        "show_id",
        "title",
        "tagline",
        "host_name",
        "host_role",
        "description",
        "base_prompt",
        "llm_system_instruction",
        "tts_voice",
    ]
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        joined = ", ".join(missing_fields)
        raise ValueError(f"Show config {config_path} is missing fields: {joined}")

    return ShowConfig(
        show_id=data["show_id"],
        title=data["title"],
        tagline=data["tagline"],
        host_name=data["host_name"],
        host_role=data["host_role"],
        description=data["description"],
        base_prompt=data["base_prompt"],
        llm_system_instruction=data["llm_system_instruction"],
        tts_voice=data["tts_voice"],
        branding=branding,
        studio=studio,
        sources=sources,
        segment_plan=segment_plan,
    )


__all__ = ["DEFAULT_SHOW_ID", "load_show_config"]
