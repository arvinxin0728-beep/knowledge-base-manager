#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEARCH = ROOT / "scripts" / "kb_search.py"


def search(config: Path, *args: str) -> dict:
    return json.loads(subprocess.check_output(["python3", str(SEARCH), "--config", str(config), *args], text=True))


def test_rebuild_and_query_return_layered_line_citations() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        kb = root / "kb"
        refinement = kb / "10-source-refinements" / "articles" / "pipeline.md"
        topic = kb / "20-topic-pages" / "pages" / "recovery.md"
        refinement.parent.mkdir(parents=True); topic.parent.mkdir(parents=True)
        refinement.write_text(
            "# Transactional Knowledge\n\n## Recovery\nA durable state ledger supports checkpoint recovery and idempotent commits.\n",
            encoding="utf-8",
        )
        topic.write_text(
            "# Reliable Processing\n\n## Decision\nLease expiry returns interrupted work to a recoverable queue.\n",
            encoding="utf-8",
        )
        config = root / "config.json"
        config.write_text(json.dumps({
            "version": 1, "name": "Search Test", "ai_knowledge_base": str(kb), "source_libraries": {},
            "mapping": {"system": "00-system", "source_refinements": "10-source-refinements", "topic_pages": "20-topic-pages", "reusable_assets": "30-reusable-assets", "outputs": "40-outputs"},
            "pipeline": {"runtime_storage": "legacy", "artifact_retention_days": 7},
        }), encoding="utf-8")
        preview = search(config, "rebuild")
        assert preview["applied"] is False and preview["artifacts"] == 2
        assert not Path(preview["database"]).exists()
        built = search(config, "rebuild", "--apply")
        assert built["chunks"] >= 2
        result = search(config, "query", "--query", "checkpoint recovery", "--limit", "5")
        assert result["engine"] == "lexical-v1" and result["result_count"] >= 1
        first = result["results"][0]
        assert first["layer"] == "source_refinement"
        assert first["citation"]["relative_path"].startswith("10-source-refinements/")
        assert first["citation"]["start_line"] <= first["citation"]["end_line"]
        assert "checkpoint recovery" in first["snippet"].lower()


def test_query_can_be_limited_to_one_knowledge_layer() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw); kb = root / "kb"; output = kb / "40-outputs" / "answer.md"
        output.parent.mkdir(parents=True)
        output.write_text("# Answer\n\nEvidence citation is required for durable answers.\n", encoding="utf-8")
        config = root / "config.json"
        config.write_text(json.dumps({
            "version": 1, "name": "Layer Test", "ai_knowledge_base": str(kb), "source_libraries": {},
            "mapping": {"system": "00", "source_refinements": "10", "topic_pages": "20", "reusable_assets": "30", "outputs": "40-outputs"},
            "pipeline": {"runtime_storage": "legacy", "artifact_retention_days": 7},
        }), encoding="utf-8")
        search(config, "rebuild", "--apply")
        assert search(config, "query", "--query", "evidence citation", "--layer", "output")["result_count"] == 1
        assert search(config, "query", "--query", "evidence citation", "--layer", "topic_page")["result_count"] == 0


def test_frontmatter_links_do_not_pollute_ranking_or_snippets() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw); kb = root / "kb"; notes = kb / "10"; notes.mkdir(parents=True)
        (notes / "irrelevant.md").write_text(
            "---\nrelated_topics:\n  - personal knowledge recovery\n---\n# Cash Register\n\nRestaurant payment operations.\n",
            encoding="utf-8",
        )
        (notes / "relevant.md").write_text(
            "---\ntags: [research]\n---\n# Recovery\n\nPersonal knowledge recovery requires durable checkpoints.\n",
            encoding="utf-8",
        )
        config = root / "config.json"
        config.write_text(json.dumps({
            "version": 1, "name": "Frontmatter Test", "ai_knowledge_base": str(kb), "source_libraries": {},
            "mapping": {"system": "00", "source_refinements": "10", "topic_pages": "20", "reusable_assets": "30", "outputs": "40"},
            "pipeline": {"runtime_storage": "legacy", "artifact_retention_days": 7},
        }), encoding="utf-8")
        search(config, "rebuild", "--apply")
        result = search(config, "query", "--query", "personal knowledge recovery")
        assert result["result_count"] == 1
        assert result["results"][0]["title"] == "Recovery"
        assert result["results"][0]["citation"]["start_line"] == 4
        assert result["results"][0]["citation"]["end_line"] >= result["results"][0]["citation"]["start_line"]
        assert "related_topics" not in result["results"][0]["snippet"]


def test_navigation_sections_rank_below_substantive_content() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw); kb = root / "kb"; notes = kb / "10"; notes.mkdir(parents=True)
        (notes / "openclaw.md").write_text(
            "# OpenClaw Knowledge Base\n\n## Core analysis\nOpenClaw knowledge base design keeps evidence traceable.\n\n"
            "## Related outputs\nOpenClaw knowledge base knowledge base knowledge base links.\n",
            encoding="utf-8",
        )
        (notes / "generic.md").write_text(
            "# Generic Knowledge Base\n\n## Core analysis\nKnowledge base knowledge base knowledge base design.\n",
            encoding="utf-8",
        )
        config = root / "config.json"
        config.write_text(json.dumps({
            "version": 1, "name": "Navigation Test", "ai_knowledge_base": str(kb), "source_libraries": {},
            "mapping": {"system": "00", "source_refinements": "10", "topic_pages": "20", "reusable_assets": "30", "outputs": "40"},
            "pipeline": {"runtime_storage": "legacy", "artifact_retention_days": 7},
        }), encoding="utf-8")
        search(config, "rebuild", "--apply")
        result = search(config, "query", "--query", "OpenClaw knowledge base")
        assert result["results"][0]["heading"] == "Core analysis"
        assert all("openclaw" in item["title"].lower() or "openclaw" in item["snippet"].lower() for item in result["results"])
