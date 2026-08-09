"""Shared date parsing for freshness and lifecycle policies."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any


def parse_date(value: Any) -> date | None:
    text = str(value or "").strip().strip('"').strip("'")
    if not re.match(r"^\d{4}-\d{2}-\d{2}", text):
        return None
    try:
        return datetime.strptime(text[:10], "%Y-%m-%d").date()
    except ValueError:
        return None
