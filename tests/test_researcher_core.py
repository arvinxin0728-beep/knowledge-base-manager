#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kbm.platform.config import load_config, validate_config
from kbm.platform.paths import db_path, local_runtime_dir, system_file


MANAGER = ROOT / "scripts" / "kb_manager.py"
PIPELINE = ROOT / "scripts" / "kb_pipeline.py"


def invoke_pipeline(config: Path, *args: str) -> dict:
    return json.loads(subprocess.check_output(["python3", str(PIPELINE), "--config", str(config), *args], text=True))


def test_legacy_config_becomes_an_implicit_researcher_without_file_migration() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        config = root / "legacy.json"
        original = {"name": "Legacy Knowledge Base", "version": 1, "source_libraries": {}, "ai_knowledge_base": str(root / "kb"), "mapping": {"system": "00-system", "source_refinements": "10", "topic_pages": "20", "reusable_assets": "30", "outputs": "40"}}
        config.write_text(json.dumps(original), encoding="utf-8")
        loaded = load_config(config)
        assert loaded["researcher"]["id"] == "legacy-knowledge-base"
        assert validate_config(loaded) == []
        assert "researcher" not in json.loads(config.read_text(encoding="utf-8"))
        assert local_runtime_dir(loaded).parent.name.startswith("legacy-knowledge-base-")


def test_legacy_config_with_non_ascii_name_keeps_a_stable_distinct_runtime_namespace() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        config = root / "legacy.json"
        original = {"name": "信封的知识管理", "version": 1, "source_libraries": {}, "ai_knowledge_base": str(root / "kb"), "mapping": {"system": "00-system", "source_refinements": "10", "topic_pages": "20", "reusable_assets": "30", "outputs": "40"}}
        config.write_text(json.dumps(original, ensure_ascii=False), encoding="utf-8")
        loaded = load_config(config)
        # The strict ASCII researcher.id used for identity/validation still collapses
        # a non-ASCII name to a generic placeholder ...
        assert loaded["researcher"]["id"] == "default-researcher"
        # ... but the runtime namespace used for on-disk state must not collapse the
        # same way, or two differently-named non-ASCII researchers would silently
        # collide/orphan each other's pipeline state.
        assert local_runtime_dir(loaded).parent.name.startswith("信封的知识管理-")


def test_explicit_researcher_contract_is_validated() -> None:
    cfg = {"version": 1, "source_libraries": {}, "ai_knowledge_base": "/tmp/kb", "mapping": {"system": "00", "source_refinements": "10", "topic_pages": "20", "reusable_assets": "30", "outputs": "40"}, "pipeline": {"runtime_storage": "local", "artifact_retention_days": 7}, "researcher": {"id": "Bad ID", "name": "", "domain": "", "role": "assistant", "isolation": "shared", "shared_methods": "all"}}
    fields = {item["field"] for item in validate_config(cfg)}
    assert {"researcher.id", "researcher.name", "researcher.domain", "researcher.role", "researcher.isolation", "researcher.shared_methods"} <= fields


def test_research_design_v2_dimensions_are_validated() -> None:
    cfg = {
        "version": 1, "source_libraries": {}, "ai_knowledge_base": "/tmp/kb",
        "mapping": {"system": "00", "source_refinements": "10", "topic_pages": "20", "reusable_assets": "30", "outputs": "40"},
        "pipeline": {"runtime_storage": "local", "artifact_retention_days": 7},
        "research_design": {
            "schema_version": 1, "preset": "unknown", "scope": {"theme": ""},
            "sources": ["unknown"], "process": "active-reading", "outputs": [],
        },
    }
    fields = {item["field"] for item in validate_config(cfg)}
    assert {
        "research_design.schema_version", "research_design.preset", "research_design.scope.theme",
        "research_design.sources", "research_design.process",
    } <= fields


def test_two_researchers_keep_runtime_state_and_system_files_isolated() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        previous = os.environ.get("KBM_RUNTIME_ROOT")
        os.environ["KBM_RUNTIME_ROOT"] = str(root / "runtime")
        try:
            configs = []
            for researcher_id in ("ai-researcher", "sales-researcher"):
                workspace = root / researcher_id
                sources = workspace / "sources"
                sources.mkdir(parents=True)
                (sources / "one.md").write_text(f"# {researcher_id}\n\n" + "Evidence. " * 50, encoding="utf-8")
                config = workspace / "config.json"
                config.write_text(json.dumps({
                    "name": researcher_id,
                    "version": 1,
                    "researcher": {"id": researcher_id, "name": researcher_id, "domain": researcher_id, "role": "researcher", "isolation": "independent_workspace", "shared_methods": []},
                    "source_libraries": {"articles": str(sources)},
                    "ai_knowledge_base": str(workspace / "kb"),
                    "mapping": {"system": "00-system", "source_refinements": "10", "topic_pages": "20", "reusable_assets": "30", "outputs": "40"},
                    "pipeline": {"runtime_storage": "local", "artifact_retention_days": 7},
                }), encoding="utf-8")
                configs.append(config)

            first, second = configs
            invoke_pipeline(first, "discover")
            invoke_pipeline(second, "discover")
            (first.parent / "sources" / "two.md").write_text("# Two\n\n" + "Evidence. " * 50, encoding="utf-8")
            invoke_pipeline(first, "discover")
            assert invoke_pipeline(first, "status")["total"] == 2
            assert invoke_pipeline(second, "status")["total"] == 1

            first_cfg, second_cfg = load_config(first), load_config(second)
            assert db_path(first_cfg) != db_path(second_cfg)
            assert db_path(first_cfg).is_file() and db_path(second_cfg).is_file()
            assert system_file(first_cfg, "processed-index.jsonl") != system_file(second_cfg, "processed-index.jsonl")
        finally:
            if previous is None:
                os.environ.pop("KBM_RUNTIME_ROOT", None)
            else:
                os.environ["KBM_RUNTIME_ROOT"] = previous


def test_init_writes_explicit_researcher_identity() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        config = root / "kb" / "00-system" / "kb-config.json"
        subprocess.check_output([
            "python3", str(MANAGER), "init", "--config", str(config),
            "--ai-knowledge-base", str(root / "kb"), "--name", "AI Lab",
            "--researcher-id", "ai-lab", "--research-domain", "AI systems", "--apply",
        ], text=True)
        written = json.loads(config.read_text(encoding="utf-8"))
        assert written["researcher"]["id"] == "ai-lab"
        assert written["researcher"]["domain"] == "AI systems"
        assert written["researcher"]["isolation"] == "independent_workspace"
        assert written["pipeline"]["runtime_namespace"] == "ai-lab"


if __name__ == "__main__":
    test_legacy_config_becomes_an_implicit_researcher_without_file_migration()
    test_explicit_researcher_contract_is_validated()
    test_two_researchers_keep_runtime_state_and_system_files_isolated()
    test_init_writes_explicit_researcher_identity()
    print("ok")
