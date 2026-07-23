#!/usr/bin/env python3
from __future__ import annotations

import json
import importlib.util
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "kb_manager.py"
LINKER = ROOT / "scripts" / "obsidian_linker.py"
EBOOK_PROBE = ROOT / "scripts" / "ebook_probe.py"
OFFICIAL_ACCOUNT = ROOT / "scripts" / "official_account_library.rb"
FIXTURE = ROOT / "tests" / "fixtures" / "minimal-kb"

SPEC = importlib.util.spec_from_file_location("kb_manager", SCRIPT)
assert SPEC and SPEC.loader
KBM = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(KBM)

def make_case() -> tuple[tempfile.TemporaryDirectory, Path]:
    tmp = tempfile.TemporaryDirectory()
    dst = Path(tmp.name) / "minimal-kb"
    shutil.copytree(FIXTURE, dst)
    config = dst / "config.json"
    cfg = json.loads(config.read_text(encoding="utf-8"))
    cfg["source_libraries"]["public_accounts"] = str(dst / "Sources" / "Public-Accounts")
    cfg["ai_knowledge_base"] = str(dst / "AI-Knowledge-Base")
    cfg.setdefault("promotion_rules", {})["cluster_rules"] = str(ROOT / "examples" / "profiles" / "8xx" / "cluster-rules.json")
    config.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return tmp, config

def run(*args: str) -> dict:
    out = subprocess.check_output(["python3", str(SCRIPT), *args], text=True)
    return json.loads(out)

def test_normalize_index_preview() -> None:
    tmp, config = make_case()
    try:
        result = run("normalize-index", "--config", str(config))
        assert result["input_rows"] == 3
        rows = result["preview_rows"]
    finally:
        tmp.cleanup()
    assert rows[0]["source_path"] == "/tmp/a.md"
    assert rows[0]["source_type"] == "public_account_article"
    assert rows[2]["topics"] == ["个人知识库", "研究工作流"]

def test_promote_preview() -> None:
    tmp, config = make_case()
    try:
        result = run("promote", "--config", str(config))
        clusters = result["clusters"]
        assert clusters
        first = clusters[0]
        assert first["score"] >= 4
        assert first["source_count"] == 3
    finally:
        tmp.cleanup()

def test_create_stubs_writes_only_system_stub_area() -> None:
    tmp, config = make_case()
    try:
        result = run("promote", "--config", str(config), "--apply", "--create-stubs")
        assert result["stub_artifacts"]
        assert all("/00-system/stubs/" in path for path in result["stub_artifacts"])
        cfg = json.loads(config.read_text(encoding="utf-8"))
        kb = Path(cfg["ai_knowledge_base"])
        assert not list((kb / "20-topic-pages" / "pages").glob("*AI*.md"))
        assert not list((kb / "30-reusable-assets").rglob("*-asset.md"))
        assert not list((kb / "40-outputs").rglob("*-output.md"))
    finally:
        tmp.cleanup()

def test_output_evaluation_preview() -> None:
    tmp, config = make_case()
    try:
        result = run("evaluate-outputs", "--config", str(config))
        assert result["outputs"] == 1
        assert result["results"][0]["score"] >= 4
    finally:
        tmp.cleanup()

def test_zero_source_predefined_cluster_is_not_emitted() -> None:
    rules = {
        "default_min_sources": 3,
        "clusters": [{
            "id": "preset",
            "name": "Preset",
            "question": "What is supported?",
            "asset_type": "methods",
            "output_type": "feynman",
            "risk": "medium",
            "keywords": ["preset"],
        }],
    }
    assert KBM.cluster_rows([], rules) == []

def test_insufficient_evidence_is_candidate_only() -> None:
    rows = [KBM.normalize_index_obj({"title": "One", "source_path": "/tmp/one.md", "topics": ["Sparse"]})]
    rules = {"default_min_sources": 3, "clusters": []}
    cluster = KBM.build_cluster({"id": "sparse", "name": "Sparse", "question": "Q?", "asset_type": "methods", "output_type": "feynman"}, rows, rules)
    assert cluster["action"] == "candidate_only"
    assert "insufficient_sources" in cluster["non_promotion_reason"]

