#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kbm.application.promotion import artifact_candidates, cluster_rows, load_cluster_rules
from kbm.domain.naming import path_slug, safe_stem


def test_portable_rules_resolve_from_the_skill_root() -> None:
    rules = load_cluster_rules(None)
    assert isinstance(rules.get("clusters"), list)


def test_auto_cluster_preserves_five_dimension_scoring_and_candidates() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        rows = []
        for index in range(3):
            note = root / f"{index}.md"
            note.write_text("\n".join([
                "1. 这是一个长度足够的核心观点，用于证明来源精炼不是空洞模板并支持主题晋升判断，同时保留来源证据和使用边界。",
                "2. 第二个核心观点同样包含具体内容，使质量权重可以识别这是一份相对丰富的来源精炼，而不是机械填充的短句。",
                "3. 第三个核心观点用于满足丰富度阈值，并验证迁移前后的五维评分保持一致，同时覆盖实际输出场景和限制条件。",
            ]), encoding="utf-8")
            rows.append({
                "source_id": f"s{index}", "title": f"Source {index}",
                "source_type": "article", "source_path": str(note),
                "output_file": str(note), "topics": ["研究工作流", "输出"],
            })
        clusters = cluster_rows(rows, {"default_min_sources": 3, "clusters": []})
        target = next(item for item in clusters if item["name"] == "研究工作流")
        assert target["score"] == 4
        assert target["action"] == "topic_page_and_asset"
        assert [item["artifact_type"] for item in artifact_candidates(target)] == ["topic_page"]


def test_safe_stem_remains_portable_after_domain_extraction() -> None:
    assert safe_stem(' A/B: C? ') == "ABC"
    assert safe_stem("   ") == "untitled"


def test_path_slug_keeps_ascii_names_backward_compatible() -> None:
    assert path_slug("xiaowang-knowledge-base") == "xiaowang-knowledge-base"
    assert path_slug("Legacy Knowledge Base") == "legacy-knowledge-base"
    assert path_slug("   ") == "default-researcher"


def test_path_slug_preserves_non_ascii_researcher_names() -> None:
    assert path_slug("信封的知识管理") == "信封的知识管理"
    # Two distinct non-ASCII names must not collapse to the same namespace.
    assert path_slug("客如云知识库") != path_slug("信封的知识管理")
    # Filesystem-unsafe characters are still stripped/replaced.
    assert path_slug("信封/知识:管理") == "信封-知识-管理"


if __name__ == "__main__":
    test_portable_rules_resolve_from_the_skill_root()
    test_auto_cluster_preserves_five_dimension_scoring_and_candidates()
    test_safe_stem_remains_portable_after_domain_extraction()
    test_path_slug_keeps_ascii_names_backward_compatible()
    test_path_slug_preserves_non_ascii_researcher_names()
    print("ok")
