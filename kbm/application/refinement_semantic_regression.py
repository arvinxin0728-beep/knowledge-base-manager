"""Deterministic golden regression for source-refinement fidelity."""

from __future__ import annotations

import re
from typing import Any


def _normalized(text: str) -> str:
    return re.sub(r"[\s，。；：、,.!?！？:;\-—_`'\"（）()]", "", text).lower()


def evaluate_golden_case(case: dict[str, Any]) -> dict[str, Any]:
    refinement = _normalized(str(case.get("refinement") or ""))
    required = [str(value) for value in case.get("required_claims", [])]
    forbidden = [str(value) for value in case.get("forbidden_claims", [])]
    missing = [claim for claim in required if _normalized(claim) not in refinement]
    unsupported = [claim for claim in forbidden if _normalized(claim) in refinement]
    coverage = (len(required) - len(missing)) / len(required) if required else 1.0
    return {
        "id": str(case.get("id") or ""),
        "passed": not missing and not unsupported,
        "coverage": coverage,
        "missing_required_claims": missing,
        "present_forbidden_claims": unsupported,
    }


def evaluate_golden_suite(cases: list[dict[str, Any]]) -> dict[str, Any]:
    results = [evaluate_golden_case(case) for case in cases]
    mean_coverage = sum(item["coverage"] for item in results) / len(results) if results else 1.0
    return {
        "passed": all(item["passed"] for item in results),
        "case_count": len(results),
        "passed_count": sum(1 for item in results if item["passed"]),
        "mean_required_claim_coverage": mean_coverage,
        "results": results,
    }
