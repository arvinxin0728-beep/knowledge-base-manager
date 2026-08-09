#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from kbm.application.source_index import (
    file_sha256,
    iter_sources,
    normalize_index_obj,
    read_processed,
    split_topics,
)


def make_config(root: Path) -> dict:
    return {
        "ai_knowledge_base": str(root / "kb"),
        "mapping": {"system": "00-system"},
        "source_libraries": {"articles": str(root / "sources")},
    }


def test_normalize_legacy_index_fields() -> None:
    normalized = normalize_index_obj({
        "source_file": "/tmp/legacy.md",
        "refinement_file": "/tmp/refined.md",
        "type": "公众号",
        "tags": "AI，知识管理; 写作",
    })
    assert normalized["source_type"] == "public_account_article"
    assert normalized["topics"] == ["AI", "知识管理", "写作"]
    assert normalized["title"] == "legacy"
    assert len(normalized["source_id"]) == 16


def test_source_discovery_filters_extensions_and_is_stable() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        source = root / "sources"
        source.mkdir()
        (source / "b.pdf").write_bytes(b"pdf")
        (source / "a.md").write_text("article", encoding="utf-8")
        (source / "ignored.png").write_bytes(b"image")
        found = iter_sources(make_config(root))
        assert [path.name for path in found] == ["a.md", "b.pdf"]
        assert file_sha256(source / "a.md") == file_sha256(source / "a.md")


def test_read_processed_normalizes_paths_and_hashes() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        cfg = make_config(root)
        active = root / "kb" / "00-system" / "active"
        active.mkdir(parents=True)
        source_path = root / "sources" / "one.md"
        row = {"source_file": str(source_path), "sha256": "abc", "tags": ["one"]}
        (active / "processed-index.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
        paths, hashes, count = read_processed(cfg)
        assert paths == {str(source_path.resolve())}
        assert hashes == {"abc"}
        assert count == 1


def test_split_topics_handles_empty_and_lists() -> None:
    assert split_topics(None) == []
    assert split_topics(["#one", "[[two]]", ""]) == ["one", "two"]
