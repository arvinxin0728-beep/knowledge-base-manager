#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANAGER = ROOT / "scripts" / "kb_manager.py"
PIPELINE = ROOT / "scripts" / "kb_pipeline.py"


def run_json(*args: str) -> dict:
    return json.loads(subprocess.check_output(["python3", *args], text=True))


def manager(*args: str) -> dict:
    return run_json(str(MANAGER), *args)


def pipeline(config: Path, *args: str) -> dict:
    return run_json(str(PIPELINE), "--config", str(config), *args)


def test_new_user_portable_lifecycle() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        sources = root / "Knowledge-System" / "Sources" / "Articles"
        kb = root / "Knowledge-System" / "AI-Knowledge-Base"
        config = kb / "00-system" / "kb-config.json"
        previous_runtime = os.environ.get("KBM_RUNTIME_ROOT")
        os.environ["KBM_RUNTIME_ROOT"] = str(root / "runtime-state")
        try:
            run_new_user_case(config, kb, sources, root)
        finally:
            if previous_runtime is None:
                os.environ.pop("KBM_RUNTIME_ROOT", None)
            else:
                os.environ["KBM_RUNTIME_ROOT"] = previous_runtime


def run_new_user_case(config: Path, kb: Path, sources: Path, root: Path) -> None:
    manager(
        "init",
        "--config", str(config),
        "--ai-knowledge-base", str(kb),
        "--articles", str(sources),
        "--language", "en",
        "--apply",
    )
    assert manager("validate-config", "--config", str(config))["valid"] is True
    assert manager("doctor", "--config", str(config))["healthy"] is True

    for index in range(3):
        (sources / f"article-{index}.md").write_text(
            "# Knowledge workflow\n\n"
            "A reusable knowledge system needs source refinement, topic synthesis, reusable assets, and output review.\n"
            "Connected topics: Knowledge workflow, Output review.\n",
            encoding="utf-8",
        )

    pipeline(config, "discover")
    pipeline(config, "extract", "--limit", "3")
    for _ in range(3):
        jobs = pipeline(config, "claim", "--worker", "e2e", "--limit", "1")["jobs"]
        assert jobs
        job = jobs[0]
        refinement = root / f"refinement-{job['job_id']}.md"
        metadata = root / f"metadata-{job['job_id']}.json"
        refinement.write_text(
            "# Knowledge workflow source\n\n"
            "---\n"
            "stage: source_refinement\n"
            "status: processed\n"
            "fact_check_required: false\n"
            "---\n\n"
            "## One-line value\nA knowledge workflow turns raw sources into reusable output.\n\n"
            "## Problem addressed\nHow to avoid inert content archives.\n\n"
            "## Core claims\nA layered workflow improves reuse.\n\n"
            "## Reusable models or cases\nSource refinement, topic page, asset, output.\n\n"
            "## Limits / fact-check needs\nMethod claim only.\n\n"
            "## Connected topics\nKnowledge workflow, Output review.\n\n"
            "## Promotion candidate\nCandidate for knowledge workflow topic.\n",
            encoding="utf-8",
        )
        metadata.write_text(
            json.dumps({
                "title": "Knowledge workflow source",
                "topics": ["Knowledge workflow", "Output review"],
                "fact_risk": "low",
                "fact_check_required": False,
            }),
            encoding="utf-8",
        )
        pipeline(config, "submit", "--job-id", job["job_id"], "--lease-token", job["lease_token"], "--refinement", str(refinement), "--metadata", str(metadata))
        pipeline(config, "commit", "--job-id", job["job_id"])

    status = pipeline(config, "status")
    assert status["states"]["committed"] == 3
    promote = manager("promote", "--config", str(config), "--apply", "--create-stubs")
    assert promote["clusters"]
    assert promote["stub_artifacts"]
    assert all("/00-system/stubs/" in path for path in promote["stub_artifacts"])
    assert not any((kb / "20-topic-pages" / "pages").glob("*.md"))

    result = manager("run", "--config", str(config), "--apply")
    assert result["apply"] is True
    assert result["quality_gate_passed"] is True
    gate = manager("quality-gate", "--config", str(config), "--strict")
    assert gate["passed"] is True
    assert manager("package-lint", "--strict")["passed"] is True


if __name__ == "__main__":
    test_new_user_portable_lifecycle()
    print("ok")
