#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path

from kbm.application.output_quality import article_maturity, evaluate_output_file, render_output_quality


def test_short_article_remains_seed() -> None:
    text = "读者问题：为什么系统失败？\n## 正文草稿\n### 原因\n例如团队缺少边界。\n事实边界：待核查。"
    maturity, checks = article_maturity(text, text)
    assert maturity == "article_seed"
    assert checks["article_body_1500_zh"] is False


def test_non_article_output_preserves_mechanical_contract() -> None:
    with tempfile.TemporaryDirectory() as raw:
        base = Path(raw)
        output = base / "memo.md"
        output.write_text(
            "---\nsource_theme: systems\nfact_check_required: false\n---\n\n"
            "## Audience\nTeam lead\n\n## Core Message\nEvidence matters.\n\n"
            "## Evidence\nBased on internal sources.\n\n## Limits\nScope is bounded.\n\n"
            + "Actionable material. " * 30,
            encoding="utf-8",
        )
        result = evaluate_output_file(base, output)
        assert result["status"] == "usable"
        assert result["article_maturity"] is None
        assert result["score"] == 8


def test_quality_report_uses_dynamic_denominator() -> None:
    report = render_output_quality([
        {"file": "memo.md", "score": 2, "status": "usable", "checks": {"a": True, "b": True}}
    ])
    assert "| `memo.md` | 2/2 | usable |" in report
    assert "- a: pass" in report
