#!/usr/bin/env python3
"""Transactional source-processing pipeline for large mapped knowledge bases."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ebook_probe import candidate_chapters, chunk_text, extract
from kbm.platform.config import load_config
from kbm.interfaces.pipeline_cli import build_parser
from kbm.application.source_inventory import RefinementCatalog
from kbm.application.model_runs import completed_artifacts, ensure_schema as ensure_model_run_schema, fail_active_job_runs, mark_job_committed, mark_validated
from kbm.platform.paths import (
    db_path, legacy_runtime_dir, local_runtime_dir, runtime_dir,
    system_active_file, system_dir,
)


STATES = ("discovered", "extracted", "refining", "refined", "committed", "failed")
PIPELINE_VERSION = "2.0.0"
SOURCE_EXTS = {".md", ".markdown", ".txt", ".html", ".htm", ".pdf", ".epub", ".docx"}
REQUIRED_HEADING_GROUPS = (
    ("## 一句话价值", "## One-line value"),
    ("## 文章解决的问题", "## Problem addressed"),
    ("## 核心观点", "## Core claims"),
    ("## 可复用模型", "## Reusable models or cases"),
    ("## 存疑点 / 使用边界", "## Limits / fact-check needs"),
    ("## 可连接主题", "## Connected topics"),
    ("## 候选提升", "## Promotion candidate"),
)


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def directory_stats(path: Path) -> dict[str, Any]:
    files = [item for item in path.rglob("*") if item.is_file()] if path.is_dir() else []
    return {"path": str(path), "exists": path.exists(), "files": len(files), "bytes": sum(item.stat().st_size for item in files)}


def database_summary(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"exists": False, "jobs": 0, "events": 0, "refining": 0, "integrity": None}
    with sqlite3.connect(path) as db:
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        jobs = db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        events = db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        refining = db.execute("SELECT COUNT(*) FROM jobs WHERE state='refining'").fetchone()[0]
    return {"exists": True, "jobs": jobs, "events": events, "refining": refining, "integrity": integrity}


def storage_status(cfg: dict[str, Any]) -> dict[str, Any]:
    return {
        "pipeline_version": PIPELINE_VERSION,
        "runtime_storage": cfg.get("pipeline", {}).get("runtime_storage", "legacy"),
        "active": directory_stats(runtime_dir(cfg)),
        "legacy": directory_stats(legacy_runtime_dir(cfg)),
        "local": directory_stats(local_runtime_dir(cfg)),
        "database": database_summary(db_path(cfg)),
    }


def rewrite_runtime_paths(database: Path, old_root: Path, new_root: Path) -> None:
    columns = ("artifact_dir", "extracted_text", "chunks_file", "refinement_file", "refinement_metadata")
    old_prefix = str(old_root.absolute())
    new_prefix = str(new_root.absolute())
    with sqlite3.connect(database) as db:
        for column in columns:
            rows = db.execute(f"SELECT job_id,{column} FROM jobs WHERE {column} IS NOT NULL").fetchall()
            for job_id, value in rows:
                if value == old_prefix or value.startswith(old_prefix + os.sep):
                    replacement = new_prefix + value[len(old_prefix):]
                    db.execute(f"UPDATE jobs SET {column}=? WHERE job_id=?", (replacement, job_id))
        db.commit()


def migrate_runtime(config_path: Path, cfg: dict[str, Any], apply: bool) -> dict[str, Any]:
    source = legacy_runtime_dir(cfg)
    target = local_runtime_dir(cfg)
    source_db = source / "pipeline.sqlite3"
    preflight = {
        "mode": "apply" if apply else "dry-run",
        "source": directory_stats(source),
        "target": directory_stats(target),
        "source_database": database_summary(source_db),
    }
    if cfg.get("pipeline", {}).get("runtime_storage") == "local":
        return preflight | {"migrated": False, "reason": "already_using_local_runtime"}
    if not source_db.is_file():
        return preflight | {"migrated": False, "reason": "legacy_database_missing"}
    if preflight["source_database"]["integrity"] != "ok":
        raise SystemExit("legacy_database_integrity_check_failed")
    if preflight["source_database"]["refining"]:
        raise SystemExit("cannot_migrate_while_jobs_are_refining")
    if target.exists():
        raise SystemExit("local_runtime_target_already_exists")
    if not apply:
        return preflight | {"migrated": False, "ready": True}

    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.parent / f".{target.name}.migrating-{uuid.uuid4().hex}"
    try:
        staging.mkdir()
        for child in source.iterdir():
            if child.name.startswith("pipeline.sqlite3"):
                continue
            destination = staging / child.name
            if child.is_dir():
                shutil.copytree(child, destination)
            else:
                shutil.copy2(child, destination)
        with sqlite3.connect(source_db) as source_conn, sqlite3.connect(staging / "pipeline.sqlite3") as target_conn:
            source_conn.execute("PRAGMA wal_checkpoint(FULL)")
            source_conn.backup(target_conn)
        rewrite_runtime_paths(staging / "pipeline.sqlite3", source, target)
        target_summary = database_summary(staging / "pipeline.sqlite3")
        if target_summary["integrity"] != "ok" or target_summary["jobs"] != preflight["source_database"]["jobs"] or target_summary["events"] != preflight["source_database"]["events"]:
            raise RuntimeError("migrated_database_verification_failed")
        staging.rename(target)
        updated = json.loads(config_path.read_text(encoding="utf-8"))
        updated.setdefault("pipeline", {})["runtime_storage"] = "local"
        updated["pipeline"].setdefault("artifact_retention_days", 7)
        atomic_write(config_path, json.dumps(updated, ensure_ascii=False, indent=2) + "\n")
        return preflight | {"migrated": True, "ready": True, "active": directory_stats(target), "target_database": target_summary}
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def retire_legacy_runtime(cfg: dict[str, Any], apply: bool) -> dict[str, Any]:
    source = legacy_runtime_dir(cfg)
    active = runtime_dir(cfg)
    source_summary = database_summary(source / "pipeline.sqlite3")
    active_summary = database_summary(active / "pipeline.sqlite3")
    result = {
        "mode": "apply" if apply else "dry-run",
        "legacy": directory_stats(source),
        "active": directory_stats(active),
        "legacy_database": source_summary,
        "active_database": active_summary,
    }
    if cfg.get("pipeline", {}).get("runtime_storage") != "local":
        return result | {"retired": False, "reason": "local_runtime_not_active"}
    if not source.exists():
        return result | {"retired": False, "reason": "legacy_runtime_missing"}
    if active_summary["integrity"] != "ok" or source_summary["integrity"] != "ok":
        raise SystemExit("runtime_database_integrity_check_failed")
    if active_summary["jobs"] != source_summary["jobs"] or active_summary["events"] != source_summary["events"]:
        raise SystemExit("runtime_database_counts_do_not_match")
    if active_summary["refining"] or source_summary["refining"]:
        raise SystemExit("cannot_retire_while_jobs_are_refining")
    recovery = active.parent / f"legacy-recovery-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    if not apply:
        return result | {"retired": False, "ready": True, "recovery_path": str(recovery)}
    shutil.move(str(source), str(recovery))
    return result | {"retired": True, "ready": True, "recovery_path": str(recovery), "legacy_exists_after": source.exists()}


def connect(cfg: dict[str, Any]) -> sqlite3.Connection:
    runtime_dir(cfg).mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(db_path(cfg), timeout=30, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA busy_timeout=30000")
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS jobs (
          job_id TEXT PRIMARY KEY,
          source_path TEXT NOT NULL UNIQUE,
          source_type TEXT NOT NULL,
          title TEXT NOT NULL,
          size INTEGER NOT NULL,
          mtime_ns INTEGER NOT NULL,
          source_sha256 TEXT,
          state TEXT NOT NULL CHECK(state IN ('discovered','extracted','refining','refined','committed','failed')),
          failed_stage TEXT,
          attempts INTEGER NOT NULL DEFAULT 0,
          last_error TEXT,
          artifact_dir TEXT,
          extracted_text TEXT,
          chunks_file TEXT,
          refinement_file TEXT,
          refinement_metadata TEXT,
          lease_owner TEXT,
          lease_token TEXT,
          lease_until TEXT,
          discovered_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          committed_at TEXT
        );
        CREATE INDEX IF NOT EXISTS jobs_state_idx ON jobs(state, updated_at);
        CREATE INDEX IF NOT EXISTS jobs_sha_idx ON jobs(source_sha256);
        CREATE TABLE IF NOT EXISTS events (
          event_id INTEGER PRIMARY KEY AUTOINCREMENT,
          job_id TEXT NOT NULL,
          event TEXT NOT NULL,
          from_state TEXT,
          to_state TEXT,
          detail TEXT,
          created_at TEXT NOT NULL,
          FOREIGN KEY(job_id) REFERENCES jobs(job_id)
        );
        """
    )
    ensure_model_run_schema(db)
    return db


