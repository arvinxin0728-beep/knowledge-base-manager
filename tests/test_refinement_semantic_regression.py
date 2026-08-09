#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kbm.application.refinement_semantic_regression import evaluate_golden_case, evaluate_golden_suite


FIXTURE = Path(__file__).parent / "fixtures" / "refinement_semantic_gold.json"


def test_ten_case_golden_refinement_suite_preserves_required_claims() -> None:
    cases = json.loads(FIXTURE.read_text(encoding="utf-8"))
    result = evaluate_golden_suite(cases)
    assert result["case_count"] == 10
    assert result["passed_count"] == 10
    assert result["mean_required_claim_coverage"] == 1.0
    assert result["passed"] is True


def test_golden_refinement_gate_detects_omission_and_unsupported_claim() -> None:
    result = evaluate_golden_case({
        "id": "negative",
        "refinement": "模型判断可以替代核验。",
        "required_claims": ["可靠的一手来源核验"],
        "forbidden_claims": ["模型判断可以替代核验"],
    })
    assert result["passed"] is False
    assert result["coverage"] == 0.0
    assert result["missing_required_claims"] == ["可靠的一手来源核验"]
    assert result["present_forbidden_claims"] == ["模型判断可以替代核验"]


if __name__ == "__main__":
    test_ten_case_golden_refinement_suite_preserves_required_claims()
    test_golden_refinement_gate_detects_omission_and_unsupported_claim()
    print("ok")
