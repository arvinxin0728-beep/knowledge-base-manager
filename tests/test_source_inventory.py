#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kbm.application.source_inventory import RefinementCatalog, audit_sources, normalized_source_name


def make_config(root: Path) -> dict:
    source = root / "sources"
    refinement = root / "kb" / "10-refinements"
    active = root / "kb" / "00-system" / "active"
    source.mkdir(parents=True)
    refinement.mkdir(parents=True)
    active.mkdir(parents=True)
    return {
        "ai_knowledge_base": str(root / "kb"),
        "source_libraries": {"articles": str(source)},
        "mapping": {"system": "00-system", "source_refinements": "10-refinements"},
    }


def test_inventory_rejects_temporary_output_and_recovers_unique_renamed_refinement() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        cfg = make_config(root)
        source = root / "sources" / "研究“高替”方法.md"
        source.write_text("source", encoding="utf-8")
        refinement = root / "kb" / "10-refinements" / "2026-08-09 renamed.md"
        refinement.write_text(
            "---\nstage: 来源精炼\nsource_file: " + str(root / "old" / "研究「高替」方法.md") + "\n---\n",
            encoding="utf-8",
        )
        index = root / "kb" / "00-system" / "active" / "processed-index.jsonl"
        index.write_text(json.dumps({"source_path": str(source), "output_file": "/private/tmp/ref.md"}) + "\n", encoding="utf-8")
        result = audit_sources(cfg)
        assert result["verified_processed_count"] == 1
        assert result["unprocessed_count"] == 0
        assert RefinementCatalog(cfg).resolve(source, {"output_file": "/private/tmp/ref.md"}) == refinement.resolve()


def test_inventory_keeps_ambiguous_refinement_unprocessed() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        cfg = make_config(root)
        source = root / "sources" / "same.md"
        source.write_text("source", encoding="utf-8")
        for index in range(2):
            (root / "kb" / "10-refinements" / f"ref-{index}.md").write_text(
                f"---\nstage: 来源精炼\nsource_file: /old-{index}/same.md\n---\n", encoding="utf-8"
            )
        ledger = root / "kb" / "00-system" / "active" / "processed-index.jsonl"
        ledger.write_text(json.dumps({"source_path": str(source), "output_file": "/missing.md"}) + "\n", encoding="utf-8")
        result = audit_sources(cfg)
        assert result["verified_processed_count"] == 0
        assert result["unprocessed_count"] == 1
        assert result["unprocessed"][0]["reason"] == "missing_or_ambiguous_refinement"


def test_source_identity_normalizes_unicode_punctuation() -> None:
    assert normalized_source_name("研究“高替”方法.md") == normalized_source_name("研究「高替」方法.md")
    assert normalized_source_name("2026-08-09 2026-07-24 2026-04-12 研究方法.md") == normalized_source_name("2026-04-12 研究方法.md")


def test_inventory_applies_instance_source_exclusions() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        cfg = make_config(root)
        sources = root / "sources"
        (sources / "article.md").write_text("source", encoding="utf-8")
        (sources / ".agents").mkdir()
        (sources / ".agents" / "SKILL.md").write_text("operations", encoding="utf-8")
        (sources / "library_2026-08-11.md").write_text("inventory", encoding="utf-8")
        cfg["pipeline"] = {"source_exclude_globs": [".agents/**", "library_*.md"]}
        result = audit_sources(cfg)
        assert result["source_count"] == 1
        assert result["unprocessed"][0]["path"] == str((sources / "article.md").resolve())


if __name__ == "__main__":
    test_inventory_rejects_temporary_output_and_recovers_unique_renamed_refinement()
    test_inventory_keeps_ambiguous_refinement_unprocessed()
    test_source_identity_normalizes_unicode_punctuation()
    test_inventory_applies_instance_source_exclusions()
    print("ok")