def event(db: sqlite3.Connection, job_id: str, name: str, old: str | None, new: str | None, detail: Any = None) -> None:
    db.execute(
        "INSERT INTO events(job_id,event,from_state,to_state,detail,created_at) VALUES(?,?,?,?,?,?)",
        (job_id, name, old, new, json.dumps(detail, ensure_ascii=False) if detail is not None else None, now()),
    )


def source_type_for(name: str, path: Path) -> str:
    if name == "ebooks" or path.suffix.lower() in {".pdf", ".epub", ".docx"}:
        return "ebook"
    if name == "public_accounts":
        return "public_account_article"
    return "article"


def discover(cfg: dict[str, Any], db: sqlite3.Connection) -> dict[str, int]:
    inserted = changed = unchanged = 0
    for library_name, raw in sorted(cfg.get("source_libraries", {}).items()):
        if not raw:
            continue
        root = Path(raw).expanduser()
        if not root.exists():
            continue
        for path in sorted(root.rglob("*"), key=lambda p: str(p)):
            if not path.is_file() or path.suffix.lower() not in SOURCE_EXTS:
                continue
            resolved = str(path.resolve())
            stat = path.stat()
            row = db.execute("SELECT * FROM jobs WHERE source_path=?", (resolved,)).fetchone()
            stamp = now()
            if row is None:
                job_id = hashlib.sha256(resolved.encode("utf-8")).hexdigest()[:20]
                db.execute(
                    "INSERT INTO jobs(job_id,source_path,source_type,title,size,mtime_ns,state,discovered_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
                    (job_id, resolved, source_type_for(library_name, path), path.stem, stat.st_size, stat.st_mtime_ns, "discovered", stamp, stamp),
                )
                event(db, job_id, "discovered", None, "discovered")
                inserted += 1
            elif row["size"] != stat.st_size or row["mtime_ns"] != stat.st_mtime_ns:
                old = row["state"]
                db.execute(
                    "UPDATE jobs SET size=?,mtime_ns=?,state='discovered',failed_stage=NULL,last_error=NULL,source_sha256=NULL,artifact_dir=NULL,extracted_text=NULL,chunks_file=NULL,refinement_file=NULL,refinement_metadata=NULL,lease_owner=NULL,lease_token=NULL,lease_until=NULL,updated_at=?,committed_at=NULL WHERE job_id=?",
                    (stat.st_size, stat.st_mtime_ns, stamp, row["job_id"]),
                )
                event(db, row["job_id"], "source_changed", old, "discovered")
                changed += 1
            else:
                unchanged += 1
    reconciled = reconcile_processed_index(cfg, db)
    return {"inserted": inserted, "changed": changed, "unchanged": unchanged, "reconciled_committed": reconciled}