def test_nested_defaults_and_path_validation() -> None:
    cfg = KBM.deep_defaults({"ai_knowledge_base": "/tmp/kb", "mapping": {"system": "system"}}, KBM.config_defaults())
    assert cfg["mapping"]["outputs"] == "40-outputs"
    assert KBM.validate_config(cfg) == []
    cfg["mapping"]["outputs"] = "../outside"
    assert any(e["field"] == "mapping.outputs" for e in KBM.validate_config(cfg))

def test_run_preview_and_config_validation() -> None:
    tmp, config = make_case()
    try:
        assert run("validate-config", "--config", str(config))["valid"] is True
        result = run("run", "--config", str(config))
        assert result["apply"] is False
        assert result["outputs_evaluated"] == 1
        assert "quality_gate_passed" in result
        assert result["written"] == []
    finally:
        tmp.cleanup()

def test_package_lint_requires_current_chinese_readme() -> None:
    result = run("package-lint", "--strict")
    assert result["passed"] is True
    assert result["issue_count"] == 0

def test_obsidian_without_taxonomy_keeps_unclassified() -> None:
    tmp, config = make_case()
    try:
        cfg = json.loads(config.read_text(encoding="utf-8"))
        cfg["integrations"] = {"obsidian": {"enabled": True}}
        config.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        topic = Path(cfg["ai_knowledge_base"]) / "20-topic-pages" / "pages" / "Photography.md"
        topic.parent.mkdir(parents=True, exist_ok=True)
        topic.write_text("# Photography\n\nA topic unrelated to configured taxonomies.\n", encoding="utf-8")
        subprocess.check_output(["python3", str(LINKER), "--config", str(config), "--apply"], text=True)
        updated = topic.read_text(encoding="utf-8")
        assert 'theme_cluster: "unclassified"' in updated
        moc_dir = Path(cfg["ai_knowledge_base"]) / "20-topic-pages" / "moc"
        assert not list(moc_dir.glob("*-MOC.md"))
    finally:
        tmp.cleanup()

def test_run_apply_is_repeatable() -> None:
    tmp, config = make_case()
    try:
        first = run("run", "--config", str(config), "--apply")
        tracked = [Path(p) for p in first["written"] if p.endswith((".md", ".jsonl"))]
        before = {p: p.read_bytes() for p in tracked}
        second = run("run", "--config", str(config), "--apply")
        after = {p: p.read_bytes() for p in tracked}
        assert second["apply"] is True
        assert before == after
        cfg = json.loads(config.read_text(encoding="utf-8"))
        decision_log = Path(cfg["ai_knowledge_base"]) / "00-system" / "active" / "promotion-decision.jsonl"
        assert decision_log.exists()
        assert len(decision_log.read_text(encoding="utf-8").splitlines()) == len(set(decision_log.read_text(encoding="utf-8").splitlines()))
    finally:
        tmp.cleanup()

def test_portability_audit_detects_private_implementation_leakage() -> None:
    tmp, config = make_case()
    try:
        cfg = json.loads(config.read_text(encoding="utf-8"))
        asset = Path(cfg["ai_knowledge_base"]) / "30-reusable-assets" / "methods" / "private.md"
        asset.parent.mkdir(parents=True, exist_ok=True)
        asset.write_text("---\nstage: reusable-asset\nstatus: active\nasset_type: diagnostic-checklist\nrelated_topics:\n  - \"[[Personal Knowledge Base]]\"\ntheme_cluster: test\n---\n\n# Private\n\nThis method tells users to inspect /Users/example/Desktop and 20/30/40 folders.\n", encoding="utf-8")
        result = run("audit-portability", "--config", str(config))
        assert result["issue_count"] >= 1
        assert any(item["issue"] == "absolute_or_private_path" for item in result["issues"])
    finally:
        tmp.cleanup()

