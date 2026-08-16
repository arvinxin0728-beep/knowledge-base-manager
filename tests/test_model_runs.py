#!/usr/bin/env python3
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_pipeline import invoke, make_case, write_refinement


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "scripts" / "kb_model.py"


def model(config: Path, *args: str) -> dict:
    return json.loads(subprocess.check_output(["python3", str(MODEL), "--config", str(config), *args], text=True))


def test_model_run_is_snapshotted_validated_and_committed() -> None:
    temp, config, _sources = make_case()
    root = Path(temp.name)
    try:
        invoke(config, "discover"); invoke(config, "extract")
        job = invoke(config, "claim", "--worker", "model-worker")["jobs"][0]
        started = model(
            config, "start", "--job-id", job["job_id"], "--lease-token", job["lease_token"],
            "--provider", "synthetic", "--model", "test-model", "--prompt-version", "refinement-v1",
        )
        run_id = started["run"]["run_id"]
        assert model(
            config, "start", "--job-id", job["job_id"], "--lease-token", job["lease_token"],
            "--provider", "synthetic", "--model", "test-model", "--prompt-version", "refinement-v1",
        )["idempotent"] is True
        note, metadata = write_refinement(root)
        completed = model(
            config, "complete", "--run-id", run_id, "--output", str(note), "--metadata", str(metadata),
            "--input-tokens", "100", "--output-tokens", "50", "--duration-ms", "1200",
        )
        snapshot = Path(completed["run"]["output_snapshot"])
        assert snapshot.is_file() and snapshot != note
        note.unlink(); metadata.unlink()
        submitted = invoke(
            config, "submit", "--job-id", job["job_id"], "--lease-token", job["lease_token"],
            "--model-run-id", run_id,
        )
        assert submitted["model_run_id"] == run_id
        assert model(config, "list", "--job-id", job["job_id"])["runs"][0]["state"] == "validated"
        invoke(config, "commit", "--job-id", job["job_id"])
        final = model(config, "list", "--job-id", job["job_id"])["runs"][0]
        assert final["state"] == "committed"
        status = model(config, "status")
        assert status["input_tokens"] == 100 and status["output_tokens"] == 50
    finally:
        temp.cleanup()


def test_model_failure_is_auditable_and_job_can_retry() -> None:
    temp, config, _sources = make_case()
    try:
        invoke(config, "discover"); invoke(config, "extract")
        job = invoke(config, "claim", "--worker", "model-worker")["jobs"][0]
        run_id = model(
            config, "start", "--job-id", job["job_id"], "--lease-token", job["lease_token"],
            "--model", "test-model", "--prompt-version", "v1",
        )["run"]["run_id"]
        assert model(config, "fail", "--run-id", run_id, "--error-code", "timeout")["run"]["state"] == "failed"
        invoke(config, "fail", "--job-id", job["job_id"], "--lease-token", job["lease_token"], "--error", "timeout")
        assert invoke(config, "retry")["retried"] == 1
        assert invoke(config, "claim", "--worker", "retry")["jobs"][0]["job_id"] == job["job_id"]
    finally:
        temp.cleanup()


def test_model_completion_rejects_an_expired_lease() -> None:
    temp, config, _sources = make_case()
    root = Path(temp.name)
    try:
        invoke(config, "discover"); invoke(config, "extract")
        job = invoke(config, "claim", "--worker", "expired")["jobs"][0]
        run_id = model(
            config, "start", "--job-id", job["job_id"], "--lease-token", job["lease_token"],
            "--model", "test-model", "--prompt-version", "v1",
        )["run"]["run_id"]
        cfg = json.loads(config.read_text(encoding="utf-8"))
        database = Path(cfg["ai_knowledge_base"]) / "00-system" / "runtime" / "pipeline.sqlite3"
        with sqlite3.connect(database) as db:
            db.execute("UPDATE jobs SET lease_until='2000-01-01T00:00:00+00:00' WHERE job_id=?", (job["job_id"],))
        note, metadata = write_refinement(root)
        failed = subprocess.run(
            ["python3", str(MODEL), "--config", str(config), "complete", "--run-id", run_id,
             "--output", str(note), "--metadata", str(metadata)], text=True, capture_output=True,
        )
        assert failed.returncode != 0 and "invalid_or_expired_lease" in failed.stdout
    finally:
        temp.cleanup()
