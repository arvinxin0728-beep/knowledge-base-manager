#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path

from kbm.application.editorial_quality import editorial_quality_audit, editorial_quality_for_output


def write_output(root: Path, name: str, body: str) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_generic_output_is_parked_with_repair_actions() -> None:
    with tempfile.TemporaryDirectory() as raw:
        base = Path(raw)
        output = write_output(base, "generic.md", "---\nsource_theme: x\n---\n\n总之，随着时代发展，这具有重要意义。")
        result = editorial_quality_for_output(base, output)
        assert result["status"] == "park"
        assert "insight_density" in result["weak_dimensions"]
        assert result["repair_actions"]


def test_argument_gate_reports_missing_counterpoint() -> None:
    with tempfile.TemporaryDirectory() as raw:
        base = Path(raw)
        output = write_output(
            base,
            "argument.md",
            "---\nsource_theme: x\nfact_check_required: true\n---\n\n## 核心观点\n读者应该行动。\n\n"
            "### 一\n研究证据说明问题。\n### 二\n例如团队案例。\n### 三\n下一步采用清单。\n",
        )
        result = editorial_quality_for_output(base, output)
        assert result["argument_gate"]["core_thesis_explicit"] is True
        assert result["argument_gate"]["three_supporting_moves"] is True
        assert result["argument_gate"]["counterpoint_or_boundary_present"] is False
        assert result["argument_gate_passed"] is False


def test_editorial_audit_aggregates_output_statuses() -> None:
    with tempfile.TemporaryDirectory() as raw:
        base = Path(raw) / "kb"
        outputs = base / "40-outputs"
        write_output(outputs, "one.md", "---\nsource_theme: x\n---\n\n普通内容。")
        cfg = {"ai_knowledge_base": str(base), "mapping": {"outputs": "40-outputs"}}
        result = editorial_quality_audit(cfg)
        assert result["output_count"] == 1
        assert result["needs_attention_count"] == 1
        assert sum(result["status_counts"].values()) == 1
