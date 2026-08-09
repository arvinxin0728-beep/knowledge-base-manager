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


if __name__ == "__main__":
    test_source_weighting_separates_primary_and_marketing_evidence()
    test_verification_result_becomes_stale_after_source_rewrite()
    print("ok")
