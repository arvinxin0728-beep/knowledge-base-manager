#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kbm.application.refinement_quality import check_refinement, gate_10


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


if __name__ == "__main__":
    test_single_refinement_contract_passes_and_blocks_placeholders()
    test_batch_gate_blocks_repeated_model_text()
    print("ok")
