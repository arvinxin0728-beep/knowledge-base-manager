#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "kb_pipeline.py"


def invoke(config: Path, *args: str) -> dict:
    output = subprocess.check_output(["python3", str(SCRIPT), "--config", str(config), *args], text=True)
    return json.loads(output)


def make_case(article_count: int = 1) -> tuple[tempfile.TemporaryDirectory, Path, Path]:
    temp = tempfile.TemporaryDirectory()
    root = Path(temp.name)
    sources = root / "sources"
    sources.mkdir()
    for index in range(article_count):
        (sources / f"article-{index}.md").write_text(
            f"# Article {index}\n\n" + "Evidence-based knowledge processing. " * 30,
            encoding="utf-8",
        )
    kb = root / "kb"
    config = root / "config.json"
    config.write_text(json.dumps({
        "ai_knowledge_base": str(kb),
        "source_libraries": {"articles": str(sources)},
        "mapping": {"system": "00-system", "source_refinements": "10-source-refinements"},
        "source_refinement_subdirs": {"articles": "articles"},
        "pipeline": {"chunk_size": 500},
    }), encoding="utf-8")
    return temp, config, sources


def processed_index(config: Path) -> Path:
    cfg = json.loads(config.read_text(encoding="utf-8"))
    return Path(cfg["ai_knowledge_base"]) / "00-system" / "active" / "processed-index.jsonl"


def write_refinement(root: Path, suffix: str = "") -> tuple[Path, Path]:
    note = root / f"refinement{suffix}.md"
    note.write_text(
        "# Article refinement\n\n"
        "## One-line value\nEvidence becomes reusable through a controlled pipeline.\n\n"
        "## Problem addressed\nHow to process knowledge reliably.\n\n"
        "## Core claims\nA durable state ledger prevents duplicate work and supports recovery.\n\n"
        "## Reusable models or cases\nUse explicit stages and idempotent commits.\n\n"
        "## Limits / fact-check needs\nThis is a workflow claim with low factual risk.\n\n"
        "## Connected topics\nKnowledge systems; workflow reliability.\n\n"
        "## Promotion candidate\nCandidate for a workflow topic page.\n",
        encoding="utf-8",
    )
    metadata = root / f"metadata{suffix}.json"
    metadata.write_text(json.dumps({
        "title": "Article refinement",
        "topics": ["Knowledge systems"],
        "theme_cluster": "Knowledge systems",
        "saved_at": "2026-01-01",
        "fact_risk": "low",
        "fact_check_required": False,
    }), encoding="utf-8")
    return note, metadata


def test_full_lifecycle_and_idempotent_commit() -> None:
    temp, config, _sources = make_case()
    root = Path(temp.name)
    try:
        assert invoke(config, "init")["initialized"] is True
        assert invoke(config, "discover")["inserted"] == 1
        extracted = invoke(config, "extract", "--limit", "10")["jobs"]
        assert extracted[0]["state"] == "extracted"
        job = invoke(config, "claim", "--worker", "test", "--limit", "1")["jobs"][0]
        note, metadata = write_refinement(root)
        submitted = invoke(config, "submit", "--job-id", job["job_id"], "--lease-token", job["lease_token"], "--refinement", str(note), "--metadata", str(metadata))
        assert submitted["state"] == "refined"
        assert invoke(config, "status")["states"]["refined"] == 1
        committed = invoke(config, "commit", "--job-id", job["job_id"])
        assert committed["committed"] is True and committed["idempotent"] is False
        again = invoke(config, "commit", "--job-id", job["job_id"])
        assert again["idempotent"] is True
        status = invoke(config, "status")
        assert status["states"]["committed"] == 1
        index = processed_index(config)
        assert len(index.read_text(encoding="utf-8").splitlines()) == 1
        output = Path(committed["output_file"]).read_text(encoding="utf-8")
        assert output.startswith("---\nstage: 来源精炼")
        assert "stage: 来源精炼" in output
        assert 'saved_at: "2026-01-01"' in output
    finally:
        temp.cleanup()


def test_failed_refinement_can_retry_without_reextracting() -> None:
    temp, config, _sources = make_case()
    try:
        invoke(config, "discover")
        invoke(config, "extract")
        job = invoke(config, "claim", "--worker", "test")["jobs"][0]
        failed = invoke(config, "fail", "--job-id", job["job_id"], "--lease-token", job["lease_token"], "--error", "model interrupted")
        assert failed["state"] == "failed"
        assert invoke(config, "retry")["retried"] == 1
        claimed = invoke(config, "claim", "--worker", "test-2")["jobs"]
        assert claimed[0]["job_id"] == job["job_id"]
        assert claimed[0]["extracted_text"]
    finally:
        temp.cleanup()


