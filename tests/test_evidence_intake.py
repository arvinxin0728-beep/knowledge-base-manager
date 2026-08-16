#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path

from kbm.application.evidence_intake import (
    evidence_intake_audit,
    init_evidence_intake,
    render_evidence_intake_audit,
    render_source_capabilities,
)


def make_config(root: Path) -> dict:
    return {
        "ai_knowledge_base": str(root / "kb"),
        "mapping": {"system": "00-system", "source_refinements": "10-refinements"},
        "source_refinement_subdirs": {"system_evidence_fill": "system-evidence"},
    }


def test_evidence_intake_dry_run_is_non_mutating() -> None:
    with tempfile.TemporaryDirectory() as raw:
        cfg = make_config(Path(raw))
        result = init_evidence_intake(cfg)
        assert result["created_count"] == 12
        assert not Path(result["ledger"]).exists()
        assert evidence_intake_audit(cfg)["passed"] is False


def test_evidence_intake_apply_creates_complete_skeleton() -> None:
    with tempfile.TemporaryDirectory() as raw:
        cfg = make_config(Path(raw))
        prepared: list[str] = []
        result = init_evidence_intake(cfg, apply=True, prepare_system=lambda _cfg: prepared.append("called"))
        audit = evidence_intake_audit(cfg)
        assert prepared == ["called"]
        assert result["created_count"] == 12
        assert audit["passed"] is True
        assert audit["missing_count"] == 0


def test_evidence_intake_reports_are_stable() -> None:
    with tempfile.TemporaryDirectory() as raw:
        cfg = make_config(Path(raw))
        init_evidence_intake(cfg, apply=True)
        audit = evidence_intake_audit(cfg)
        assert "status: passed" in render_evidence_intake_audit(audit)
        assert "evidence_intake_audit_passed: true" in render_source_capabilities(cfg, audit)
