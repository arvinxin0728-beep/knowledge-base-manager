"""Portable naming rules shared by domain and application modules."""

from __future__ import annotations

import re


def safe_stem(value: str) -> str:
    value = re.sub(r"[\\/:*?\"<>|\n\r\t]+", "", value).strip()
    value = re.sub(r"\s+", "", value)
    return value[:80] or "untitled"


def path_slug(value: str) -> str:
    """Filesystem-safe namespace for runtime/state directories.

    ASCII-ish input keeps the historical lowercase-kebab form so existing
    researcher directories are unaffected. Non-ASCII names (for example a
    Chinese researcher name) are preserved rather than collapsed to a generic
    placeholder, which would otherwise silently orphan that researcher's
    existing runtime state and risk colliding with another researcher's.
    """
    stripped = value.strip()
    if re.fullmatch(r"[A-Za-z0-9 _.-]*", stripped):
        normalized = re.sub(r"[^a-z0-9]+", "-", stripped.lower()).strip("-")
        return normalized or "default-researcher"
    normalized = re.sub(r"[\\/:*?\"<>|\s]+", "-", stripped).strip("-")
    return normalized or "default-researcher"