def reconcile_processed_index(cfg: dict[str, Any], db: sqlite3.Connection) -> int:
    """Import existing canonical index records into a newly created task ledger."""
    index = system_active_file(cfg, "processed-index.jsonl")
    if not index.exists():
        return 0
    rows = index_rows(index)
    records_by_path: dict[str, dict[str, Any]] = {}
    records_by_hash: dict[str, list[dict[str, Any]]] = {}
    for record in rows:
        source = record.get("source_path") or record.get("source_file")
        if source:
            records_by_path[str(Path(source).expanduser().resolve())] = record
        recorded_sha = record.get("source_sha256") or record.get("sha256")
        if recorded_sha:
            records_by_hash.setdefault(recorded_sha, []).append(record)
    reconciled = 0
    index_changed = False
    refinements = RefinementCatalog(cfg)
    for row in db.execute("SELECT * FROM jobs WHERE state!='committed'").fetchall():
        source_sha = None
        record = records_by_path.get(row["source_path"])
        if record is None and records_by_hash:
            source_sha = sha256_file(Path(row["source_path"]))
            hash_matches = records_by_hash.get(source_sha, [])
            if len(hash_matches) == 1:
                record = hash_matches[0]
        if not record:
            continue
        recorded_sha = record.get("source_sha256") or record.get("sha256")
        if recorded_sha:
            source_sha = source_sha or sha256_file(Path(row["source_path"]))
        if recorded_sha and source_sha != recorded_sha:
            continue
        output = refinements.resolve(Path(row["source_path"]), record)
        if output is None and not (record.get("output_file") or record.get("refinement_file")):
            legacy_destination = refinement_destination(cfg, row)
            output = legacy_destination if legacy_destination.is_file() else None
        if output is None:
            continue
        canonical_output = str(output.resolve())
        canonical_sha = recorded_sha or source_sha or sha256_file(Path(row["source_path"]))
        db.execute(
            "UPDATE jobs SET state='committed',source_sha256=?,refinement_file=?,committed_at=?,updated_at=? WHERE job_id=?",
            (canonical_sha, canonical_output, record.get("processed_at") or now(), now(), row["job_id"]),
        )
        event(db, row["job_id"], "reconciled_from_index", row["state"], "committed", {"output_file": canonical_output})
        canonical_fields = {
            "schema_version": 1,
            "source_id": row["job_id"],
            "source_path": row["source_path"],
            "source_sha256": canonical_sha,
            "source_type": row["source_type"],
            "title": record.get("title") or row["title"],
            "output_file": canonical_output,
            "status": "processed",
        }
        if any(record.get(key) != value for key, value in canonical_fields.items()):
            record.update(canonical_fields)
            index_changed = True
        reconciled += 1
    if index_changed:
        atomic_write(index, "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in rows))
    return reconciled


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    tmp = Path(raw)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def extract_jobs(cfg: dict[str, Any], db: sqlite3.Connection, limit: int, max_attempts: int, source_type: str | None = None) -> list[dict[str, Any]]:
    where = "(state='discovered' OR (state='failed' AND failed_stage='extract' AND attempts < ?))"
    params: list[Any] = [max_attempts]
    if source_type:
        where += " AND source_type=?"
        params.append(source_type)
    params.append(limit)
    rows = db.execute(f"SELECT * FROM jobs WHERE {where} ORDER BY updated_at LIMIT ?", params).fetchall()
    results = []
    for row in rows:
        job_id = row["job_id"]
        path = Path(row["source_path"])
        artifact = runtime_dir(cfg) / "artifacts" / job_id
        try:
            title, text = extract(path)
            if not text.strip():
                raise ValueError("no_extractable_text")
            chunks = chunk_text(text, size=int(cfg.get("pipeline", {}).get("chunk_size", 5000)))
            full_text = artifact / "full_text.txt"
            chunks_file = artifact / "chunks.jsonl"
            manifest = artifact / "manifest.json"
            atomic_write(full_text, text)
            atomic_write(chunks_file, "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in chunks))
            source_sha = sha256_file(path)
            manifest_data = {
                "job_id": job_id,
                "source_path": str(path),
                "source_type": row["source_type"],
                "title": title or row["title"],
                "source_sha256": source_sha,
                "characters": len(text),
                "chunk_count": len(chunks),
                "candidate_chapters": candidate_chapters(text),
            }
            atomic_write(manifest, json.dumps(manifest_data, ensure_ascii=False, indent=2) + "\n")
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "UPDATE jobs SET title=?,source_sha256=?,state='extracted',failed_stage=NULL,last_error=NULL,artifact_dir=?,extracted_text=?,chunks_file=?,updated_at=? WHERE job_id=?",
                (title or row["title"], source_sha, str(artifact), str(full_text), str(chunks_file), now(), job_id),
            )
            event(db, job_id, "extracted", row["state"], "extracted", {"chunks": len(chunks)})
            db.commit()
            results.append({"job_id": job_id, "state": "extracted", "chunks": len(chunks)})
        except Exception as exc:  # noqa: BLE001
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "UPDATE jobs SET state='failed',failed_stage='extract',attempts=attempts+1,last_error=?,updated_at=? WHERE job_id=?",
                (str(exc)[:2000], now(), job_id),
            )
            event(db, job_id, "extract_failed", row["state"], "failed", {"error": str(exc)[:500]})
            db.commit()
            results.append({"job_id": job_id, "state": "failed", "error": str(exc)})
    return results


