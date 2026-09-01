"""Researcher-scoped knowledge-base and runtime paths."""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path
from typing import Any

from kbm.domain.naming import path_slug


SYSTEM_ACTIVE_FILES = {'processed-index.jsonl', 'active-run-state.json', 'run-log.jsonl', 'promotion-decision.jsonl', 'verification-queue.jsonl', 'verification-results.jsonl', 'output-review-results.jsonl', 'evidence-fill-ledger.jsonl', 'kb-config.json', 'obsidian-taxonomy.json', 'rules.md', 'topics.md'}
SYSTEM_REPORT_FILES = {'topic-clusters.md', 'promotion-review.md', 'asset-output-candidates.md', 'quality-gate.md', 'gate-10.md', 'verification-status.md', 'output-quality-review.md', 'output-review-status.md', 'portability-audit.md', 'topic-page-audit.md', 'relation-audit.md', 'asset-relation-audit.md', 'lifecycle-audit.md', 'knowledge-health.md', 'source-quality-audit.md', 'evidence-gap-registry.md', 'editorial-quality-review.md', 'evidence-intake-audit.md', 'source-capabilities.md', 'inbox-review.md'}


def kb_path(cfg: dict[str, Any], key: str) -> Path:
    return Path(cfg["ai_knowledge_base"]) / cfg["mapping"][key]


def system_dir(cfg: dict[str, Any]) -> Path:
    return kb_path(cfg, "system")


def topic_pages_content_dir(cfg: dict[str, Any]) -> Path:
    subdir = cfg.get("topic_page_subdirs", {}).get("pages")
    root = kb_path(cfg, "topic_pages")
    return root / subdir if subdir else root


def topic_pages_moc_dir(cfg: dict[str, Any]) -> Path:
    subdir = cfg.get("topic_page_subdirs", {}).get("moc")
    root = kb_path(cfg, "topic_pages")
    return root / subdir if subdir else root


def system_file(cfg: dict[str, Any], name: str) -> Path:
    root = system_dir(cfg)
    category = "active" if name in SYSTEM_ACTIVE_FILES else "reports" if name in SYSTEM_REPORT_FILES else None
    if not category:
        return root / name
    preferred = root / category / name
    fallback = root / name
    return preferred if preferred.exists() or not fallback.exists() else fallback


def system_active_file(cfg: dict[str, Any], name: str) -> Path:
    return system_file(cfg, name)


def legacy_runtime_dir(cfg: dict[str, Any]) -> Path:
    return system_dir(cfg) / "runtime"


def local_runtime_dir(cfg: dict[str, Any]) -> Path:
    override = os.environ.get("KBM_RUNTIME_ROOT")
    if override:
        root = Path(override).expanduser()
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support" / "knowledge-base-manager"
    elif os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        root = Path(os.environ["LOCALAPPDATA"]) / "knowledge-base-manager"
    else:
        root = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / "knowledge-base-manager"
    namespace = path_slug(str(cfg.get("pipeline", {}).get("runtime_namespace") or cfg.get("name") or "knowledge-base"))
    kb_identity = hashlib.sha256(str(Path(cfg["ai_knowledge_base"]).expanduser().resolve()).encode("utf-8")).hexdigest()[:12]
    return root / f"{namespace}-{kb_identity}" / "runtime"


def runtime_dir(cfg: dict[str, Any]) -> Path:
    storage = cfg.get("pipeline", {}).get("runtime_storage", "legacy")
    if storage == "local":
        return local_runtime_dir(cfg)
    if storage != "legacy":
        raise SystemExit("pipeline.runtime_storage_must_be_local_or_legacy")
    return legacy_runtime_dir(cfg)


def db_path(cfg: dict[str, Any]) -> Path:
    return runtime_dir(cfg) / "pipeline.sqlite3"
