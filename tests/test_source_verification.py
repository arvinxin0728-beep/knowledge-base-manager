#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kbm.application.source_verification import (
    append_verification_result, classify_source_quality, risk_signals,
    verification_items, verification_status,
)


def config(root: Path) -> dict:
    system = root / "00-system" / "active"
    system.mkdir(parents=True)
    for name in ("10-来源精炼", "20-主题页", "40-输出"):
        (root / name).mkdir()
    return {
        "ai_knowledge_base": str(root),
        "mapping": {"system": "00-system", "source_refinements": "10-来源精炼", "topic_pages": "20-主题页", "outputs": "40-输出"},
    }


def test_source_weighting_separates_primary_and_marketing_evidence() -> None:
    official = classify_source_quality({"source_type": "paper", "saved_at": "2026-08-01"}, Path("paper.md"), "primary evidence")
    marketing = classify_source_quality({"source_type": "public_account_article", "saved_at": "2020-01-01"}, Path("暴利必看.md"), "月入百万，未来3年预计提升50%")
    assert official["source_quality_tier"] == "A"
    assert official["promotion_weight"] == 1.3
    assert marketing["source_quality_tier"] == "D"
    assert "marketing_or_title_bait" in marketing["flags"]
    signals = risk_signals("TOP 10 项目预计未来3年提升 50%")
    assert {"ranking", "forecast", "quantified_improvement"} <= set(signals)


def test_source_channel_uses_provenance_before_ambiguous_title_words() -> None:
    public = classify_source_quality(
        {"source_type": "public_account_article"},
        Path("公众号/AI行业研究报告解读.md"),
        "这是一篇对研究报告的解读文章。",
    )
    assert public["source_channel"] == "public_account"
    assert public["source_channel_basis"] == "metadata"
    ambiguous = classify_source_quality({}, Path("AI研究方法.md"), "研究如何改进工作流。")
    assert ambiguous["source_channel"] == "unknown"
    assert ambiguous["source_channel_confidence"] == "low"
    report = classify_source_quality({"source_type": "research_report"}, Path("市场观察.md"), "报告正文")
    assert report["source_channel"] == "report"


def test_verification_result_becomes_stale_after_source_rewrite() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        cfg = config(root)
        source = root / "10-来源精炼" / "claim.md"
        source.write_text("数据显示市场增长率提升 50%", encoding="utf-8")
        item = verification_items(cfg)[0]
        append_verification_result(cfg, {"schema_version": 1, "id": item["id"], "status": "verified", "verified_at": "2000-01-01T00:00:00", "claim": "", "evidence_url_or_path": "", "verifier": "test", "note": ""})
        timestamp = source.stat().st_mtime + 2
        os.utime(source, (timestamp, timestamp))
        result = verification_status(cfg)
        assert result["items"][0]["status"] == "stale"
        assert result["pending_count"] == 0
        assert result["counts"] == {"stale": 1}
        assert result["stale_count"] == 1


def test_verification_status_reconciles_superseded_and_orphaned_results() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        cfg = config(root)
        source = root / "10-来源精炼" / "claim.md"
        source.write_text("数据显示市场增长率提升 50%", encoding="utf-8")
        item = verification_items(cfg)[0]
        for status in ("pending", "verified"):
            append_verification_result(cfg, {"schema_version": 1, "id": item["id"], "status": status, "verified_at": "2999-01-01T00:00:00"})
        append_verification_result(cfg, {"schema_version": 1, "id": "orphaned", "status": "verified", "verified_at": "2999-01-01T00:00:00"})
        result = verification_status(cfg)
        assert result["ledger_row_count"] == 3
        assert result["result_rows"] == 2
        assert result["superseded_result_count"] == 1
        assert result["orphaned_result_count"] == 1
        assert result["orphaned_result_ids"] == ["orphaned"]


if __name__ == "__main__":
    test_source_weighting_separates_primary_and_marketing_evidence()
    test_source_channel_uses_provenance_before_ambiguous_title_words()
    test_verification_result_becomes_stale_after_source_rewrite()
    test_verification_status_reconciles_superseded_and_orphaned_results()
    print("ok")