def reap_expired(db: sqlite3.Connection) -> int:
    stamp = now()
    rows = db.execute("SELECT job_id FROM jobs WHERE state='refining' AND lease_until < ?", (stamp,)).fetchall()
    for row in rows:
        fail_active_job_runs(db, row["job_id"], "lease_expired", "pipeline lease expired before model completion")
        db.execute(
            "UPDATE jobs SET state='extracted',lease_owner=NULL,lease_token=NULL,lease_until=NULL,updated_at=? WHERE job_id=?",
            (stamp, row["job_id"]),
        )
        event(db, row["job_id"], "lease_expired", "refining", "extracted")
    return len(rows)


def claim(cfg: dict[str, Any], db: sqlite3.Connection, worker: str, limit: int, lease_minutes: int, source_type: str | None = None) -> list[dict[str, Any]]:
    db.execute("BEGIN IMMEDIATE")
    reap_expired(db)
    if source_type:
        rows = db.execute("SELECT * FROM jobs WHERE state='extracted' AND source_type=? ORDER BY updated_at LIMIT ?", (source_type, limit)).fetchall()
    else:
        rows = db.execute("SELECT * FROM jobs WHERE state='extracted' ORDER BY updated_at LIMIT ?", (limit,)).fetchall()
    claimed = []
    until = (datetime.now(timezone.utc) + timedelta(minutes=lease_minutes)).replace(microsecond=0).isoformat()
    for row in rows:
        token = uuid.uuid4().hex
        db.execute(
            "UPDATE jobs SET state='refining',lease_owner=?,lease_token=?,lease_until=?,attempts=attempts+1,updated_at=? WHERE job_id=? AND state='extracted'",
            (worker, token, until, now(), row["job_id"]),
        )
        event(db, row["job_id"], "claimed", "extracted", "refining", {"worker": worker, "lease_until": until})
        claimed.append({
            "job_id": row["job_id"], "lease_token": token, "lease_until": until,
            "source_path": row["source_path"], "source_type": row["source_type"], "title": row["title"],
            "extracted_text": row["extracted_text"], "chunks_file": row["chunks_file"], "artifact_dir": row["artifact_dir"],
        })
    db.commit()
    return claimed


def validate_refinement(path: Path, metadata: dict[str, Any]) -> list[str]:
    errors = []
    if not path.is_file():
        return ["refinement_file_missing"]
    text = path.read_text(encoding="utf-8", errors="ignore")
    for alternatives in REQUIRED_HEADING_GROUPS:
        if not any(heading in text for heading in alternatives):
            errors.append(f"missing_heading:{'|'.join(alternatives)}")
    if "TBD" in text or "TODO" in text or "待补充" in text:
        errors.append("unfinished_placeholder")
    if len(text.strip()) < 300:
        errors.append("refinement_too_short")
    if not isinstance(metadata.get("topics"), list):
        errors.append("metadata_topics_must_be_array")
    if metadata.get("fact_risk") not in {"low", "medium", "high", "unknown"}:
        errors.append("metadata_fact_risk_invalid")
    return errors