def test_expired_lease_is_reclaimed() -> None:
    temp, config, _sources = make_case()
    try:
        invoke(config, "discover")
        invoke(config, "extract")
        first = invoke(config, "claim", "--worker", "dead-worker")["jobs"][0]
        cfg = json.loads(config.read_text())
        database = Path(cfg["ai_knowledge_base"]) / "00-system" / "runtime" / "pipeline.sqlite3"
        with sqlite3.connect(database) as db:
            db.execute("UPDATE jobs SET lease_until='2000-01-01T00:00:00+00:00' WHERE job_id=?", (first["job_id"],))
        second = invoke(config, "claim", "--worker", "replacement")["jobs"][0]
        assert second["job_id"] == first["job_id"]
        assert second["lease_token"] != first["lease_token"]
    finally:
        temp.cleanup()


def test_source_change_returns_committed_job_to_discovered() -> None:
    temp, config, sources = make_case()
    root = Path(temp.name)
    try:
        invoke(config, "discover"); invoke(config, "extract")
        job = invoke(config, "claim", "--worker", "test")["jobs"][0]
        note, metadata = write_refinement(root)
        invoke(config, "submit", "--job-id", job["job_id"], "--lease-token", job["lease_token"], "--refinement", str(note), "--metadata", str(metadata))
        invoke(config, "commit", "--job-id", job["job_id"])
        article = next(sources.glob("*.md"))
        article.write_text(article.read_text(encoding="utf-8") + "\nChanged.\n", encoding="utf-8")
        result = invoke(config, "discover")
        assert result["changed"] == 1
        assert invoke(config, "status")["states"]["discovered"] == 1
    finally:
        temp.cleanup()


def test_thousand_source_discovery() -> None:
    temp, config, _sources = make_case(article_count=1000)
    try:
        result = invoke(config, "discover")
        assert result["inserted"] == 1000
        assert invoke(config, "status")["total"] == 1000
        assert invoke(config, "discover")["unchanged"] == 1000
    finally:
        temp.cleanup()


def test_source_type_filter_limits_prepare_and_claim() -> None:
    temp, config, _sources = make_case()
    try:
        cfg = json.loads(config.read_text())
        ebooks = Path(temp.name) / "ebooks"
        ebooks.mkdir()
        (ebooks / "book.md").write_text("# Book\n\n" + "Book content. " * 40, encoding="utf-8")
        cfg["source_libraries"]["ebooks"] = str(ebooks)
        config.write_text(json.dumps(cfg), encoding="utf-8")
        prepared = invoke(config, "prepare", "--limit", "10", "--source-type", "public_account_article")
        assert prepared["extract"] == []
        prepared = invoke(config, "prepare", "--limit", "10", "--source-type", "article")
        assert len(prepared["extract"]) == 1
        assert invoke(config, "claim", "--worker", "filtered", "--source-type", "ebook")["jobs"] == []
        assert len(invoke(config, "claim", "--worker", "filtered", "--source-type", "article")["jobs"]) == 1
    finally:
        temp.cleanup()


def test_existing_index_is_reconciled_into_new_ledger() -> None:
    temp, config, sources = make_case()
    try:
        cfg = json.loads(config.read_text())
        source = next(sources.glob("*.md")).resolve()
        output = Path(cfg["ai_knowledge_base"]) / "10-source-refinements" / "articles" / "existing.md"
        output.parent.mkdir(parents=True)
        output.write_text("# Existing refinement\n", encoding="utf-8")
        index = Path(cfg["ai_knowledge_base"]) / "00-system" / "processed-index.jsonl"
        index.parent.mkdir(parents=True)
        index.write_text(json.dumps({"source_path": str(source), "output_file": str(output), "processed_at": "2026-01-01"}) + "\n", encoding="utf-8")
        result = invoke(config, "discover")
        assert result["reconciled_committed"] == 1
        state = invoke(config, "status")["states"]
        assert state["committed"] == 1 and state["discovered"] == 0
    finally:
        temp.cleanup()