def test_topic_page_audit_rejects_process_only_split_page() -> None:
    tmp, config = make_case()
    try:
        cfg = json.loads(config.read_text(encoding="utf-8"))
        topic = Path(cfg["ai_knowledge_base"]) / "20-topic-pages" / "pages" / "split.md"
        topic.parent.mkdir(parents=True, exist_ok=True)
        topic.write_text("---\nstage: topic_page\nstatus: active\n---\n\n# Split\n\n## Topic Question\nQ\n\n从原来的 AI 知识管理拆出。\n", encoding="utf-8")
        result = run("audit-topic-pages", "--config", str(config))
        assert result["issue_count"] >= 1
        assert any(item["issue"] == "split_process_in_body" for item in result["issues"])
    finally:
        tmp.cleanup()

def test_quality_gate_blocks_unresolved_links_and_bad_outputs() -> None:
    tmp, config = make_case()
    try:
        cfg = json.loads(config.read_text(encoding="utf-8"))
        output = Path(cfg["ai_knowledge_base"]) / "40-outputs" / "feynman-explanations" / "bad.md"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("---\nstage: output\nstatus: draft\nsource_theme: test\nfact_check_required: false\nrelated_topics:\n  - \"[[Missing Topic]]\"\n---\n\n# Bad\n\n## Audience\nReader\n\n## Core Message\nShort.\n\nTBD\n", encoding="utf-8")
        result = run("quality-gate", "--config", str(config))
        assert result["passed"] is False
        gates = {item["gate"] for item in result["blockers"]}
        assert "relations" in gates or "output_quality" in gates
    finally:
        tmp.cleanup()

def test_verification_result_resolves_output_verification_blocker() -> None:
    tmp, config = make_case()
    try:
        cfg = json.loads(config.read_text(encoding="utf-8"))
        output = Path(cfg["ai_knowledge_base"]) / "40-outputs" / "feynman-explanations" / "risky.md"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("---\nstage: output\nstatus: active\nsource_theme: test\nfact_check_required: true\nrelated_topics:\n  - \"[[Personal Knowledge Base]]\"\nrelated_assets:\n  - \"[[Knowledge Workflow Asset]]\"\n---\n\n# Risky\n\n## Audience\nReader\n\n## Core Message\nThis output cites market data.\n\n## Evidence\nBased on a source refinement and market data.\n\n## Scope\nUse only after verification.\n\n" + "Market data needs verification. " * 20, encoding="utf-8")
        queue = run("verification-queue", "--config", str(config))
        item = next(x for x in queue["queue"] if x["file"].endswith("risky.md"))
        blocked = run("quality-gate", "--config", str(config))
        assert blocked["passed"] is False
        assert any(x["gate"] == "verification" for x in blocked["blockers"])
        run("verify-claim", "--config", str(config), "--id", item["id"], "--status", "verified", "--claim", "market data", "--evidence", "https://example.test/source", "--note", "fixture evidence")
        status = run("verification-status", "--config", str(config))
        resolved = next(x for x in status["items"] if x["id"] == item["id"])
        assert resolved["status"] == "verified"
        assert resolved["verification"]["evidence_url_or_path"] == "https://example.test/source"
    finally:
        tmp.cleanup()

def test_record_output_review_can_block_quality_gate() -> None:
    tmp, config = make_case()
    try:
        cfg = json.loads(config.read_text(encoding="utf-8"))
        rel = "40-outputs/feynman-explanations/sample.md"
        result = run("record-output-review", "--config", str(config), "--file", rel, "--status", "needs_revision", "--scores", "{\"argument_clarity\":2,\"evidence_strength\":2}", "--note", "needs stronger evidence")
        assert result["blocking_review_count"] >= 1
        gate = run("quality-gate", "--config", str(config))
        assert any(item["gate"] == "output_review" for item in gate["blockers"])
    finally:
        tmp.cleanup()

