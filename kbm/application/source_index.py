"""Canonical source-index normalization and lookup services."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from kbm.platform.jsonl import read_jsonl_objects
from kbm.platform.paths import system_file


SOURCE_EXTS = {".md", ".markdown", ".txt", ".html", ".htm", ".pdf", ".epub", ".docx"}
SOURCE_TYPE_ALIASES = {
    "公众号": "public_account_article", "public_account": "public_account_article",
    "public_accounts": "public_account_article", "public_account_article": "public_account_article",
    "wechat": "public_account_article", "wechat_article": "public_account_article",
    "电子书": "ebook", "book": "ebook", "ebook": "ebook",
    "article": "article", "web": "web_article", "webpage": "web_article",
    "web_article": "web_article",
}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def split_topics(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip(" #[]") for item in value if str(item).strip(" #[]")]
    text = str(value).replace("，", ",").replace("、", ",").replace(";", ",")
    return [part.strip(" #[]") for part in text.split(",") if part.strip(" #[]")]


def normalize_source_type(value: Any) -> str:
    raw = str(value or "").strip()
    return SOURCE_TYPE_ALIASES.get(raw, raw or "unknown")


def stable_source_id(obj: dict[str, Any]) -> str:
    raw = (
        obj.get("source_sha256") or obj.get("source_path") or obj.get("output_file")
        or obj.get("title") or json.dumps(obj, ensure_ascii=False, sort_keys=True)
    )
    return hashlib.sha256(str(raw).encode("utf-8")).hexdigest()[:16]


def normalize_index_obj(obj: dict[str, Any]) -> dict[str, Any]:
    source_path = obj.get("source_path") or obj.get("source_file") or obj.get("file") or ""
    output_file = obj.get("output_file") or obj.get("refinement_file") or obj.get("note_path") or ""
    title = obj.get("title") or (Path(source_path).stem if source_path else Path(output_file).stem if output_file else "")
    normalized = {
        "schema_version": int(obj.get("schema_version") or 1),
        "source_id": obj.get("source_id") or "",
        "source_path": str(source_path),
        "source_sha256": obj.get("source_sha256") or obj.get("sha256") or "",
        "source_type": normalize_source_type(obj.get("source_type") or obj.get("type")),
        "title": str(title),
        "processed_at": obj.get("processed_at") or obj.get("created_at") or "",
        "output_file": str(output_file),
        "topics": split_topics(obj.get("topics") or obj.get("tags") or obj.get("connected_topics")),
        "status": obj.get("status") or "processed",
        "fact_risk": obj.get("fact_risk") or obj.get("risk") or "unknown",
        "fact_check_required": bool(obj.get("fact_check_required", False)),
    }
    normalized["source_id"] = normalized["source_id"] or stable_source_id(normalized)
    return normalized


def read_processed(cfg: dict[str, Any]) -> tuple[set[str], set[str], int]:
    paths: set[str] = set()
    hashes: set[str] = set()
    rows, _errors = read_jsonl_objects(system_file(cfg, "processed-index.jsonl"))
    for obj in rows:
        normalized = normalize_index_obj(obj)
        if normalized.get("source_path"):
            paths.add(str(Path(normalized["source_path"]).expanduser().resolve()))
        if normalized.get("source_sha256"):
            hashes.add(normalized["source_sha256"])
    return paths, hashes, len(rows)


def iter_sources(cfg: dict[str, Any]) -> list[Path]:
    files: list[Path] = []
    for raw in cfg.get("source_libraries", {}).values():
        if not raw:
            continue
        root = Path(raw)
        if root.exists():
            files.extend(
                path.resolve() for path in root.rglob("*")
                if path.is_file() and path.suffix.lower() in SOURCE_EXTS
            )
    return sorted(files, key=str)