def test_legacy_blank_output_is_reconciled_through_path_alias() -> None:
    temp, config, sources = make_case()
    try:
        cfg = json.loads(config.read_text())
        alias = Path(temp.name) / "source-alias"
        alias.symlink_to(sources, target_is_directory=True)
        cfg["source_libraries"]["articles"] = str(alias)
        config.write_text(json.dumps(cfg), encoding="utf-8")

        source = next(sources.glob("*.md")).resolve()
        output = Path(cfg["ai_knowledge_base"]) / "10-source-refinements" / "articles" / f"{source.stem}.md"
        output.parent.mkdir(parents=True)
        output.write_text("---\nstage: 来源精炼\n---\n\n# Existing refinement\n", encoding="utf-8")
        index = Path(cfg["ai_knowledge_base"]) / "00-system" / "processed-index.jsonl"
        index.parent.mkdir(parents=True)
        index.write_text(json.dumps({
            "source_id": "legacy-id",
            "source_path": str(alias / source.name),
            "source_sha256": "",
            "source_type": "article",
            "title": source.stem,
            "processed_at": "2026-01-01",
            "output_file": "",
            "topics": ["test"],
            "status": "processed",
        }) + "\n", encoding="utf-8")

        result = invoke(config, "discover")
        assert result["reconciled_committed"] == 1
        assert invoke(config, "status")["states"]["committed"] == 1
        repaired = json.loads(index.read_text(encoding="utf-8"))
        assert repaired["source_id"] != "legacy-id"
        assert repaired["output_file"] == str(output.resolve())
        assert repaired["source_sha256"]
    finally:
        temp.cleanup()


def test_reconciliation_recovers_renamed_refinement_and_stale_output_path() -> None:
    temp, config, sources = make_case()
    try:
        cfg = json.loads(config.read_text())
        source = next(sources.glob("*.md")).resolve()
        output = Path(cfg["ai_knowledge_base"]) / "10-source-refinements" / "articles" / "2026-08-09 2026-01-01 renamed.md"
        output.parent.mkdir(parents=True)
        historical_source = source.with_name("「article」-0.md")
        output.write_text(
            "---\nstage: 来源精炼\nsource_file: " + json.dumps(str(historical_source), ensure_ascii=False) + "\n---\n\n# Existing refinement\n",
            encoding="utf-8",
        )
        index = Path(cfg["ai_knowledge_base"]) / "00-system" / "processed-index.jsonl"
        index.parent.mkdir(parents=True)
        index.write_text(json.dumps({
            "source_path": str(source), "source_sha256": "",
            "output_file": str(Path(temp.name) / "missing-old-name.md"),
            "processed_at": "2026-01-01",
        }) + "\n", encoding="utf-8")
        result = invoke(config, "discover")
        assert result["reconciled_committed"] == 1
        assert invoke(config, "status")["states"]["committed"] == 1
        repaired = json.loads(index.read_text(encoding="utf-8"))
        assert repaired["output_file"] == str(output.resolve())
    finally:
        temp.cleanup()


def test_reconciliation_recovers_a_refined_job() -> None:
    temp, config, _sources = make_case()
    root = Path(temp.name)
    try:
        invoke(config, "discover")
        invoke(config, "extract")
        job = invoke(config, "claim", "--worker", "interrupted")["jobs"][0]
        note, metadata = write_refinement(root)
        invoke(config, "submit", "--job-id", job["job_id"], "--lease-token", job["lease_token"], "--refinement", str(note), "--metadata", str(metadata))

        cfg = json.loads(config.read_text())
        output = Path(cfg["ai_knowledge_base"]) / "10-source-refinements" / "articles" / "article-0.md"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("---\nstage: 来源精炼\n---\n\n# Existing refinement\n", encoding="utf-8")
        source = next((Path(temp.name) / "sources").glob("*.md")).resolve()
        index = Path(cfg["ai_knowledge_base"]) / "00-system" / "processed-index.jsonl"
        index.write_text(json.dumps({
            "schema_version": 1,
            "source_id": job["job_id"],
            "source_path": str(source),
            "source_sha256": "",
            "source_type": "article",
            "title": source.stem,
            "processed_at": "2026-01-01",
            "output_file": str(output),
            "topics": [],
            "status": "processed",
        }) + "\n", encoding="utf-8")

        result = invoke(config, "discover")
        assert result["reconciled_committed"] == 1
        assert invoke(config, "status")["states"]["committed"] == 1
        assert invoke(config, "status")["states"]["refined"] == 0
    finally:
        temp.cleanup()


