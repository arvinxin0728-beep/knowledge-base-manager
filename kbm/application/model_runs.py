"""Transactional model-run ledger layered on top of pipeline jobs."""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kbm.platform.paths import db_path, runtime_dir


MODEL_STATES = ("running", "completed", "validated", "committed", "failed")


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def connect_model_ledger(cfg: dict[str, Any]) -> sqlite3.Connection:
    database = db_path(cfg)
    if not database.exists():
        raise ValueError("pipeline_not_initialized")
    db = sqlite3.connect(database, timeout=30, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA busy_timeout=30000")
    ensure_schema(db)
    return db


def ensure_schema(db: sqlite3.Connection) -> None:
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS model_runs (
          run_id TEXT PRIMARY KEY,
          job_id TEXT NOT NULL,
          lease_token TEXT NOT NULL,
          state TEXT NOT NULL CHECK(state IN ('running','completed','validated','committed','failed')),
          provider TEXT NOT NULL,
          model TEXT NOT NULL,
          prompt_version TEXT NOT NULL,
          prompt_sha256 TEXT,
          input_sha256 TEXT NOT NULL,
          output_sha256 TEXT,
          output_snapshot TEXT,
          metadata_snapshot TEXT,
          input_tokens INTEGER,
          output_tokens INTEGER,
          duration_ms INTEGER,
          error_code TEXT,
          error_detail TEXT,
          started_at TEXT NOT NULL,
          completed_at TEXT,
          validated_at TEXT,
          committed_at TEXT,
          FOREIGN KEY(job_id) REFERENCES jobs(job_id)
        );
        CREATE INDEX IF NOT EXISTS model_runs_job_idx ON model_runs(job_id, started_at);
        CREATE INDEX IF NOT EXISTS model_runs_state_idx ON model_runs(state, started_at);
        """
    )


def _row(db: sqlite3.Connection, run_id: str) -> sqlite3.Row:
    row = db.execute("SELECT * FROM model_runs WHERE run_id=?", (run_id,)).fetchone()
    if row is None:
        raise ValueError("model_run_not_found")
    return row


def public_run(row: sqlite3.Row) -> dict[str, Any]:
    return {
        key: row[key] for key in (
            "run_id", "job_id", "state", "provider", "model", "prompt_version",
            "prompt_sha256", "input_sha256", "output_sha256", "output_snapshot",
            "metadata_snapshot", "input_tokens", "output_tokens", "duration_ms",
            "error_code", "started_at", "completed_at", "validated_at", "committed_at",
        )
    }


def start_run(
    db: sqlite3.Connection, *, job_id: str, lease_token: str, provider: str,
    model: str, prompt_version: str, prompt_sha256: str | None = None,
) -> dict[str, Any]:
    job = db.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
    if job is None:
        raise ValueError("job_not_found")
    if job["state"] != "refining" or job["lease_token"] != lease_token or (job["lease_until"] and job["lease_until"] < now()):
        raise ValueError("invalid_or_expired_lease")
    active = db.execute(
        "SELECT * FROM model_runs WHERE job_id=? AND lease_token=? AND state IN ('running','completed','validated') ORDER BY started_at DESC LIMIT 1",
        (job_id, lease_token),
    ).fetchone()
    if active is not None:
        return {"started": True, "idempotent": True, "run": public_run(active)}
    extracted = Path(job["extracted_text"] or "")
    if not extracted.is_file():
        raise ValueError("extracted_input_missing")
    run_id = uuid.uuid4().hex
    db.execute("BEGIN IMMEDIATE")
    db.execute(
        "INSERT INTO model_runs(run_id,job_id,lease_token,state,provider,model,prompt_version,prompt_sha256,input_sha256,started_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (run_id, job_id, lease_token, "running", provider, model, prompt_version, prompt_sha256, sha256_file(extracted), now()),
    )
    db.commit()
    return {"started": True, "idempotent": False, "run": public_run(_row(db, run_id))}


def complete_run(
    cfg: dict[str, Any], db: sqlite3.Connection, *, run_id: str, output: Path,
    metadata: Path, input_tokens: int | None = None,
    output_tokens: int | None = None, duration_ms: int | None = None,
) -> dict[str, Any]:
    row = _row(db, run_id)
    if row["state"] in {"completed", "validated", "committed"}:
        return {"completed": True, "idempotent": True, "run": public_run(row)}
    if row["state"] != "running":
        raise ValueError("model_run_must_be_running")
    job = db.execute("SELECT state,lease_token,lease_until FROM jobs WHERE job_id=?", (row["job_id"],)).fetchone()
    if job is None or job["state"] != "refining" or job["lease_token"] != row["lease_token"] or (job["lease_until"] and job["lease_until"] < now()):
        raise ValueError("invalid_or_expired_lease")
    if not output.is_file():
        raise ValueError("model_output_missing")
    if not metadata.is_file():
        raise ValueError("model_metadata_missing")
    if any(value is not None and value < 0 for value in (input_tokens, output_tokens, duration_ms)):
        raise ValueError("model_metrics_must_be_non_negative")
    destination = runtime_dir(cfg) / "artifacts" / row["job_id"] / "model-runs" / run_id
    destination.mkdir(parents=True, exist_ok=True)
    output_snapshot = destination / "refinement.md"
    shutil.copy2(output, output_snapshot)
    metadata_snapshot = destination / "metadata.json"
    shutil.copy2(metadata, metadata_snapshot)
    db.execute("BEGIN IMMEDIATE")
    db.execute(
        "UPDATE model_runs SET state='completed',output_sha256=?,output_snapshot=?,metadata_snapshot=?,input_tokens=?,output_tokens=?,duration_ms=?,completed_at=? WHERE run_id=? AND state='running'",
        (sha256_file(output_snapshot), str(output_snapshot), str(metadata_snapshot),
         input_tokens, output_tokens, duration_ms, now(), run_id),
    )
    db.commit()
    return {"completed": True, "idempotent": False, "run": public_run(_row(db, run_id))}


def fail_run(db: sqlite3.Connection, *, run_id: str, error_code: str, error_detail: str = "") -> dict[str, Any]:
    row = _row(db, run_id)
    if row["state"] == "failed":
        return {"failed": True, "idempotent": True, "run": public_run(row)}
    if row["state"] in {"validated", "committed"}:
        raise ValueError("validated_model_run_cannot_fail")
    db.execute(
        "UPDATE model_runs SET state='failed',error_code=?,error_detail=?,completed_at=? WHERE run_id=?",
        (error_code, error_detail[:2000], now(), run_id),
    )
    return {"failed": True, "idempotent": False, "run": public_run(_row(db, run_id))}


def completed_artifacts(db: sqlite3.Connection, run_id: str, job_id: str, lease_token: str) -> tuple[Path, Path]:
    row = _row(db, run_id)
    if row["job_id"] != job_id or row["lease_token"] != lease_token:
        raise ValueError("model_run_job_or_lease_mismatch")
    if row["state"] not in {"completed", "validated"}:
        raise ValueError("model_run_must_be_completed")
    if not row["output_snapshot"] or not row["metadata_snapshot"]:
        raise ValueError("model_run_artifacts_incomplete")
    return Path(row["output_snapshot"]), Path(row["metadata_snapshot"])


def mark_validated(db: sqlite3.Connection, run_id: str) -> None:
    db.execute("UPDATE model_runs SET state='validated',validated_at=? WHERE run_id=? AND state='completed'", (now(), run_id))


def mark_job_committed(db: sqlite3.Connection, job_id: str) -> None:
    db.execute("UPDATE model_runs SET state='committed',committed_at=? WHERE job_id=? AND state='validated'", (now(), job_id))


def fail_active_job_runs(db: sqlite3.Connection, job_id: str, error_code: str, detail: str = "") -> None:
    db.execute(
        "UPDATE model_runs SET state='failed',error_code=?,error_detail=?,completed_at=? WHERE job_id=? AND state='running'",
        (error_code, detail[:2000], now(), job_id),
    )


def list_runs(db: sqlite3.Connection, *, job_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    if job_id:
        rows = db.execute("SELECT * FROM model_runs WHERE job_id=? ORDER BY started_at DESC LIMIT ?", (job_id, limit)).fetchall()
    else:
        rows = db.execute("SELECT * FROM model_runs ORDER BY started_at DESC LIMIT ?", (limit,)).fetchall()
    return [public_run(row) for row in rows]


def summary(db: sqlite3.Connection) -> dict[str, Any]:
    states = {state: 0 for state in MODEL_STATES}
    for row in db.execute("SELECT state,COUNT(*) AS count FROM model_runs GROUP BY state"):
        states[row["state"]] = row["count"]
    totals = db.execute(
        "SELECT COUNT(*) AS runs,COALESCE(SUM(input_tokens),0) AS input_tokens,COALESCE(SUM(output_tokens),0) AS output_tokens,COALESCE(SUM(duration_ms),0) AS duration_ms FROM model_runs"
    ).fetchone()
    return {"states": states, **dict(totals)}
