"""Portable naming rules shared by domain and application modules."""

from __future__ import annotations

import re


def safe_stem(value: str) -> str:
    value = re.sub(r"[\\/:*?\"<>|\n\r\t]+", "", value).strip()
    value = re.sub(r"\s+", "", value)
    return value[:80] or "untitled"