def refinement_destination(cfg: dict[str, Any], row: sqlite3.Row) -> Path:
    root = Path(cfg["ai_knowledge_base"]) / cfg["mapping"]["source_refinements"]
    subdirs = cfg.get("source_refinement_subdirs", {})
    key = "ebooks" if row["source_type"] == "ebook" else "public_accounts" if row["source_type"] == "public_account_article" else "articles"
    return root / subdirs.get(key, key) / f"{safe_name(row['title'])}.md"


def safe_name(value: str) -> str:
    return "".join(c for c in value if c not in '\\/:*?"<>|\n\r\t').strip()[:80] or "untitled"


def date_value(value: Any) -> str:
    text = str(value or "").strip().strip('"').strip("'")
    if len(text) >= 10 and text[:10].count("-") == 2:
        return text[:10]
    return ""


def source_saved_at(row: sqlite3.Row, metadata: dict[str, Any]) -> str:
    explicit = date_value(metadata.get("saved_at"))
    if explicit:
        return explicit
    name = Path(row["source_path"]).name
    if len(name) >= 10 and name[:10].count("-") == 2:
        return name[:10]
    return ""


def strip_leading_dates(value: str) -> str:
    text = value.strip()
    while len(text) > 11 and text[:10].count("-") == 2 and text[10].isspace():
        text = text[11:].strip()
    return text


def dated_refinement_destination(cfg: dict[str, Any], row: sqlite3.Row, metadata: dict[str, Any]) -> Path:
    dest = refinement_destination(cfg, row)
    created = date_value(metadata.get("created_at")) or now()[:10]
    updated = date_value(metadata.get("updated_at")) or created
    saved = source_saved_at(row, metadata)
    if not saved:
        return dest
    title = strip_leading_dates(str(metadata.get("title") or row["title"]))
    return dest.with_name(f"{updated} {created} {saved} {safe_name(title)}.md")


def with_canonical_frontmatter(row: sqlite3.Row, metadata: dict[str, Any], content: str) -> str:
    if content.lstrip().startswith("---\n"):
        return content
    topics = metadata.get("topics", [])
    created = date_value(metadata.get("created_at")) or now()[:10]
    updated = date_value(metadata.get("updated_at")) or created
    saved = source_saved_at(row, metadata)
    lines = [
        "---",
        "stage: 来源精炼",
        "status: processed",
        f"theme_cluster: {json.dumps(str(metadata.get('theme_cluster') or (topics[0] if topics else '未归类')), ensure_ascii=False)}",
        "tags:",
        "  - 来源精炼",
    ]
    lines.extend(f"  - {json.dumps(str(topic), ensure_ascii=False)}" for topic in topics)
    lines.extend([
        "related_sources: []",
        "related_topics: []",
        "related_assets: []",
        "related_outputs: []",
        'moc: ""',
        f"obsidian_links_updated: {json.dumps(updated, ensure_ascii=False)}",
        f"account: {json.dumps(str(metadata.get('account') or ''), ensure_ascii=False)}",
        f"author: {json.dumps(str(metadata.get('author') or ''), ensure_ascii=False)}",
        f"processed_at: {json.dumps(now()[:10], ensure_ascii=False)}",
        f"published_at: {json.dumps(date_value(metadata.get('published_at')), ensure_ascii=False)}",
        f"saved_at: {json.dumps(saved, ensure_ascii=False)}",
        f"source_file: {json.dumps(row['source_path'], ensure_ascii=False)}",
        f"source_type: {json.dumps(row['source_type'], ensure_ascii=False)}",
        f"url: {json.dumps(str(metadata.get('url') or ''), ensure_ascii=False)}",
        f"created_at: {json.dumps(created, ensure_ascii=False)}",
        f"updated_at: {json.dumps(updated, ensure_ascii=False)}",
        "---",
        "",
        content.lstrip(),
    ])
    return "\n".join(lines)


