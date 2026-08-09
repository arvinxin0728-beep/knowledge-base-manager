#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path

from kbm.domain.markdown import (
    clean_link_target, collect_markdown_files, extract_sections, markdown_title,
    split_frontmatter, wikilink_targets,
)


def test_markdown_primitives_preserve_legacy_contracts() -> None:
    text = """---
status: processed
topics:
  - AI
enabled: true
---
# Example

## 核心观点
First point.

## 关联知识
[[Topic|Alias]] and [[Other#Section]]
"""
    meta, body = split_frontmatter(text)
    assert meta == {"status": "processed", "topics": ["AI"], "enabled": True}
    assert extract_sections(body)["核心观点"] == "First point."
    assert markdown_title(Path("fallback.md"), text) == "Example"
    assert wikilink_targets(text) == ["Topic", "Other"]
    assert clean_link_target("Topic|Alias") == "Topic"


def test_markdown_collection_is_recursive_and_stable() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        (root / "b").mkdir()
        (root / "b" / "two.md").write_text("two", encoding="utf-8")
        (root / "one.md").write_text("one", encoding="utf-8")
        (root / "skip.txt").write_text("skip", encoding="utf-8")
        assert [path.name for path in collect_markdown_files(root)] == ["two.md", "one.md"]


if __name__ == "__main__":
    test_markdown_primitives_preserve_legacy_contracts()
    test_markdown_collection_is_recursive_and_stable()
    print("ok")
