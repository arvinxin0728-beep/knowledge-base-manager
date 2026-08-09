#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kbm.application.promotion_runtime import (
    append_promotion_decisions, promotion_decision_rows, write_run_checkpoint,
    write_stub_artifacts,
)
from kbm.platform.jsonl import read_jsonl_objects, write_jsonl


CLUSTER = {
    "id": "research-system", "name": "Research System", "question": "How?",
    "source_count": 3, "score": 5, "action": "topic_page_asset_output",
    "asset_type": "methods", "output_type": "feynman", "risk": "medium",
    "fact_check_required": True, "sources": [{"source_id": "s1", "title": "One"}],
}


def make_config(root: Path) -> dict:
    system = root / "00-system"
    (system / "active").mkdir(parents=True)
    return {
        "ai_knowledge_base": str(root),
        "mapping": {"system": "00-system"},
        "reusable_asset_subdirs": {"methods": "methods"},
        "output_subdirs": {"feynman": "feynman"},
    }


def test_decision_ledger_is_idempotent_and_jsonl_reports_parse_errors() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        cfg = make_config(root)
        rows = promotion_decision_rows([CLUSTER], decision_context="test")
        append_promotion_decisions(cfg, rows)
        append_promotion_decisions(cfg, rows)
        ledger = root / "00-system" / "active" / "promotion-decision.jsonl"
        loaded, errors = read_jsonl_objects(ledger)
        assert len(loaded) == 1 and errors == []
        ledger.write_text(ledger.read_text(encoding="utf-8") + "not-json\n", encoding="utf-8")
        _loaded, errors = read_jsonl_objects(ledger)
        assert errors and errors[0]["line"] == 2
        rewritten = root / "rewritten.jsonl"
        write_jsonl(rewritten, loaded)
        assert read_jsonl_objects(rewritten)[0] == loaded


def test_checkpoint_and_stubs_remain_recoverable_and_system_scoped() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        cfg = make_config(root)
        written = write_stub_artifacts(cfg, [CLUSTER])
        assert len(written) == 3
        assert write_stub_artifacts(cfg, [CLUSTER]) == []
        assert all("/00-system/stubs/" in path for path in written)
        assert not (root / "20-topic-pages").exists()
        assert not (root / "30-reusable-assets").exists()
        assert not (root / "40-outputs").exists()
        write_run_checkpoint(cfg, objective="promote", stage="promotion_review", cost_tier="medium", status="waiting_for_approval", clusters=[CLUSTER], written=written)
        state = json.loads((root / "00-system" / "active" / "active-run-state.json").read_text(encoding="utf-8"))
        assert state["status"] == "waiting_for_approval"
        assert state["candidates"][0]["cluster_id"] == "research-system"
        assert state["generated_files"] == written


if __name__ == "__main__":
    test_decision_ledger_is_idempotent_and_jsonl_reports_parse_errors()
    test_checkpoint_and_stubs_remain_recoverable_and_system_scoped()
    print("ok")
