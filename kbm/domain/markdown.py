"""Shared Markdown parsing primitives with no workspace or CLI dependencies."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def collect_markdown_files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted((item for item in path.rglob("*.md") if item.is_file()), key=str)


def extract_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []
    for line in text.split("\n"):
        match = re.match(r"^##\s+(.+)$", line)
        if match:
            if current_key and current_lines:
                sections[current_key] = "\n".join(current_lines).strip()
            current_key = match.group(1).strip().rstrip(":")
            current_lines = []
        elif current_key:
            current_lines.append(line)
    if current_key and current_lines:
        sections[current_key] = "\n".join(current_lines).strip()
    return sections


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    raw = text[4:end].strip()
    body = text[end + len("\n---"):].lstrip("\n")
    meta: dict[str, Any] = {}
    current: str | None = None
    for line in raw.splitlines():
        if not line.strip():
            continue
        if re.match(r"^[A-Za-z0-9_\-]+:\s*", line):
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            current = key
            if value == "":
                meta[key] = []
            elif value.lower() in {"true", "false"}:
                meta[key] = value.lower() == "true"
            else:
                meta[key] = value.strip('"')
        elif line.lstrip().startswith("- ") and current:
            if not isinstance(meta.get(current), list):
                meta[current] = []
            meta[current].append(line.strip()[2:].strip('"'))
    return meta, body


def markdown_title(path: Path, text: str) -> str:
    _meta, body = split_frontmatter(text)
    match = re.search(r"(?m)^#\s+(.+)$", body)
    return match.group(1).strip() if match else path.stem


def clean_link_target(value: str) -> str:
    return str(value).split("|", 1)[0].split("#", 1)[0].strip()


def wikilink_targets(text: str) -> list[str]:
    return [clean_link_target(value) for value in re.findall(r"\[\[([^\]]+)\]\]", text)]