def index_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def submit(cfg: dict[str, Any], db: sqlite3.Connection, job_id: str, token: str, refinement: Path | None, metadata_path: Path | None, model_run_id: str | None = None) -> dict[str, Any]:
    if model_run_id:
        refinement, metadata_path = completed_artifacts(db, model_run_id, job_id, token)
    if refinement is None or metadata_path is None:
        raise SystemExit("refinement_and_metadata_or_model_run_required")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    errors = validate_refinement(refinement, metadata)
    if errors:
        raise SystemExit(json.dumps({"submitted": False, "errors": errors}, ensure_ascii=False))
    # Gate-10 check: block low-quality refinements before they enter the pipeline
    import subprocess as _sp
    _gate = _sp.run([sys.executable, str(Path(__file__).resolve().parents[1] / "scripts" / "kb_manager.py"), "check-refinement", "--file", str(refinement)], capture_output=True, text=True)
    if _gate.returncode != 0:
        try:
            _detail = json.loads(_gate.stdout)
        except Exception:
            _detail = {"blockers": ["gate-10_check_failed"]}
        raise SystemExit(json.dumps({"submitted": False, "blocked_by_gate10": True, **_detail}, ensure_ascii=False))
    db.execute("BEGIN IMMEDIATE")
    row = db.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
    if row is None:
        db.rollback()
        raise SystemExit("unknown_job")
    if row["state"] in {"refined", "committed"}:
        db.rollback()
        return {"submitted": True, "idempotent": True, "state": row["state"]}
    if row["state"] != "refining" or row["lease_token"] != token:
        db.rollback()
        raise SystemExit("invalid_or_expired_lease")
    artifact = Path(row["artifact_dir"])
    staged_note = artifact / "refinement.md"
    staged_metadata = artifact / "refinement-metadata.json"
    atomic_write(staged_note, refinement.read_text(encoding="utf-8"))
    atomic_write(staged_metadata, json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    db.execute(
        "UPDATE jobs SET state='refined',refinement_file=?,refinement_metadata=?,lease_owner=NULL,lease_token=NULL,lease_until=NULL,last_error=NULL,failed_stage=NULL,updated_at=? WHERE job_id=?",
        (str(staged_note), str(staged_metadata), now(), job_id),
    )
    event(db, job_id, "submitted", "refining", "refined")
    if model_run_id:
        mark_validated(db, model_run_id)
    db.commit()
    return {"submitted": True, "idempotent": False, "state": "refined", "refinement_file": str(staged_note), "model_run_id": model_run_id}


def commit(cfg: dict[str, Any], db: sqlite3.Connection, job_id: str) -> dict[str, Any]:
    db.execute("BEGIN IMMEDIATE")
    row = db.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
    if row is None:
        db.rollback()
        raise SystemExit("unknown_job")
    if row["state"] == "committed":
        db.rollback()
        return {"committed": True, "idempotent": True, "output_file": row["refinement_file"]}
    if row["state"] != "refined":
        db.rollback()
        raise SystemExit("job_must_be_refined_before_commit")
    refinement = Path(row["refinement_file"])
    metadata_path = Path(row["refinement_metadata"])
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    errors = validate_refinement(refinement, metadata)
    if errors:
        db.rollback()
        raise SystemExit(json.dumps({"committed": False, "errors": errors}, ensure_ascii=False))
    dest = dated_refinement_destination(cfg, row, metadata)
    if dest.exists() and Path(row["refinement_file"]).resolve() != dest.resolve():
        db.rollback()
        raise SystemExit(json.dumps({"committed": False, "error": "destination_exists", "existing_file": str(dest)}, ensure_ascii=False))
    content = with_canonical_frontmatter(row, metadata, refinement.read_text(encoding="utf-8"))
    atomic_write(dest, content)
    index = system_active_file(cfg, "processed-index.jsonl")
    rows = index_rows(index)
    record = {
        "schema_version": 1, "source_id": job_id, "source_path": row["source_path"],
        "source_sha256": row["source_sha256"] or "", "source_type": row["source_type"],
        "title": metadata.get("title") or row["title"], "processed_at": now(), "output_file": str(dest),
        "topics": metadata.get("topics", []), "status": "processed", "fact_risk": metadata.get("fact_risk", "unknown"),
        "fact_check_required": bool(metadata.get("fact_check_required", False)),
    }
    rows = [item for item in rows if item.get("source_id") != job_id]
    rows.append(record)
    atomic_write(index, "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in rows))
    db.execute(
        "UPDATE jobs SET state='committed',refinement_file=?,lease_owner=NULL,lease_token=NULL,lease_until=NULL,last_error=NULL,failed_stage=NULL,updated_at=?,committed_at=? WHERE job_id=?",
        (str(dest), now(), now(), job_id),
    )
    event(db, job_id, "committed", "refined", "committed", {"output_file": str(dest)})
    mark_job_committed(db, job_id)
    db.commit()
    return {"committed": True, "idempotent": False, "output_file": str(dest)}


def fail(db: sqlite3.Connection, job_id: str, token: str, error: str) -> dict[str, Any]:
    db.execute("BEGIN IMMEDIATE")
    row = db.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
    if row is None or row["state"] != "refining" or row["lease_token"] != token:
        db.rollback()
        raise SystemExit("invalid_or_expired_lease")
    db.execute(
        "UPDATE jobs SET state='failed',failed_stage='refine',last_error=?,lease_owner=NULL,lease_token=NULL,lease_until=NULL,updated_at=? WHERE job_id=?",
        (error[:2000], now(), job_id),
    )
    event(db, job_id, "refine_failed", "refining", "failed", {"error": error[:500]})
    fail_active_job_runs(db, job_id, "refinement_failed", error)
    db.commit()
    return {"job_id": job_id, "state": "failed"}


def adopt_existing(cfg: dict[str, Any], db: sqlite3.Connection, job_id: str, existing_file: Path) -> dict[str, Any]:
    if not existing_file.is_file():
        raise SystemExit("existing_file_missing")
    text = existing_file.read_text(encoding="utf-8", errors="ignore")
    if "stage:" not in text or "来源精炼" not in text:
        raise SystemExit("existing_file_is_not_source_refinement")
    # Gate-10 check: block low-quality refinements before they enter the pipeline
    import subprocess as _sp
    _gate = _sp.run([sys.executable, str(Path(__file__).resolve().parents[1] / "scripts" / "kb_manager.py"), "check-refinement", "--file", str(existing_file)], capture_output=True, text=True)
    if _gate.returncode != 0:
        try:
            _detail = json.loads(_gate.stdout)
        except Exception:
            _detail = {"blockers": ["gate-10_check_failed"]}
        raise SystemExit(json.dumps({"adopted": False, "blocked_by_gate10": True, **_detail}, ensure_ascii=False))
    db.execute("BEGIN IMMEDIATE")
    row = db.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
    if row is None:
        db.rollback()
        raise SystemExit("unknown_job")
    index = system_active_file(cfg, "processed-index.jsonl")
    rows = index_rows(index)
    matched = False
    deduplicated = []
    for record in rows:
        is_match = record.get("source_id") == job_id or str(Path(record.get("source_path", "")).expanduser().resolve()) == row["source_path"]
        if is_match and not matched:
            record["source_id"] = job_id
            record["source_path"] = row["source_path"]
            record["output_file"] = str(existing_file.resolve())
            matched = True
            deduplicated.append(record)
        elif not is_match:
            deduplicated.append(record)
    rows = deduplicated
    if not matched:
        rows.append({
            "schema_version": 1, "source_id": job_id, "source_path": row["source_path"],
            "source_sha256": row["source_sha256"] or "", "source_type": row["source_type"],
            "title": row["title"], "processed_at": now(), "output_file": str(existing_file.resolve()),
            "topics": [], "status": "processed", "fact_risk": "unknown", "fact_check_required": False,
        })
    atomic_write(index, "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in rows))
    db.execute("UPDATE jobs SET state='committed',refinement_file=?,updated_at=?,committed_at=COALESCE(committed_at,?) WHERE job_id=?", (str(existing_file.resolve()), now(), now(), job_id))
    event(db, job_id, "adopted_existing_refinement", row["state"], "committed", {"output_file": str(existing_file.resolve())})
    db.commit()
    return {"adopted": True, "job_id": job_id, "output_file": str(existing_file.resolve())}


def retry(db: sqlite3.Connection, limit: int) -> int:
    db.execute("BEGIN IMMEDIATE")
    rows = db.execute("SELECT job_id,failed_stage FROM jobs WHERE state='failed' ORDER BY updated_at LIMIT ?", (limit,)).fetchall()
    for row in rows:
        target = "extracted" if row["failed_stage"] == "refine" else "discovered"
        db.execute("UPDATE jobs SET state=?,failed_stage=NULL,last_error=NULL,updated_at=? WHERE job_id=?", (target, now(), row["job_id"]))
        event(db, row["job_id"], "retried", "failed", target)
    db.commit()
    return len(rows)


def status(db: sqlite3.Connection) -> dict[str, Any]:
    reap_expired(db)
    counts = {state: 0 for state in STATES}
    for row in db.execute("SELECT state,COUNT(*) AS n FROM jobs GROUP BY state"):
        counts[row["state"]] = row["n"]
    failures = [dict(row) for row in db.execute("SELECT job_id,source_path,failed_stage,attempts,last_error,updated_at FROM jobs WHERE state='failed' ORDER BY updated_at DESC LIMIT 20")]
    return {"total": sum(counts.values()), "states": counts, "recent_failures": failures}


def commit_ready(cfg: dict[str, Any], db: sqlite3.Connection, limit: int) -> list[dict[str, Any]]:
    job_ids = [row["job_id"] for row in db.execute("SELECT job_id FROM jobs WHERE state='refined' ORDER BY updated_at LIMIT ?", (limit,)).fetchall()]
    return [commit(cfg, db, job_id) | {"job_id": job_id} for job_id in job_ids]


def cleanup_artifacts(cfg: dict[str, Any], db: sqlite3.Connection, retention_days: int, apply: bool) -> dict[str, Any]:
    """Preview or remove artifacts for safely committed jobs after a retention period."""
    if retention_days < 0:
        raise SystemExit("retention_days_must_be_non_negative")
    artifacts_root = (runtime_dir(cfg) / "artifacts").resolve()
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    candidates: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    rows = db.execute("SELECT * FROM jobs WHERE state='committed' AND artifact_dir IS NOT NULL ORDER BY committed_at").fetchall()
    for row in rows:
        artifact = Path(row["artifact_dir"])
        source = Path(row["source_path"])
        output = Path(row["refinement_file"] or "")
        try:
            committed_at = datetime.fromisoformat(row["committed_at"] or row["updated_at"])
        except (TypeError, ValueError):
            skipped.append({"job_id": row["job_id"], "reason": "invalid_commit_time"})
            continue
        reasons = []
        if committed_at > cutoff:
            reasons.append("inside_retention_period")
        if not source.is_file():
            reasons.append("source_missing")
        if not output.is_file():
            reasons.append("final_refinement_missing")
        try:
            resolved = artifact.resolve()
            if resolved.parent != artifacts_root or resolved.name != row["job_id"]:
                reasons.append("artifact_path_outside_managed_root")
        except OSError:
            reasons.append("artifact_path_invalid")
        if not artifact.is_dir():
            reasons.append("artifact_directory_missing")
        if reasons:
            skipped.append({"job_id": row["job_id"], "reason": ",".join(reasons)})
            continue
        files = [path for path in artifact.rglob("*") if path.is_file()]
        candidates.append({
            "job_id": row["job_id"],
            "artifact_dir": str(artifact),
            "file_count": len(files),
            "bytes": sum(path.stat().st_size for path in files),
        })

    if apply and candidates:
        trash = runtime_dir(cfg) / ".cleanup-trash" / uuid.uuid4().hex
        moved: list[tuple[Path, Path]] = []
        db.execute("BEGIN IMMEDIATE")
        try:
            for item in candidates:
                source = Path(item["artifact_dir"])
                destination = trash / item["job_id"]
                destination.parent.mkdir(parents=True, exist_ok=True)
                source.rename(destination)
                moved.append((source, destination))
                db.execute(
                    "UPDATE jobs SET artifact_dir=NULL,extracted_text=NULL,chunks_file=NULL,refinement_metadata=NULL,updated_at=? WHERE job_id=?",
                    (now(), item["job_id"]),
                )
                event(db, item["job_id"], "artifacts_cleaned", "committed", "committed", item)
            db.commit()
        except Exception:
            db.rollback()
            for source, destination in reversed(moved):
                if destination.exists() and not source.exists():
                    destination.rename(source)
            raise
        finally:
            if trash.exists():
                shutil.rmtree(trash)
    return {
        "mode": "apply" if apply else "dry-run",
        "retention_days": retention_days,
        "candidate_jobs": len(candidates),
        "candidate_files": sum(item["file_count"] for item in candidates),
        "candidate_bytes": sum(item["bytes"] for item in candidates),
        "candidates": candidates,
        "skipped": skipped,
    }


def main() -> None:
    args = build_parser(PIPELINE_VERSION).parse_args()
    cfg = load_config(args.config)
    pipeline_cfg = cfg.get("pipeline", {})
    if args.command == "migrate-runtime":
        print(json.dumps(migrate_runtime(args.config, cfg, args.apply), ensure_ascii=False, indent=2))
        return
    if args.command == "retire-legacy-runtime":
        print(json.dumps(retire_legacy_runtime(cfg, args.apply), ensure_ascii=False, indent=2))
        return
    if args.command == "storage-status":
        print(json.dumps(storage_status(cfg), ensure_ascii=False, indent=2))
        return
    db = connect(cfg)
    try:
        if args.command == "init": result = {"database": str(db_path(cfg)), "initialized": True}
        elif args.command == "discover": result = discover(cfg, db)
        elif args.command == "prepare":
            found = discover(cfg, db)
            result = {"discover": found, "extract": extract_jobs(cfg, db, args.limit or int(pipeline_cfg.get("default_batch_size", 10)), args.max_attempts or int(pipeline_cfg.get("max_attempts", 3)), args.source_type), "status": status(db)}
        elif args.command == "extract": result = {"jobs": extract_jobs(cfg, db, args.limit or int(pipeline_cfg.get("default_batch_size", 10)), args.max_attempts or int(pipeline_cfg.get("max_attempts", 3)), args.source_type)}
        elif args.command == "claim": result = {"jobs": claim(cfg, db, args.worker, args.limit or int(pipeline_cfg.get("default_batch_size", 10)), args.lease_minutes or int(pipeline_cfg.get("lease_minutes", 120)), args.source_type)}
        elif args.command == "submit": result = submit(cfg, db, args.job_id, args.lease_token, args.refinement, args.metadata, args.model_run_id)
        elif args.command == "commit": result = commit(cfg, db, args.job_id)
        elif args.command == "commit-ready": result = {"jobs": commit_ready(cfg, db, args.limit)}
        elif args.command == "fail": result = fail(db, args.job_id, args.lease_token, args.error)
        elif args.command == "adopt-existing": result = adopt_existing(cfg, db, args.job_id, args.existing_file)
        elif args.command == "retry": result = {"retried": retry(db, args.limit)}
        elif args.command == "cleanup": result = cleanup_artifacts(cfg, db, args.retention_days if args.retention_days is not None else int(pipeline_cfg.get("artifact_retention_days", 7)), args.apply)
        else: result = status(db)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