def test_package_lint_passes_clean_skill_package() -> None:
    result = run("package-lint")
    assert result["passed"] is True

def test_init_creates_configured_source_and_empty_run_requests_sources() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        config = root / "kb" / "00-system" / "kb-config.json"
        kb = root / "kb"
        articles = root / "sources" / "articles"
        subprocess.check_output(["python3", str(SCRIPT), "init", "--config", str(config), "--ai-knowledge-base", str(kb), "--articles", str(articles), "--apply"], text=True)
        assert articles.is_dir()
        assert run("doctor", "--config", str(config))["healthy"] is True
        assert run("run", "--config", str(config))["next_action"] == "add_sources"

def test_output_with_tbd_is_not_usable() -> None:
    with tempfile.TemporaryDirectory() as raw:
        base = Path(raw)
        output = base / "draft.md"
        output.write_text("---\nsource_theme: x\nfact_check_required: false\n---\n\n## Audience\nReader\n\n## Core Message\n" + "Useful text. " * 30 + "\n\nTBD\n", encoding="utf-8")
        result = KBM.evaluate_output_file(base, output)
        assert result["checks"]["no_placeholders"] is False
        assert result["status"] == "needs_revision"

def test_ebook_probe_text_smoke() -> None:
    with tempfile.TemporaryDirectory() as raw:
        base = Path(raw)
        book = base / "book.md"
        out = base / "out"
        book.write_text("# Chapter One\n\n" + "Knowledge systems need evidence. " * 50, encoding="utf-8")
        result = json.loads(subprocess.check_output(["python3", str(EBOOK_PROBE), str(book), "--out-dir", str(out)], text=True))
        assert result["chunks"] >= 1
        assert (out / "manifest.json").exists()

def test_official_account_dedupe_uses_quarantine() -> None:
    with tempfile.TemporaryDirectory() as raw:
        base = Path(raw) / "sync"
        target = base / "公众号原始文章"
        quarantine = Path(raw) / "quarantine"
        target.mkdir(parents=True)
        (target / "2026-01-01 Article.md").write_text("same", encoding="utf-8")
        (target / "2026-01-01 Article 1.md").write_text("same", encoding="utf-8")
        preview = subprocess.check_output(["ruby", str(OFFICIAL_ACCOUNT), "dedupe", "--base", str(base)], text=True)
        assert "duplicate_extras=1" in preview
        subprocess.check_output(["ruby", str(OFFICIAL_ACCOUNT), "dedupe", "--base", str(base), "--apply", "--quarantine", str(quarantine)], text=True)
        assert len(list(target.glob("*.md"))) == 1
        assert len(list(quarantine.glob("*.md"))) == 1

if __name__ == "__main__":
    test_normalize_index_preview()
    test_promote_preview()
    test_create_stubs_writes_only_system_stub_area()
    test_output_evaluation_preview()
    test_zero_source_predefined_cluster_is_not_emitted()
    test_insufficient_evidence_is_candidate_only()
    test_nested_defaults_and_path_validation()
    test_run_preview_and_config_validation()
    test_package_lint_requires_current_chinese_readme()
    test_obsidian_without_taxonomy_keeps_unclassified()
    test_run_apply_is_repeatable()
    test_portability_audit_detects_private_implementation_leakage()
    test_topic_page_audit_rejects_process_only_split_page()
    test_quality_gate_blocks_unresolved_links_and_bad_outputs()
    test_verification_result_resolves_output_verification_blocker()
    test_record_output_review_can_block_quality_gate()
    test_package_lint_passes_clean_skill_package()
    test_init_creates_configured_source_and_empty_run_requests_sources()
    test_output_with_tbd_is_not_usable()
    test_ebook_probe_text_smoke()
    test_official_account_dedupe_uses_quarantine()
    print("ok")
