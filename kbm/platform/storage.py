"""Researcher-scoped persistence primitives."""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from kbm.platform.paths import system_file


def backup_file(path: Path, max_backups: int = 5) -> Path | None:
    if not path.exists():
        return None
    backups_dir = path.parent / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backups_dir / f"{path.name}.{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    shutil.copy2(path, backup_path)
    existing = sorted(backups_dir.glob(f"{path.name}.*"))
    while len(existing) > max_backups:
        existing.pop(0).unlink(missing_ok=True)
    return backup_path


def append_operation_log(cfg: dict[str, Any], command: str, summary: str, counts: dict[str, Any] | None = None, error: str | None = None) -> None:
    log = system_file(cfg, "run-log.jsonl")
    record: dict[str, Any] = {"timestamp": datetime.now().astimezone().isoformat(timespec="seconds"), "command": command, "summary": summary, "counts": counts or {}}
    if error:
        record["error"] = error
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as exc:
        print(f"Warning: failed to write operation log: {exc}", file=sys.stderr)