def test_cleanup_is_dry_run_by_default_and_only_removes_safe_committed_artifacts() -> None:
    temp, config, _sources = make_case(article_count=2)
    root = Path(temp.name)
    try:
        invoke(config, "discover")
        invoke(config, "extract", "--limit", "2")
        job = invoke(config, "claim", "--worker", "test", "--limit", "1")["jobs"][0]
        note, metadata = write_refinement(root)
        invoke(config, "submit", "--job-id", job["job_id"], "--lease-token", job["lease_token"], "--refinement", str(note), "--metadata", str(metadata))
        committed = invoke(config, "commit", "--job-id", job["job_id"])
        artifact = Path(job["artifact_dir"])
        assert artifact.exists()

        preview = invoke(config, "cleanup", "--retention-days", "0")
        assert preview["mode"] == "dry-run" and preview["candidate_jobs"] == 1
        assert artifact.exists()
        applied = invoke(config, "cleanup", "--retention-days", "0", "--apply")
        assert applied["candidate_jobs"] == 1 and not artifact.exists()
        assert Path(committed["output_file"]).exists()

        cfg = json.loads(config.read_text())
        database = Path(cfg["ai_knowledge_base"]) / "00-system" / "runtime" / "pipeline.sqlite3"
        with sqlite3.connect(database) as db:
            row = db.execute("SELECT state,artifact_dir,refinement_file FROM jobs WHERE job_id=?", (job["job_id"],)).fetchone()
        assert row[0] == "committed" and row[1] is None and Path(row[2]).exists()
        assert invoke(config, "cleanup", "--retention-days", "0")["candidate_jobs"] == 0
    finally:
        temp.cleanup()


def test_runtime_migration_preserves_state_rewrites_paths_and_retires_recoverably() -> None:
    temp, config, _sources = make_case(article_count=2)
    root = Path(temp.name)
    previous = os.environ.get("KBM_RUNTIME_ROOT")
    os.environ["KBM_RUNTIME_ROOT"] = str(root / "local-state")
    try:
        invoke(config, "discover")
        invoke(config, "extract", "--limit", "2")
        legacy = Path(json.loads(config.read_text())["ai_knowledge_base"]) / "00-system" / "runtime"
        preview = invoke(config, "migrate-runtime")
        assert preview["mode"] == "dry-run" and preview["ready"] is True
        assert json.loads(config.read_text()).get("pipeline", {}).get("runtime_storage") is None

        migrated = invoke(config, "migrate-runtime", "--apply")
        assert migrated["migrated"] is True
        cfg = json.loads(config.read_text())
        assert cfg["pipeline"]["runtime_storage"] == "local"
        active = Path(invoke(config, "storage-status")["active"]["path"])
        assert active.exists() and legacy.exists()
        with sqlite3.connect(active / "pipeline.sqlite3") as db:
            paths = db.execute("SELECT artifact_dir FROM jobs WHERE artifact_dir IS NOT NULL").fetchall()
        assert paths and all(str(active) in row[0] for row in paths)
        assert invoke(config, "status")["total"] == 2

        retire_preview = invoke(config, "retire-legacy-runtime")
        assert retire_preview["ready"] is True and legacy.exists()
        retired = invoke(config, "retire-legacy-runtime", "--apply")
        assert retired["retired"] is True and not legacy.exists()
        assert Path(retired["recovery_path"]).exists()
        assert invoke(config, "status")["total"] == 2
    finally:
        if previous is None:
            os.environ.pop("KBM_RUNTIME_ROOT", None)
        else:
            os.environ["KBM_RUNTIME_ROOT"] = previous
        temp.cleanup()


if __name__ == "__main__":
    test_full_lifecycle_and_idempotent_commit()
    test_failed_refinement_can_retry_without_reextracting()
    test_expired_lease_is_reclaimed()
    test_source_change_returns_committed_job_to_discovered()
    test_thousand_source_discovery()
    test_source_type_filter_limits_prepare_and_claim()
    test_existing_index_is_reconciled_into_new_ledger()
    test_legacy_blank_output_is_reconciled_through_path_alias()
    test_reconciliation_recovers_renamed_refinement_and_stale_output_path()
    test_reconciliation_recovers_a_refined_job()
    test_cleanup_is_dry_run_by_default_and_only_removes_safe_committed_artifacts()
    test_runtime_migration_preserves_state_rewrites_paths_and_retires_recoverably()
    print("ok")
