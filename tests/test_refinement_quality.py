#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kbm.application.refinement_quality import check_refinement, gate_10, resolve_essential_aliases


VALID_NOTE = """---
theme_cluster: 视频研究
related_sources:
  - Peer
---
# Example

## 一句话价值
这篇材料说明如何把视频内容转换成可以验证和复用的研究材料。

## 文章解决的问题
它解决如何在保留来源边界的前提下，把长视频转换成可检索、可验证、可继续综合的研究材料。

## 核心观点
1. 视频处理必须保留时间戳、原始字幕和关键帧之间的可追溯关系，避免精炼结果失去证据上下文。
2. 转录只是提取阶段，只有经过阅读、判断、质量门和正式提交以后，内容才可以进入知识系统。

## 可复用模型
视频发现 → 音轨与字幕提取 → 时间戳切块 → 模型精炼 → 质量检查 → 原子提交。

## 可复用案例
一段访谈可以同时生成带时间戳的转录文本、核心观点精炼和被引用的关键帧。

## 可连接主题
- 视频研究
- 来源可追溯性

## 候选提升
积累三个独立来源后，再判断是否形成视频研究方法主题页。
"""


def config(root: Path) -> dict:
    return {
        "ai_knowledge_base": str(root),
        "mapping": {"source_refinements": "10-来源精炼"},
        "quality": {"batch_model_repeat_threshold": 0.5},
    }


def test_single_refinement_contract_passes_and_blocks_placeholders() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        valid = root / "valid.md"
        valid.write_text(VALID_NOTE, encoding="utf-8")
        assert check_refinement(valid)["passed"] is True
        invalid = root / "invalid.md"
        invalid.write_text(VALID_NOTE.replace("视频发现 → 音轨与字幕提取 → 时间戳切块 → 模型精炼 → 质量检查 → 原子提交。", "（待补充模型）"), encoding="utf-8")
        result = check_refinement(invalid)
        assert result["passed"] is False
        assert any("placeholder" in issue for issue in result["blockers"])


def test_batch_gate_blocks_repeated_model_text() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        refinements = root / "10-来源精炼"
        refinements.mkdir()
        (refinements / "one.md").write_text(VALID_NOTE, encoding="utf-8")
        (refinements / "two.md").write_text(VALID_NOTE.replace("# Example", "# Second"), encoding="utf-8")
        result = gate_10(config(root))
        assert result["passed"] is False
        assert result["failed_count"] == 0
        assert result["batch_model_repeat_rate"] == 1.0
        assert result["batch_issues"]


RENAMED_SECTIONS_NOTE = VALID_NOTE.replace(
    "## 文章解决的问题", "## 解决的业务问题"
).replace(
    "## 核心观点", "## 核心知识点"
).replace(
    "## 可复用模型", "## 可复用销售话术/卖点"
).replace(
    "## 可复用案例", "## 可复用客户案例"
)


def test_renamed_sections_fail_without_config_alias() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        note = root / "renamed.md"
        note.write_text(RENAMED_SECTIONS_NOTE, encoding="utf-8")
        result = check_refinement(note)
        assert result["passed"] is False
        assert any("missing_section" in b for b in result["blockers"])


def test_researcher_can_declare_essential_aliases_for_renamed_sections() -> None:
    quality_cfg = {
        "essential_aliases": {
            "文章解决的问题": ["解决的业务问题"],
            "核心观点": ["核心知识点"],
            "可复用模型": ["可复用销售话术/卖点"],
            "可复用案例": ["可复用客户案例"],
        }
    }
    merged = resolve_essential_aliases(quality_cfg)
    # Built-in English aliases for unrelated canonical names must still be present.
    assert "Core claims" in merged["核心观点"]
    assert merged["核心观点"] == ["Core claims", "Core points", "Core argument", "核心知识点"]

    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        note = root / "renamed.md"
        note.write_text(RENAMED_SECTIONS_NOTE, encoding="utf-8")
        result = check_refinement(note, essential_aliases=merged)
        assert result["passed"] is True


def test_empty_theme_cluster_blocks_by_default_when_other_frontmatter_present() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        note = root / "note.md"
        note.write_text(VALID_NOTE.replace("theme_cluster: 视频研究", "theme_cluster:"), encoding="utf-8")
        result = check_refinement(note)
        assert result["passed"] is False
        assert any("invalid_theme_cluster" in b for b in result["blockers"])


def test_researcher_can_defer_theme_cluster_to_promotion_review() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        note = root / "note.md"
        note.write_text(VALID_NOTE.replace("theme_cluster: 视频研究", "theme_cluster:"), encoding="utf-8")
        result = check_refinement(note, require_theme_cluster_at_refinement=False)
        assert result["passed"] is True
        assert any("missing_theme_cluster" in w for w in result["warnings"])

        refinements = root / "10-来源精炼"
        refinements.mkdir()
        note.rename(refinements / "note.md")
        cfg = config(root)
        cfg["quality"]["require_theme_cluster_at_refinement"] = False
        gate_result = gate_10(cfg)
        assert gate_result["failed_count"] == 0


def test_gate_10_reads_essential_aliases_from_config() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        refinements = root / "10-来源精炼"
        refinements.mkdir()
        (refinements / "one.md").write_text(RENAMED_SECTIONS_NOTE, encoding="utf-8")
        cfg = config(root)
        cfg["quality"]["essential_aliases"] = {
            "文章解决的问题": ["解决的业务问题"],
            "核心观点": ["核心知识点"],
            "可复用模型": ["可复用销售话术/卖点"],
            "可复用案例": ["可复用客户案例"],
        }
        result = gate_10(cfg)
        assert result["failed_count"] == 0


if __name__ == "__main__":
    test_single_refinement_contract_passes_and_blocks_placeholders()
    test_batch_gate_blocks_repeated_model_text()
    test_renamed_sections_fail_without_config_alias()
    test_researcher_can_declare_essential_aliases_for_renamed_sections()
    test_empty_theme_cluster_blocks_by_default_when_other_frontmatter_present()
    test_researcher_can_defer_theme_cluster_to_promotion_review()
    test_gate_10_reads_essential_aliases_from_config()
    print("ok")
