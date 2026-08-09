#!/usr/bin/env python3
"""Deterministic helpers for mapped AI knowledge-base systems."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kbm.domain.researcher import slug
from kbm.domain.naming import safe_stem
from kbm.domain.markdown import (
    clean_link_target, collect_markdown_files, extract_sections, markdown_title,
    split_frontmatter, wikilink_targets,
)
from kbm.application.package_release import (
    package_lint as lint_release_package,
    refresh_source_hash,
    source_content_hash as _source_content_hash,
    tracked_package_files as _tracked_files_for_root,
)
from kbm.application.refinement_quality import (
    BOILERPLATE_TOPICS_DEFAULT, KNOWN_TEMPLATE_PATTERNS, check_refinement,
    gate_10, render_gate_10,
)
from kbm.application.promotion import (
    artifact_candidates, build_cluster, cluster_rows, load_cluster_rules,
    non_promotion_reason, render_asset_output_candidates,
    render_promotion_review, render_topic_clusters, source_matches_cluster,
)
from kbm.application.promotion_runtime import (
    append_promotion_decisions, promotion_decision_rows, render_asset_stub,
    render_output_stub, render_topic_stub, subdir_for_asset, subdir_for_output,
    write_run_checkpoint, write_stub_artifacts,
)
from kbm.application.source_verification import (
    HIGH_RISK_PATTERNS, VALID_VERIFICATION_STATUSES,
    append_verification_result, classify_source_quality, has_high_risk,
    latest_verification_results, render_source_quality_audit,
    render_verification_status, risk_signals, source_quality_audit,
    verification_items, verification_result_row, verification_status,
)
from kbm.application.source_inventory import audit_sources
from kbm.application.evidence_intake import (
    evidence_intake_audit, evidence_intake_expected_dirs, evidence_intake_root,
    init_evidence_intake as _init_evidence_intake,
    render_evidence_intake_audit, render_source_capabilities,
    system_evidence_refinement_root,
)
from kbm.platform.config import (
    DEFAULT_MAPPING, DEFAULT_OUTPUT_SUBDIRS, DEFAULT_REUSABLE_ASSET_SUBDIRS,
    DEFAULT_SOURCE_SUBDIRS, DEFAULT_TOPIC_PAGE_SUBDIRS, config_defaults,
    deep_defaults, load_config, require_valid_config, validate_config, write_config,
)
from kbm.platform.paths import kb_path, system_file, topic_pages_content_dir, topic_pages_moc_dir
from kbm.platform.storage import append_operation_log, backup_file
from kbm.platform.clock import now_iso
from kbm.platform.jsonl import read_jsonl_objects as read_index_objects, write_jsonl
from kbm.platform.dates import parse_date as _parse_date

SOURCE_EXTS = {".md", ".markdown", ".txt", ".html", ".htm", ".pdf", ".epub", ".docx"}
SKILL_ROOT = Path(__file__).resolve().parents[1]
def _tracked_package_files() -> list[Path]:
    """Compatibility wrapper for callers that import the legacy script."""
    return _tracked_files_for_root(SKILL_ROOT)


INDEX_FIELDS = [
    "schema_version",
    "source_id",
    "source_path",
    "source_sha256",
    "source_type",
    "title",
    "processed_at",
    "output_file",
    "topics",
    "status",
    "fact_risk",
    "fact_check_required",
]
SOURCE_TYPE_ALIASES = {
    "公众号": "public_account_article",
    "public_account": "public_account_article",
    "public_accounts": "public_account_article",
    "public_account_article": "public_account_article",
    "wechat": "public_account_article",
    "wechat_article": "public_account_article",
    "电子书": "ebook",
    "book": "ebook",
    "ebook": "ebook",
    "article": "article",
    "web": "web_article",
    "webpage": "web_article",
    "web_article": "web_article",
}



LIFECYCLE_STATUSES = {
    "candidate", "draft", "active", "needs_revision", "needs_evidence",
    "parked", "superseded", "deprecated", "archived",
}
HEALTH_STATUSES = {
    "healthy", "review_due", "stale", "weak_evidence", "conflicted",
    "low_reuse", "deprecated",
}


def ensure_system_files(cfg: dict[str, Any]) -> None:
    system = kb_path(cfg, "system")
    system.mkdir(parents=True, exist_ok=True)
    (system / "active").mkdir(parents=True, exist_ok=True)
    (system / "reports").mkdir(parents=True, exist_ok=True)
    (system / "backups").mkdir(parents=True, exist_ok=True)
    defaults = {
        "processed-index.jsonl": "",
        "topics.md": "# Topic Index\n\n## Current topic candidates\n\n",
        "topic-clusters.md": "# Topic Clusters\n\n",
        "promotion-review.md": "# Promotion Review\n\n",
        "promotion-decision.jsonl": "",
        "asset-output-candidates.md": "# Asset and Output Candidates\n\n",
        "asset-relation-audit.md": "# Asset Relation Audit\n\n",
        "relation-audit.md": "# Relation Audit\n\n",
        "portability-audit.md": "# Portability Audit\n\n",
        "topic-page-audit.md": "# Topic Page Audit\n\n",
        "quality-gate.md": "# Quality Gate\n\n",
        "run-log.jsonl": "",
        "verification-queue.jsonl": "",
        "verification-results.jsonl": "",
        "verification-status.md": "# Verification Status\n\n",
        "output-quality-review.md": "# Output Quality Review\n\n",
        "output-review-results.jsonl": "",
        "output-review-status.md": "# Output Review Status\n\n",
        "evidence-fill-ledger.jsonl": "",
        "editorial-quality-review.md": "# Editorial Quality Review\n\n",
        "evidence-intake-audit.md": "# Evidence Intake Audit\n\n",
        "source-capabilities.md": "# Source Capabilities\n\n",
        "inbox-review.md": "# Inbox Review\n\n",
        "rules.md": (
            "# Knowledge Base Rules\n\n"
            "This knowledge base stores understood, compressed, structured, and reusable knowledge. "
            "It is not a raw-source archive.\n\n"
            "## Boundaries\n\n"
            "- Raw sources stay in source libraries.\n"
            "- Source refinements explain one source.\n"
            "- Topic pages synthesize multiple sources around a question.\n"
            "- Reusable assets extract methods, cases, expressions, and frameworks.\n"
            "- Outputs serve explicit readers, tasks, and scenarios.\n"
        ),
    }
    for name, content in defaults.items():
        p = system_file(cfg, name)
        if not p.exists():
            p.write_text(content, encoding="utf-8")


def ensure_tree(cfg: dict[str, Any]) -> None:
    base = Path(cfg["ai_knowledge_base"])
    for raw in cfg.get("source_libraries", {}).values():
        if raw:
            Path(raw).expanduser().mkdir(parents=True, exist_ok=True)
    for key in ["system", "source_refinements", "topic_pages", "reusable_assets", "outputs"]:
        (base / cfg["mapping"][key]).mkdir(parents=True, exist_ok=True)
    for sub in cfg.get("source_refinement_subdirs", {}).values():
        (kb_path(cfg, "source_refinements") / sub).mkdir(parents=True, exist_ok=True)
    for sub in cfg.get("topic_page_subdirs", {}).values():
        (kb_path(cfg, "topic_pages") / sub).mkdir(parents=True, exist_ok=True)
    reusable = kb_path(cfg, "reusable_assets")
    for sub in cfg.get("reusable_asset_subdirs", {}).values():
        (reusable / sub).mkdir(parents=True, exist_ok=True)
    for sub in cfg.get("output_subdirs", {}).values():
        (kb_path(cfg, "outputs") / sub).mkdir(parents=True, exist_ok=True)
    ensure_system_files(cfg)


def init_evidence_intake(cfg: dict[str, Any], apply: bool = False) -> dict[str, Any]:
    return _init_evidence_intake(cfg, apply=apply, prepare_system=ensure_system_files)


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def split_topics(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip(" #[]") for v in value if str(v).strip(" #[]")]
    text = str(value)
    text = text.replace("，", ",").replace("、", ",").replace(";", ",")
    return [part.strip(" #[]") for part in text.split(",") if part.strip(" #[]")]


def normalize_source_type(value: Any) -> str:
    raw = str(value or "").strip()
    return SOURCE_TYPE_ALIASES.get(raw, raw or "unknown")


def stable_source_id(obj: dict[str, Any]) -> str:
    raw = obj.get("source_sha256") or obj.get("source_path") or obj.get("output_file") or obj.get("title") or json.dumps(obj, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(str(raw).encode("utf-8")).hexdigest()[:16]


def normalize_index_obj(obj: dict[str, Any]) -> dict[str, Any]:
    source_path = obj.get("source_path") or obj.get("source_file") or obj.get("file") or ""
    output_file = obj.get("output_file") or obj.get("refinement_file") or obj.get("note_path") or ""
    title = obj.get("title") or (Path(source_path).stem if source_path else Path(output_file).stem if output_file else "")
    normalized = {
        "schema_version": int(obj.get("schema_version") or 1),
        "source_id": obj.get("source_id") or "",
        "source_path": str(source_path),
        "source_sha256": obj.get("source_sha256") or obj.get("sha256") or "",
        "source_type": normalize_source_type(obj.get("source_type") or obj.get("type")),
        "title": str(title),
        "processed_at": obj.get("processed_at") or obj.get("created_at") or "",
        "output_file": str(output_file),
        "topics": split_topics(obj.get("topics") or obj.get("tags") or obj.get("connected_topics")),
        "status": obj.get("status") or "processed",
        "fact_risk": obj.get("fact_risk") or obj.get("risk") or "unknown",
        "fact_check_required": bool(obj.get("fact_check_required", False)),
    }
    normalized["source_id"] = normalized["source_id"] or stable_source_id(normalized)
    return normalized


def read_processed(cfg: dict[str, Any]) -> tuple[set[str], set[str], int]:
    index = system_file(cfg, "processed-index.jsonl")
    paths: set[str] = set()
    hashes: set[str] = set()
    count = 0
    rows, _errors = read_index_objects(index)
    for obj in rows:
        count += 1
        norm = normalize_index_obj(obj)
        if norm.get("source_path"):
            paths.add(str(Path(norm["source_path"]).expanduser().resolve()))
        if norm.get("source_sha256"):
            hashes.add(norm["source_sha256"])
    return paths, hashes, count


def iter_sources(cfg: dict[str, Any]) -> list[Path]:
    files: list[Path] = []
    for raw in cfg.get("source_libraries", {}).values():
        if not raw:
            continue
        root = Path(raw)
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if p.is_file() and p.suffix.lower() in SOURCE_EXTS:
                files.append(p.resolve())
    return sorted(files, key=lambda p: str(p))


def audit(cfg: dict[str, Any], include_hashes: bool = False) -> dict[str, Any]:
    return audit_sources(cfg, include_hashes=include_hashes)






def _section_text(body: str, heading: str) -> str:
    pattern = rf"(?ms)^##\s+{re.escape(heading)}\s*$\n(.*?)(?=^##\s+|\Z)"
    match = re.search(pattern, body)
    return match.group(1).strip() if match else ""


def _has_subheading(body: str, heading: str) -> bool:
    return bool(re.search(rf"(?m)^###\s+{re.escape(heading)}\s*$", body))


def _zh_char_count(text: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", text))


def _article_maturity(text: str, body: str) -> tuple[str, dict[str, bool]]:
    draft_body = _section_text(body, "正文草稿") or body
    zh_chars = _zh_char_count(draft_body)
    h3_count = len(re.findall(r"(?m)^###\s+", draft_body))
    has_hook = bool(re.search(r"开头|钩子|故事|场景|很多人|你有没有|为什么", draft_body))
    has_reader_problem = bool(re.search(r"读者问题|问题|困惑|痛点|为什么", text))
    has_examples = bool(re.search(r"案例|例子|比如|例如|场景|客户|团队", draft_body))
    has_counterpoint = bool(re.search(r"但是|反过来|误区|不是.*而是|真正的问题|矛盾", draft_body))
    has_actionable_end = bool(re.search(r"最后|所以|建议|下一步|你可以|行动|清单", draft_body[-800:]))
    has_fact_boundary = "fact_check_required" in text or "核查" in text or "事实边界" in text
    has_title_candidates = bool(_section_text(body, "标题候选"))
    editorial_card = _section_text(body, "发布编辑卡片")
    has_article_genre = _has_subheading(editorial_card, "文章体裁")
    has_publish_angle = (
        "publish_angle:" in text
        or bool(_section_text(body, "发布角度"))
        or _has_subheading(editorial_card, "选题切口")
        or _has_subheading(editorial_card, "选题角度")
    )
    has_key_scenes = (
        bool(_section_text(body, "关键场景"))
        or _has_subheading(editorial_card, "关键证据/素材")
        or _has_subheading(editorial_card, "关键素材")
    )
    memorable_lines = _section_text(body, "可复用金句")
    has_memorable_lines = len(re.findall(r"(?m)^-\s+", memorable_lines)) >= 5
    has_publish_fact_check = bool(_section_text(body, "发布前核查"))
    checks = {
        "article_body_1500_zh": zh_chars >= 1500,
        "article_body_2500_zh": zh_chars >= 2500,
        "article_3plus_sections": h3_count >= 3 or len(re.findall(r"(?m)^第[一二三四五六七八九十]+", draft_body)) >= 3,
        "article_4plus_sections": h3_count >= 4,
        "article_has_hook": has_hook,
        "article_has_reader_problem": has_reader_problem,
        "article_has_examples": has_examples,
        "article_has_counterpoint": has_counterpoint,
        "article_has_actionable_end": has_actionable_end,
        "article_has_fact_boundary": has_fact_boundary,
        "article_has_genre": has_article_genre,
        "article_has_title_candidates": has_title_candidates,
        "article_has_publish_angle": has_publish_angle,
        "article_has_key_scenes": has_key_scenes,
        "article_has_memorable_lines": has_memorable_lines,
        "article_has_publish_fact_check": has_publish_fact_check,
    }
    if (
        checks["article_body_2500_zh"]
        and checks["article_4plus_sections"]
        and has_hook
        and has_reader_problem
        and has_examples
        and has_counterpoint
        and has_actionable_end
        and has_fact_boundary
        and has_article_genre
        and has_title_candidates
        and has_publish_angle
        and has_key_scenes
        and has_memorable_lines
        and has_publish_fact_check
    ):
        return "publishable_draft", checks
    if checks["article_body_1500_zh"] and checks["article_3plus_sections"] and has_reader_problem and has_examples and has_fact_boundary:
        return "article_draft", checks
    return "article_seed", checks


def evaluate_output_file(base: Path, p: Path) -> dict[str, Any]:
    text = p.read_text(encoding="utf-8", errors="ignore")
    body = re.sub(r"---.*?---", "", text, flags=re.S).strip()
    checks = {
        "has_source_theme": "source_theme:" in text,
        "has_audience_or_scenario": bool(re.search(r"## (Audience|读者|场景|目标|Audience / Scenario)", text, re.I)),
        "has_core_message": bool(re.search(r"(##|###) (Core Message|核心观点|核心论断|核心信息|主题问题)", text, re.I)),
        "has_fact_boundary": "fact_check_required" in text or "核查" in text or "Verification" in text,
        "has_evidence_boundary": bool(re.search(r"来源|证据|Supporting|Evidence|based on|基于", body, re.I)),
        "has_scope_or_limits": bool(re.search(r"边界|限制|不适用|uncertain|limits|scope|verification", body, re.I)),
        "not_empty_draft": len(body) > 250,
        "no_placeholders": not bool(re.search(r"\bTBD\b|待补充|TODO", text, re.I)),
    }
    article_maturity = None
    rel = str(p.relative_to(base))
    if "文章草稿" in rel or 'output_type: "文章草稿"' in text or "output_type: 文章草稿" in text:
        article_maturity, article_checks = _article_maturity(text, body)
        checks.update(article_checks)
    score = sum(1 for ok in checks.values() if ok)
    status = "usable" if score >= max(6, len(checks) - 1) and checks["no_placeholders"] else "needs_revision"
    if article_maturity == "article_seed":
        status = "needs_revision"
    elif article_maturity in {"article_draft", "publishable_draft"} and all(
        checks.get(key, False)
        for key in [
            "has_source_theme",
            "has_audience_or_scenario",
            "has_core_message",
            "has_fact_boundary",
            "has_evidence_boundary",
            "has_scope_or_limits",
            "not_empty_draft",
            "no_placeholders",
            "article_body_1500_zh",
            "article_3plus_sections",
            "article_has_reader_problem",
            "article_has_examples",
            "article_has_fact_boundary",
        ]
    ):
        status = "usable"
    return {"file": rel, "score": score, "status": status, "checks": checks, "article_maturity": article_maturity}


def render_output_quality(results: list[dict[str, Any]]) -> str:
    denominator = max((len(r["checks"]) for r in results), default=0)
    lines = ["# Output Quality Review", "", "---", f"updated_at: {date.today().isoformat()}", "stage: system", "status: active", "---", "", "## Summary", "", "| File | Score | Status |", "|---|---:|---|"]
    for r in results:
        lines.append(f"| `{r['file']}` | {r['score']}/{denominator} | {r['status']} |")
    lines += ["", "## Checks", ""]
    for r in results:
        lines.append(f"### {r['file']}")
        for key, ok in r["checks"].items():
            lines.append(f"- {key}: {'pass' if ok else 'fail'}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


EDITORIAL_DIMENSIONS = [
    "insight_density",
    "problem_sharpness",
    "argument_strength",
    "originality",
    "actionability",
    "expression_quality",
]


def _score_1_5(points: int, total: int) -> int:
    if total <= 0:
        return 1
    ratio = max(0, min(points / total, 1))
    return max(1, min(5, int(round(1 + ratio * 4))))


def _body_for_editorial(text: str, body: str) -> str:
    return _section_text(body, "正文草稿") or body or text


def _argument_gate(text: str, body: str) -> dict[str, bool]:
    draft = _body_for_editorial(text, body)
    editorial_card = _section_text(body, "发布编辑卡片")
    thesis_section = _section_text(body, "核心观点") or _section_text(body, "核心论断")
    thesis_present = bool(thesis_section.strip()) or _has_subheading(editorial_card, "核心论断") or bool(re.search(r"核心(观点|论断|判断)", text))
    section_count = len(re.findall(r"(?m)^###\s+", draft))
    return {
        "core_thesis_explicit": thesis_present,
        "three_supporting_moves": section_count >= 3 or len(re.findall(r"(?m)^第[一二三四五六七八九十]+", draft)) >= 3,
        "evidence_or_examples_present": bool(re.search(r"案例|例子|比如|例如|证据|来源|数据|报告|研究|客户|团队", draft)),
        "counterpoint_or_boundary_present": bool(re.search(r"但是|反过来|误区|不是.*而是|边界|限制|不适用|风险|反例|取舍|tradeoff", draft, flags=re.I)),
        "reader_judgment_change_clear": bool(re.search(r"读者|你会|你可以|从.*到|不再|真正|判断|决策|行动", draft)),
        "fact_boundary_present": "fact_check_required" in text or "核查" in text or "事实边界" in text or "边界" in draft,
    }


def editorial_quality_for_output(base: Path, p: Path) -> dict[str, Any]:
    text = p.read_text(encoding="utf-8", errors="ignore")
    body = re.sub(r"---.*?---", "", text, flags=re.S).strip()
    draft = _body_for_editorial(text, body)
    rel = str(p.relative_to(base))
    mechanical = evaluate_output_file(base, p)
    argument_gate = _argument_gate(text, body)
    zh_chars = _zh_char_count(draft)
    h3_count = len(re.findall(r"(?m)^###\s+", draft))
    bullet_count = len(re.findall(r"(?m)^[-*]\s+", draft))
    para_count = len([para for para in re.split(r"\n\s*\n", draft) if _zh_char_count(para) > 20])
    has_generic = bool(re.search(r"总之|综上所述|在当今|随着.*发展|具有重要意义|值得注意的是|我们需要认识到", draft))
    insight_points = sum([
        bool(re.search(r"真正|本质|根因|误区|反常识|不是.*而是|关键不在|核心不是", draft)),
        bool(re.search(r"边界|代价|取舍|限制|不适用|风险", draft)),
        bool(re.search(r"判断|决策|机制|闭环|系统|杠杆", draft)),
        mechanical.get("article_maturity") in {"article_draft", "publishable_draft"} or zh_chars >= 1200,
        not has_generic,
    ])
    problem_points = sum([
        bool(re.search(r"问题|痛点|困惑|为什么|失败|卡住|犹豫|风险", text)),
        bool(re.search(r"读者|目标读者|用户|创业者|负责人|团队|学生|管理者", text)),
        bool(re.search(r"场景|现场|当.*时|如果|准备|写作|汇报|决策", text)),
        bool(re.search(r"冲突|矛盾|反常识|不是.*而是|明明.*却", draft)),
    ])
    argument_points = sum([
        argument_gate["core_thesis_explicit"],
        argument_gate["three_supporting_moves"],
        argument_gate["evidence_or_examples_present"],
        argument_gate["counterpoint_or_boundary_present"],
        argument_gate["fact_boundary_present"],
    ])
    originality_points = sum([
        bool(re.search(r"不是.*而是|反常识|误区|真正|被忽略|最大误区|关键不在", draft)),
        bool(re.search(r"对比|从.*到|区别|差异|边界|重新理解", draft)),
        bool(re.search(r"模型|框架|机制|闭环|地图|路径", draft)),
        not has_generic,
    ])
    action_points = sum([
        bool(re.search(r"步骤|清单|方法|怎么做|建议|下一步|可以这样|操作|流程", draft)),
        bullet_count >= 5,
        bool(re.search(r"判断标准|检查|原则|规则|模板|工作流|SOP", draft)),
        bool(re.search(r"结尾|最后|所以|行动|开始|避免", draft[-1000:])),
    ])
    expression_points = sum([
        bool(re.search(r"标题候选|可复用金句|金句", text)),
        para_count >= 8,
        h3_count >= 3,
        bool(re.search(r"开头|钩子|场景|故事|很多人|你有没有", draft[:1200])),
        bool(re.search(r"不是.*而是|真正|不要|只有|越.*越", draft)),
    ])
    scores = {
        "insight_density": _score_1_5(insight_points, 5),
        "problem_sharpness": _score_1_5(problem_points, 4),
        "argument_strength": _score_1_5(argument_points, 5),
        "originality": _score_1_5(originality_points, 4),
        "actionability": _score_1_5(action_points, 4),
        "expression_quality": _score_1_5(expression_points, 5),
    }
    average = round(sum(scores.values()) / len(scores), 2)
    weak_dimensions = [key for key, value in scores.items() if value <= 3]
    article_maturity = str(mechanical.get("article_maturity") or "")
    argument_gate_passed = all(argument_gate.values())
    is_article = bool(article_maturity)
    if average >= 4.2 and not any(value < 4 for value in scores.values()):
        status = "publishable" if is_article else "strong"
    elif article_maturity == "publishable_draft" and not argument_gate_passed:
        status = "downgrade_to_draft"
    elif average >= 3.0:
        status = "revise"
    elif not argument_gate["core_thesis_explicit"] and not argument_gate["reader_judgment_change_clear"]:
        status = "park"
    else:
        status = "downgrade_to_draft"
    repair = []
    mapping = {
        "insight_density": "return_to_topic_page_and_rewrite_current_judgment",
        "problem_sharpness": "rewrite_editorial_card_reader_problem_and_tension",
        "argument_strength": "repair_argument_draft_with_evidence_counterpoint_and_limits",
        "originality": "add_differentiated_angle_contrast_or_tradeoff",
        "actionability": "add_steps_checklist_decision_criteria_or_next_actions",
        "expression_quality": "rewrite_hook_rhythm_memorable_lines_and_ending",
    }
    for key in weak_dimensions:
        repair.append(mapping[key])
    if article_maturity in {"article_draft", "publishable_draft"} and not argument_gate_passed:
        repair.append("do_not_polish_longer_until_argument_gate_passes")
    return {
        "file": rel,
        "status": status,
        "average_score": average,
        "scores": scores,
        "weak_dimensions": weak_dimensions,
        "repair_actions": sorted(set(repair)),
        "article_maturity": article_maturity or None,
        "argument_gate_passed": argument_gate_passed,
        "argument_gate": argument_gate,
    }


def editorial_quality_audit(cfg: dict[str, Any]) -> dict[str, Any]:
    base = Path(cfg["ai_knowledge_base"])
    items = [editorial_quality_for_output(base, p) for p in collect_markdown_files(kb_path(cfg, "outputs"))]
    status_counts = Counter(item["status"] for item in items)
    weak_counts: Counter[str] = Counter()
    for item in items:
        for dim in item["weak_dimensions"]:
            weak_counts[dim] += 1
    return {
        "output_count": len(items),
        "status_counts": dict(status_counts),
        "weak_dimension_counts": dict(weak_counts),
        "needs_attention_count": sum(1 for item in items if item["status"] not in {"publishable", "strong"}),
        "items": sorted(items, key=lambda item: (item["status"] == "publishable", item["average_score"], item["file"])),
    }


def render_editorial_quality(result: dict[str, Any]) -> str:
    lines = [
        "# Editorial Quality Review",
        "",
        "---",
        f"updated_at: {date.today().isoformat()}",
        "stage: system",
        "status: active",
        "---",
        "",
        "## Summary",
        "",
        f"- output_count: {result['output_count']}",
        f"- needs_attention_count: {result['needs_attention_count']}",
        f"- status_counts: {result['status_counts']}",
        f"- weak_dimension_counts: {result['weak_dimension_counts']}",
        "",
        "## Items",
        "",
    ]
    if not result["items"]:
        lines.append("- None.")
    for item in result["items"]:
        lines += [
            f"### {item['status']} · `{item['file']}`",
            "",
            f"- average_score: {item['average_score']}",
            f"- article_maturity: {item['article_maturity'] or '-'}",
            f"- argument_gate_passed: {str(item['argument_gate_passed']).lower()}",
            f"- scores: {item['scores']}",
            f"- weak_dimensions: {', '.join(item['weak_dimensions']) if item['weak_dimensions'] else '-'}",
            f"- repair_actions: {', '.join(item['repair_actions']) if item['repair_actions'] else '-'}",
            "",
        ]
    return "\n".join(lines).rstrip() + "\n"


VALID_OUTPUT_REVIEW_STATUSES = {"usable", "needs_revision", "rejected", "not_applicable"}
OUTPUT_REVIEW_DIMENSIONS = ["argument_clarity", "evidence_strength", "portability", "scope_control", "actionability", "reuse_value"]


def output_review_id(file: str) -> str:
    return hashlib.sha256(file.encode("utf-8")).hexdigest()[:16]


def output_review_items(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    base = Path(cfg["ai_knowledge_base"])
    items = []
    for p in collect_markdown_files(kb_path(cfg, "outputs")):
        rel = str(p.relative_to(base))
        mechanical = evaluate_output_file(base, p)
        items.append({
            "id": output_review_id(rel),
            "file": rel,
            "mechanical_status": mechanical["status"],
            "mechanical_score": mechanical["score"],
            "dimensions": OUTPUT_REVIEW_DIMENSIONS,
            "status": "pending_review",
        })
    return items


def output_review_result_row(args: argparse.Namespace) -> dict[str, Any]:
    if args.status not in VALID_OUTPUT_REVIEW_STATUSES:
        raise SystemExit(f"--status must be one of: {', '.join(sorted(VALID_OUTPUT_REVIEW_STATUSES))}")
    scores: dict[str, int] = {}
    if args.scores:
        try:
            loaded = json.loads(args.scores)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"--scores must be JSON: {exc}") from exc
        for key, value in loaded.items():
            if key not in OUTPUT_REVIEW_DIMENSIONS:
                raise SystemExit(f"unknown output review dimension: {key}")
            try:
                score = int(value)
            except (TypeError, ValueError) as exc:
                raise SystemExit(f"score for {key} must be integer") from exc
            if score < 1 or score > 5:
                raise SystemExit(f"score for {key} must be 1..5")
            scores[key] = score
    return {
        "schema_version": 1,
        "id": output_review_id(args.file),
        "file": args.file,
        "status": args.status,
        "scores": scores,
        "reviewed_at": now_iso(),
        "reviewer": args.reviewer or "codex",
        "note": args.note or "",
    }


def append_output_review_result(cfg: dict[str, Any], row: dict[str, Any]) -> None:
    path = system_file(cfg, "output-review-results.jsonl")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def latest_output_review_results(cfg: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows, _errors = read_index_objects(system_file(cfg, "output-review-results.jsonl"))
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row.get("id"):
            latest[str(row["id"])] = row
    return latest


def output_review_status(cfg: dict[str, Any]) -> dict[str, Any]:
    items = output_review_items(cfg)
    latest = latest_output_review_results(cfg)
    merged = []
    counts: Counter[str] = Counter()
    for item in items:
        result = latest.get(item["id"])
        if result:
            merged_item = {**item, "status": result.get("status", "pending_review"), "review": result}
        else:
            merged_item = item
        counts[str(merged_item.get("status", "pending_review"))] += 1
        merged.append(merged_item)
    return {
        "items": merged,
        "counts": dict(counts),
        "pending_review_count": sum(1 for item in merged if item.get("status") == "pending_review"),
        "blocking_review_count": sum(1 for item in merged if item.get("status") in {"needs_revision", "rejected"}),
        "result_rows": len(latest),
    }


def render_output_review_status(result: dict[str, Any]) -> str:
    lines = [
        "# Output Review Status",
        "",
        "---",
        f"updated_at: {date.today().isoformat()}",
        "stage: system",
        "status: active",
        "---",
        "",
        "## Summary",
        "",
        f"- pending_review_count: {result['pending_review_count']}",
        f"- blocking_review_count: {result['blocking_review_count']}",
        f"- result_rows: {result['result_rows']}",
    ]
    for key, value in sorted(result["counts"].items()):
        lines.append(f"- {key}: {value}")
    lines += ["", "## Rubric", ""]
    for dimension in OUTPUT_REVIEW_DIMENSIONS:
        lines.append(f"- {dimension}: score 1-5")
    lines += ["", "## Items", ""]
    if not result["items"]:
        lines.append("- None.")
    for item in result["items"][:300]:
        lines.append(f"- `{item['id']}` `{item['status']}` `{item['file']}` mechanical={item['mechanical_status']} score={item['mechanical_score']}")
    return "\n".join(lines).rstrip() + "\n"


DATE_PREFIX_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\s+(\d{4}-\d{2}-\d{2})(?:\s+(\d{4}-\d{2}-\d{2}))?\s+(.+)$")


def _date_value(meta: dict[str, Any], key: str) -> str:
    value = str(meta.get(key) or "").strip().strip('"').strip("'")
    if re.match(r"^\d{4}-\d{2}-\d{2}", value):
        return value[:10]
    return ""


def recover_saved_at_from_source(meta: dict[str, Any]) -> str:
    source_file = str(meta.get("source_file") or "").strip().strip('"')
    name = Path(source_file).name if source_file else ""
    m = re.match(r"^(\d{4}-\d{2}-\d{2})(?:\s|_|-|$)", name)
    return m.group(1) if m else ""


def _body_title(body: str, fallback: str) -> str:
    match = re.search(r"(?m)^#\s+(.+)$", body)
    return match.group(1).strip() if match else fallback


def strip_date_prefix(title: str, meta: dict[str, Any] | None = None, root_key: str = "") -> str:
    title = title.strip()
    meta = meta or {}
    updated = _date_value(meta, "updated_at")
    created = _date_value(meta, "created_at")
    saved = _date_value(meta, "saved_at")
    m = DATE_PREFIX_RE.match(title)
    if not m:
        leading_dates = re.match(r"^(?:\d{4}-\d{2}-\d{2}\s+)+(.+)$", title)
        return leading_dates.group(1).strip() if leading_dates else title
    if m.group(1) != updated or m.group(2) != created:
        # Older normalized titles may start with a previous updated/created
        # pair. Strip date-like prefixes anyway so changing updated_at is
        # idempotent and does not create filenames with four dates.
        return strip_date_prefix(m.group(4).strip(), meta=meta, root_key=root_key)
    if root_key == "source_refinements":
        rest = m.group(4).strip()
        if saved and rest.startswith(saved + " "):
            rest = rest[len(saved):].strip()
        return rest
    rest = m.group(4).strip()
    # Non-source layers use only updated_at + created_at in filenames.
    # If an earlier source-style or already-normalized prefix left extra date
    # tokens in the title, peel them recursively so re-runs are idempotent.
    while True:
        nested = DATE_PREFIX_RE.match(rest)
        if nested:
            rest = nested.group(4).strip()
            continue
        leading_dates = re.match(r"^(?:\d{4}-\d{2}-\d{2}\s+)+(.+)$", rest)
        if leading_dates:
            rest = leading_dates.group(1).strip()
            continue
        return rest


def safe_filename_stem(stem: str, max_len: int = 180) -> str:
    stem = re.sub(r"[/:]", "：", stem).strip()
    stem = re.sub(r"\s+", " ", stem)
    if len(stem) <= max_len:
        return stem
    return stem[: max_len - 1].rstrip() + "…"


def expected_freshness_stem(path: Path, meta: dict[str, Any], body: str, root_key: str = "") -> str:
    created = _date_value(meta, "created_at")
    updated = _date_value(meta, "updated_at")
    saved = _date_value(meta, "saved_at")
    base_title = strip_date_prefix(_body_title(body, path.stem), meta=meta, root_key=root_key)
    if updated and created:
        if root_key == "source_refinements":
            saved = saved or recover_saved_at_from_source(meta)
            if not saved:
                return path.stem
            return safe_filename_stem(f"{updated} {created} {saved} {base_title}")
        return safe_filename_stem(f"{updated} {created} {base_title}")
    return path.stem


def filename_date_audit(cfg: dict[str, Any]) -> dict[str, Any]:
    base = Path(cfg["ai_knowledge_base"])
    issues = []
    scanned = 0
    for root_key in ("source_refinements", "topic_pages", "reusable_assets", "outputs"):
        root = kb_path(cfg, root_key)
        for p in collect_markdown_files(root):
            scanned += 1
            raw = p.read_text("utf-8", errors="ignore")
            meta, body = split_frontmatter(raw)
            created = _date_value(meta, "created_at")
            updated = _date_value(meta, "updated_at")
            rel = str(p.relative_to(base))
            if not created or not updated:
                issues.append({"file": rel, "error": "missing_created_at_or_updated_at"})
                continue
            saved = _date_value(meta, "saved_at")
            if root_key == "source_refinements":
                recovered = recover_saved_at_from_source(meta)
                if not saved:
                    issues.append({"file": rel, "error": "missing_saved_at_for_source_refinement", "recovered_from_source_file": recovered})
                elif recovered and saved != recovered:
                    issues.append({"file": rel, "error": "saved_at_mismatch_source_file_date", "saved_at": saved, "source_file_date": recovered})
            if updated < created:
                issues.append({"file": rel, "error": "updated_at_before_created_at", "created_at": created, "updated_at": updated})
            expected = expected_freshness_stem(p, meta, body, root_key=root_key)
            m = DATE_PREFIX_RE.match(p.stem)
            if not m:
                issues.append({"file": rel, "error": "missing_filename_date_prefix", "expected_stem": expected})
            elif m.group(1) != updated or m.group(2) != created:
                issues.append({"file": rel, "error": "filename_dates_do_not_match_frontmatter", "expected_stem": expected})
            elif root_key == "source_refinements" and m.group(3) != saved:
                issues.append({"file": rel, "error": "filename_saved_at_does_not_match_frontmatter", "expected_stem": expected})
            elif root_key != "source_refinements" and m.group(3):
                issues.append({"file": rel, "error": "unexpected_saved_at_date_in_non_source_filename", "expected_stem": expected})
            elif p.stem != expected:
                issues.append({"file": rel, "error": "filename_title_does_not_match_body_title", "expected_stem": expected})
    return {"files_scanned": scanned, "issue_count": len(issues), "issues": issues}


def _replace_first_h1(body: str, new_title: str) -> str:
    if re.search(r"(?m)^#\s+.+$", body):
        return re.sub(r"(?m)^#\s+.+$", f"# {new_title}", body, count=1)
    return f"# {new_title}\n\n{body.lstrip()}"


def _update_wikilinks(text: str, title_map: dict[str, str]) -> str:
    def repl(match: re.Match[str]) -> str:
        inner = match.group(1)
        target, sep, alias = inner.partition("|")
        head, hash_sep, anchor = target.partition("#")
        clean = head.strip()
        if clean not in title_map:
            return match.group(0)
        new_target = title_map[clean]
        if hash_sep:
            new_target = f"{new_target}#{anchor}"
        if sep:
            return f"[[{new_target}|{alias}]]"
        return f"[[{new_target}]]"
    return re.sub(r"\[\[([^\]]+)\]\]", repl, text)


def normalize_filename_dates(cfg: dict[str, Any], apply: bool = False, touch_updated_at: bool = False, update_link_refresh_dates: bool = True) -> dict[str, Any]:
    base = Path(cfg["ai_knowledge_base"])
    files = []
    file_root_keys: dict[Path, str] = {}
    for key in ("source_refinements", "topic_pages", "reusable_assets", "outputs"):
        for p in collect_markdown_files(kb_path(cfg, key)):
            files.append(p)
            file_root_keys[p] = key
    planned = []
    title_map: dict[str, str] = {}
    for p in files:
        raw = p.read_text("utf-8", errors="ignore")
        meta, body = split_frontmatter(raw)
        created = _date_value(meta, "created_at")
        updated = _date_value(meta, "updated_at")
        if not created or not updated:
            continue
        saved = _date_value(meta, "saved_at")
        if touch_updated_at:
            updated = date.today().isoformat()
        if updated < created:
            updated = created
        root_key = file_root_keys.get(p, "")
        if root_key == "source_refinements":
            recovered_saved = recover_saved_at_from_source(meta)
            if recovered_saved and saved != recovered_saved:
                saved = recovered_saved
        expected_stem = expected_freshness_stem(p, {**meta, "updated_at": updated, "created_at": created, "saved_at": saved}, body, root_key=root_key)
        new_path = p.with_name(expected_stem + p.suffix)
        old_stem = p.stem
        if old_stem != expected_stem:
            planned.append({"from": str(p.relative_to(base)), "to": str(new_path.relative_to(base))})
            title_map[old_stem] = expected_stem
        body_title = _body_title(body, old_stem)
        if body_title != expected_stem:
            title_map[body_title] = expected_stem
        if root_key == "source_refinements":
            recovered_saved = recover_saved_at_from_source(meta)
            if recovered_saved and created and updated and recovered_saved != created:
                base_title = strip_date_prefix(body_title, {**meta, "saved_at": recovered_saved}, root_key=root_key)
                stale_alias = safe_filename_stem(f"{updated} {created} {created} {recovered_saved} {base_title}")
                if stale_alias != expected_stem:
                    title_map[stale_alias] = expected_stem
                stale_alias_without_saved = safe_filename_stem(f"{updated} {created} {created} {base_title}")
                if stale_alias_without_saved != expected_stem:
                    title_map[stale_alias_without_saved] = expected_stem
    if not apply:
        return {"apply": False, "planned_renames": planned, "rename_count": len(planned)}
    # First update frontmatter dates when updated_at < created_at and H1 titles.
    for p in files:
        raw = p.read_text("utf-8", errors="ignore")
        meta, body = split_frontmatter(raw)
        created = _date_value(meta, "created_at")
        updated = _date_value(meta, "updated_at")
        if not created or not updated:
            continue
        fixed = raw
        root_key = file_root_keys.get(p, "")
        if root_key == "source_refinements":
            recovered_saved = recover_saved_at_from_source(meta)
            if recovered_saved and _date_value(meta, "saved_at") != recovered_saved:
                fixed = re.sub(r"(?m)^saved_at:\s*.*$", f'saved_at: "{recovered_saved}"', fixed, count=1)
        if touch_updated_at:
            today = date.today().isoformat()
            fixed = re.sub(r"(?m)^updated_at:\s*.*$", f'updated_at: "{today}"', fixed, count=1)
            updated = today
        elif updated < created:
            fixed = re.sub(r"(?m)^updated_at:\s*.*$", f'updated_at: "{created}"', fixed, count=1)
            updated = created
        meta2, body2 = split_frontmatter(fixed)
        expected_stem = expected_freshness_stem(p, meta2, body2, root_key=root_key)
        new_body = _replace_first_h1(body2, expected_stem)
        if new_body != body2:
            fm = fixed.split("---", 2)[1]
            fixed = f"---{fm}---\n{new_body}"
        p.write_text(fixed, encoding="utf-8")
    # Rename files after content title updates.
    for item in planned:
        src = base / item["from"]
        dst = base / item["to"]
        if not src.exists():
            continue
        if dst.exists() and dst != src:
            raise SystemExit(json.dumps({"error": "target_exists", "from": item["from"], "to": item["to"]}, ensure_ascii=False))
        src.rename(dst)
    # Refresh wikilinks in formal knowledge roots and system reports. Do not mutate backups.
    refreshed_files = []
    link_refresh_metadata_updated = []
    refresh_roots = [kb_path(cfg, key) for key in ("source_refinements", "topic_pages", "reusable_assets", "outputs")]
    formal_roots = {kb_path(cfg, key).resolve(): key for key in ("source_refinements", "topic_pages", "reusable_assets", "outputs")}
    reports_root = system_file(cfg, "quality-gate.md").parent
    if reports_root.exists():
        refresh_roots.append(reports_root)
    seen_refresh: set[Path] = set()
    for root in refresh_roots:
        for p in collect_markdown_files(root):
            if p in seen_refresh:
                continue
            seen_refresh.add(p)
            raw = p.read_text("utf-8", errors="ignore")
            new = _update_wikilinks(raw, title_map)
            if new != raw:
                if update_link_refresh_dates:
                    try:
                        p_resolved = p.resolve()
                        in_formal_root = any(root == p_resolved or root in p_resolved.parents for root in formal_roots)
                    except OSError:
                        in_formal_root = False
                    today = date.today().isoformat()
                    if in_formal_root:
                        refreshed, changed = _set_frontmatter_field(new, "obsidian_links_updated", today, after_keys=["moc", "related_outputs", "related_assets", "related_topics", "related_sources"])
                        if changed:
                            new = refreshed
                            link_refresh_metadata_updated.append(str(p.relative_to(base)))
                p.write_text(new, encoding="utf-8")
                refreshed_files.append(str(p.relative_to(base)))
    return {
        "apply": True,
        "renamed": planned,
        "rename_count": len(planned),
        "wikilink_files_updated": refreshed_files,
        "link_refresh_metadata_updated": link_refresh_metadata_updated,
        "date_touched_by_link_refresh": [],
        "followup": None,
    }


def relation_audit(cfg: dict[str, Any]) -> dict[str, Any]:
    base = Path(cfg["ai_knowledge_base"])
    roots = [kb_path(cfg, key) for key in ("source_refinements", "topic_pages", "reusable_assets", "outputs")]
    files = []
    for root in roots:
        files.extend(collect_markdown_files(root))
    aliases: dict[str, str] = {}
    duplicate_aliases: set[str] = set()
    for p in files:
        text = p.read_text(encoding="utf-8", errors="ignore")
        title = markdown_title(p, text)
        for alias in {p.stem, title, title.replace(" ", "")}:
            if alias in aliases and aliases[alias] != str(p.relative_to(base)):
                duplicate_aliases.add(alias)
            aliases[alias] = str(p.relative_to(base))
    unresolved = []
    for p in files:
        text = p.read_text(encoding="utf-8", errors="ignore")
        for target in wikilink_targets(text):
            if not target or target in aliases or target.replace(" ", "") in aliases:
                continue
            unresolved.append({"from": str(p.relative_to(base)), "target": target})
    return {
        "files_scanned": len(files),
        "unresolved_links": unresolved,
        "unresolved_count": len(unresolved),
        "duplicate_aliases": sorted(duplicate_aliases),
    }


def render_relation_audit(result: dict[str, Any]) -> str:
    lines = [
        "# Relation Audit",
        "",
        "---",
        f"updated_at: {date.today().isoformat()}",
        "stage: system",
        "status: active",
        "---",
        "",
        "## Summary",
        "",
        f"- files_scanned: {result['files_scanned']}",
        f"- unresolved_links: {result['unresolved_count']}",
        f"- duplicate_aliases: {len(result['duplicate_aliases'])}",
        "",
        "## Unresolved Links",
        "",
    ]
    if not result["unresolved_links"]:
        lines.append("- None.")
    for item in result["unresolved_links"][:300]:
        lines.append(f"- `{item['from']}` -> `[[{item['target']}]]`")
    if result["duplicate_aliases"]:
        lines += ["", "## Duplicate Aliases", ""]
        for alias in result["duplicate_aliases"][:100]:
            lines.append(f"- `{alias}`")
    return "\n".join(lines).rstrip() + "\n"


PORTABILITY_PATTERNS = {
    "absolute_or_private_path": r"/Users/|/Desktop/|伍豪|OPC",
    "private_folder_code": r"\b8XX\b|\b800-|801-|888-|00-系统|00-system|10-来源精炼|10-source-refinements|20-主题页|20-topic-pages|30-可复用资产|30-reusable-assets|40-输出|40-outputs|\b20/30/40\b",
    "hardcoded_public_account_batch": r"\d+\s*-\s*\d+\s*篇公众号|每处理\s*\d+\s*个新来源|最近\s*\d+\s*篇来源",
    "source_type_as_method_default": r"适用于处理\s*\d*[-—]?\d*\s*篇公众号|公众号文章、若干章节电子书",
}

LOCAL_NOTE_MARKERS = {
    "local operating note",
    "personal implementation plan",
    "migration note",
    "case record",
    "复盘记录",
    "本地操作",
    "个人实施",
    "迁移记录",
    "案例记录",
}


def portability_body(text: str) -> tuple[dict[str, Any], str]:
    meta, body = split_frontmatter(text)
    body = re.split(r"(?m)^##\s+关联知识\s*$", body, maxsplit=1)[0]
    body = re.sub(r"```.*?```", "", body, flags=re.S)
    return meta, body


def is_local_note(meta: dict[str, Any], body: str, path: Path) -> bool:
    haystack = " ".join([str(path), str(meta.get("stage", "")), str(meta.get("status", "")), body[:500]]).lower()
    return any(marker.lower() in haystack for marker in LOCAL_NOTE_MARKERS)


def portability_audit(cfg: dict[str, Any]) -> dict[str, Any]:
    base = Path(cfg["ai_knowledge_base"])
    roots = [topic_pages_content_dir(cfg), kb_path(cfg, "reusable_assets"), kb_path(cfg, "outputs")]
    issues = []
    scanned = 0
    skipped_local = []
    for root in roots:
        for p in collect_markdown_files(root):
            scanned += 1
            text = p.read_text(encoding="utf-8", errors="ignore")
            meta, body = portability_body(text)
            rel = str(p.relative_to(base))
            if is_local_note(meta, body, p):
                skipped_local.append(rel)
                continue
            for name, pattern in PORTABILITY_PATTERNS.items():
                for match in re.finditer(pattern, body, flags=re.I):
                    line_no = body[:match.start()].count("\n") + 1
                    excerpt = body[match.start():match.end()]
                    issues.append({"file": rel, "line": line_no, "issue": name, "excerpt": excerpt})
    return {
        "files_scanned": scanned,
        "issue_count": len(issues),
        "issues": issues,
        "skipped_local_notes": skipped_local,
    }


def render_portability_audit(result: dict[str, Any]) -> str:
    lines = [
        "# Portability Audit",
        "",
        "---",
        f"updated_at: {date.today().isoformat()}",
        "stage: system",
        "status: active",
        "---",
        "",
        "## Summary",
        "",
        f"- files_scanned: {result['files_scanned']}",
        f"- issue_count: {result['issue_count']}",
        f"- skipped_local_notes: {len(result['skipped_local_notes'])}",
        "",
        "## Issues",
        "",
    ]
    if not result["issues"]:
        lines.append("- None.")
    for item in result["issues"][:300]:
        lines.append(f"- `{item['file']}` line {item['line']}: {item['issue']} -> `{item['excerpt']}`")
    if result["skipped_local_notes"]:
        lines += ["", "## Skipped Local Notes", ""]
        for item in result["skipped_local_notes"][:100]:
            lines.append(f"- `{item}`")
    return "\n".join(lines).rstrip() + "\n"


TOPIC_REQUIRED_SECTION_GROUPS = {
    "topic_question": [r"^##\s+(主题问题|Topic question)\s*$"],
    "current_judgment": [r"^##\s+(当前判断|Current judgment)\s*$"],
    "supporting_sources": [r"^##\s+(支撑来源|Supporting sources)\s*$"],
    "core_model": [r"^##\s+(核心模型|Core model)\s*$"],
    "reliable": [r"^##\s+(什么是可靠的|What is reliable)\s*$"],
    "uncertain": [r"^##\s+(什么仍不确定|What is uncertain)\s*$"],
    "output_ready": [r"^##\s+(可输出内容|Output-ready material)\s*$"],
    "next_actions": [r"^##\s+(下一步动作|Next actions)\s*$"],
}

TOPIC_PROCESS_ONLY_PATTERNS = {
    "split_process_in_body": r"从原来的.+拆出|拆分后的原则|本页不是新增内容堆叠|归属重组|母题保留为总览",
    "directory_code_as_usage": r"优先看本页的\s*`?(20|30|40)`?|`30`\s*资产|`40`\s*输出",
}


def body_before_relations(text: str) -> tuple[dict[str, Any], str]:
    meta, body = split_frontmatter(text)
    body = re.split(r"(?m)^##\s+关联知识\s*$", body, maxsplit=1)[0]
    return meta, body


def topic_page_audit(cfg: dict[str, Any]) -> dict[str, Any]:
    base = Path(cfg["ai_knowledge_base"])
    root = topic_pages_content_dir(cfg)
    issues = []
    files = collect_markdown_files(root)
    for p in files:
        text = p.read_text(encoding="utf-8", errors="ignore")
        meta, body = body_before_relations(text)
        rel = str(p.relative_to(base))
        for key, patterns in TOPIC_REQUIRED_SECTION_GROUPS.items():
            if not any(re.search(pattern, body, flags=re.M | re.I) for pattern in patterns):
                issues.append({"file": rel, "issue": f"missing_section:{key}", "line": 1, "excerpt": ""})
        for name, pattern in TOPIC_PROCESS_ONLY_PATTERNS.items():
            for match in re.finditer(pattern, body, flags=re.I):
                line_no = body[:match.start()].count("\n") + 1
                issues.append({"file": rel, "issue": name, "line": line_no, "excerpt": body[match.start():match.end()]})
        if str(meta.get("stage", "")).strip('"') not in {"主题页", "topic_page", "Topic page"}:
            issues.append({"file": rel, "issue": "stage_not_topic_page", "line": 1, "excerpt": str(meta.get("stage", ""))})
    return {"files_scanned": len(files), "issue_count": len(issues), "issues": issues}


def render_topic_page_audit(result: dict[str, Any]) -> str:
    lines = [
        "# Topic Page Audit",
        "",
        "---",
        f"updated_at: {date.today().isoformat()}",
        "stage: system",
        "status: active",
        "---",
        "",
        "## Summary",
        "",
        f"- files_scanned: {result['files_scanned']}",
        f"- issue_count: {result['issue_count']}",
        "",
        "## Issues",
        "",
    ]
    if not result["issues"]:
        lines.append("- None.")
    for item in result["issues"][:300]:
        suffix = f" -> `{item['excerpt']}`" if item.get("excerpt") else ""
        lines.append(f"- `{item['file']}` line {item['line']}: {item['issue']}{suffix}")
    return "\n".join(lines).rstrip() + "\n"


def parse_wikilinks_from_value(value: Any) -> list[str]:
    if isinstance(value, list):
        text = " ".join(str(v) for v in value)
    else:
        text = str(value or "")
    return wikilink_targets(text)


def parse_evidence_refs(value: Any) -> list[str]:
    """Parse evidence references from frontmatter.

    Evidence fields may contain Obsidian wikilinks, plain titles, relative paths,
    or a mix of both. Treat plain values as candidate titles so audits do not
    confuse "not wikilinked" with "not evidenced".
    """
    refs = set(parse_wikilinks_from_value(value))
    values = value if isinstance(value, list) else [value]
    for item in values:
        text = str(item or "").strip().strip('"').strip("'")
        if not text:
            continue
        if "[[" in text:
            refs.update(wikilink_targets(text))
            continue
        refs.add(clean_link_target(text))
        refs.add(Path(clean_link_target(text)).stem)
    return sorted(r for r in refs if r)


def asset_audit(cfg: dict[str, Any]) -> dict[str, Any]:
    base = Path(cfg["ai_knowledge_base"])
    asset_root = kb_path(cfg, "reusable_assets")
    output_root = kb_path(cfg, "outputs")
    topic_root = topic_pages_content_dir(cfg)
    topic_names = set()
    for p in collect_markdown_files(topic_root):
        text = p.read_text(encoding="utf-8", errors="ignore")
        topic_names.add(p.stem)
        topic_names.add(markdown_title(p, text))
        topic_names.add(markdown_title(p, text).replace(" ", ""))
    clusters: dict[str, dict[str, Any]] = defaultdict(lambda: {"assets": [], "outputs": []})
    assets = []
    for p in collect_markdown_files(asset_root):
        text = p.read_text(encoding="utf-8", errors="ignore")
        meta, _body = split_frontmatter(text)
        cluster = str(meta.get("theme_cluster") or "unclassified").strip('"')
        related_topics = parse_wikilinks_from_value(meta.get("related_topics"))
        asset_type = str(meta.get("asset_type") or "unclassified").strip('"')
        status = str(meta.get("status") or "").strip('"')
        issue_list = []
        if not related_topics:
            issue_list.append("missing_parent_topic")
        elif not any(t in topic_names or t.replace(" ", "") in topic_names for t in related_topics):
            issue_list.append("parent_topic_not_resolved")
        if asset_type in {"", "methods", "methodology", "方法论", "frameworks", "框架图谱", "expressions", "金句表达", "cases", "案例"}:
            issue_list.append("generic_or_default_asset_type")
        if status not in {"candidate", "draft", "active", "merge_candidate", "superseded", "deprecated"}:
            issue_list.append("missing_lifecycle_status")
        item = {"file": str(p.relative_to(base)), "cluster": cluster, "asset_type": asset_type, "status": status, "related_topics": related_topics, "issues": issue_list}
        assets.append(item)
        clusters[cluster]["assets"].append(item)
    outputs = []
    for p in collect_markdown_files(output_root):
        text = p.read_text(encoding="utf-8", errors="ignore")
        meta, _body = split_frontmatter(text)
        cluster = str(meta.get("theme_cluster") or "unclassified").strip('"')
        related_topics = parse_wikilinks_from_value(meta.get("related_topics"))
        related_assets = parse_wikilinks_from_value(meta.get("related_assets"))
        issue_list = []
        if not related_topics:
            issue_list.append("missing_parent_topic")
        if not related_assets:
            issue_list.append("missing_related_assets")
        item = {"file": str(p.relative_to(base)), "cluster": cluster, "related_topics": related_topics, "related_assets": related_assets, "issues": issue_list}
        outputs.append(item)
        clusters[cluster]["outputs"].append(item)
    overloaded = []
    for cluster, values in sorted(clusters.items()):
        if len(values["assets"]) > 5 or len(values["outputs"]) > 5:
            overloaded.append({"cluster": cluster, "assets": len(values["assets"]), "outputs": len(values["outputs"]), "action": "structure_review"})
    type_counts = Counter(item["asset_type"] for item in assets)
    return {
        "assets": assets,
        "outputs": outputs,
        "asset_type_counts": dict(type_counts),
        "overloaded_clusters": overloaded,
        "asset_issue_count": sum(1 for item in assets if item["issues"]),
        "output_issue_count": sum(1 for item in outputs if item["issues"]),
    }


def render_asset_audit(result: dict[str, Any]) -> str:
    lines = [
        "# Asset Relation Audit",
        "",
        "---",
        f"updated_at: {date.today().isoformat()}",
        "stage: system",
        "status: active",
        "---",
        "",
        "## Summary",
        "",
        f"- assets: {len(result['assets'])}",
        f"- outputs: {len(result['outputs'])}",
        f"- asset_issue_count: {result['asset_issue_count']}",
        f"- output_issue_count: {result['output_issue_count']}",
        "",
        "## Asset Type Counts",
        "",
    ]
    for key, count in sorted(result["asset_type_counts"].items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- {key}: {count}")
    lines += ["", "## Overloaded Clusters", ""]
    if not result["overloaded_clusters"]:
        lines.append("- None.")
    for item in result["overloaded_clusters"]:
        lines.append(f"- `{item['cluster']}`: assets={item['assets']}, outputs={item['outputs']}, action={item['action']}")
    lines += ["", "## Asset Issues", ""]
    for item in result["assets"]:
        if item["issues"]:
            lines.append(f"- `{item['file']}`: {', '.join(item['issues'])}")
    lines += ["", "## Output Issues", ""]
    for item in result["outputs"]:
        if item["issues"]:
            lines.append(f"- `{item['file']}`: {', '.join(item['issues'])}")
    return "\n".join(lines).rstrip() + "\n"


def _source_quality_by_title(cfg: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    base = Path(cfg["ai_knowledge_base"])
    root = kb_path(cfg, "source_refinements")
    for p in collect_markdown_files(root):
        text = p.read_text("utf-8", errors="replace")
        meta, _body = split_frontmatter(text)
        quality = classify_source_quality(meta, p, text)
        rel = str(p.relative_to(base))
        title = p.stem
        md_title = markdown_title(p, text)
        record = {"file": rel, **quality}
        for key in {title, md_title, strip_date_prefix(title, meta, root_key="source_refinements"), strip_date_prefix(md_title, meta, root_key="source_refinements")}:
            if key:
                index[key] = record
    return index


def _evidence_minimum_for_gap(root_key: str, meta: dict[str, Any], path: Path) -> int:
    if root_key == "topic_pages":
        if "MOC" in path.parts or "moc" in {part.lower() for part in path.parts}:
            return 0
        return 3
    if root_key == "reusable_assets":
        asset_type = str(meta.get("asset_type") or "").strip().lower()
        if asset_type in {"case", "case-pattern", "anti-case", "expression", "definition", "distinction", "warning", "metaphor"}:
            return 1
        return 3
    output_type = str(meta.get("output_type") or "").strip().lower()
    maturity = str(meta.get("article_maturity") or "").strip().lower()
    if maturity == "publishable_draft":
        return 3
    if output_type in {"feynman", "费曼解释"}:
        return 2
    return 3


def _gap_priority(root_key: str, gap_types: list[str], meta: dict[str, Any]) -> str:
    maturity = str(meta.get("article_maturity") or "").lower()
    if "publishable_output_needs_fact_support" in gap_types or maturity == "publishable_draft":
        return "P0"
    if "high_fact_risk_without_primary_evidence" in gap_types:
        return "P1"
    if root_key == "topic_pages" or "missing_authoritative_source" in gap_types:
        return "P2"
    return "P3"


def _preferred_source_types(gap_types: list[str]) -> list[str]:
    if "high_fact_risk_without_primary_evidence" in gap_types or "publishable_output_needs_fact_support" in gap_types:
        return ["official_doc", "report", "paper", "primary_source"]
    if "missing_authoritative_source" in gap_types:
        return ["book", "paper", "official_doc", "institutional_report"]
    if "single_channel_evidence" in gap_types:
        return ["book", "report", "paper", "official_doc", "case"]
    return ["book", "report", "paper", "official_doc", "high_quality_case"]


def evidence_gap_audit(cfg: dict[str, Any]) -> dict[str, Any]:
    base = Path(cfg["ai_knowledge_base"])
    quality_index = _source_quality_by_title(cfg)
    verification_results = latest_verification_results(cfg)
    gaps = []
    type_counts: Counter[str] = Counter()
    priority_counts: Counter[str] = Counter()
    for root_key, p in formal_artifact_files(cfg):
        text = p.read_text("utf-8", errors="replace")
        meta, _body = split_frontmatter(text)
        evidence_refs = parse_evidence_refs(meta.get("evidence_from", meta.get("supported_by", [])))
        source_records = []
        for ref in evidence_refs:
            clean = clean_link_target(ref)
            rec = quality_index.get(clean)
            if rec:
                source_records.append(rec)
        tiers = [r["source_quality_tier"] for r in source_records]
        channels = [r["source_channel"] for r in source_records]
        modes = [r["source_evidence_mode"] for r in source_records]
        weights = [float(r["promotion_weight"]) for r in source_records]
        gap_types: list[str] = []
        reasons: list[str] = []
        minimum = _evidence_minimum_for_gap(root_key, meta, p)
        if len(source_records) < minimum:
            gap_types.append("thin_evidence")
            reasons.append(f"resolved evidence count {len(source_records)} is below minimum {minimum}")
        if source_records and not any(t in {"A", "B"} for t in tiers):
            gap_types.append("only_low_tier_sources")
            reasons.append("current supporting sources are all C/D tier")
        if source_records and not any(t in {"A", "B"} for t in tiers):
            gap_types.append("missing_authoritative_source")
        if len(set(channels)) == 1 and channels and channels[0] == "public_account" and root_key in {"topic_pages", "outputs"}:
            gap_types.append("single_channel_evidence")
            reasons.append("evidence is concentrated in public-account sources")
        if has_high_risk(text) and not any(m in {"primary_data", "cited_report"} or ch in {"official_doc", "paper", "report"} for m, ch in zip(modes, channels)):
            gap_types.append("high_fact_risk_without_primary_evidence")
            reasons.append("artifact has high-risk factual signals without primary/report evidence")
        rel = str(p.relative_to(base))
        verification_id = hashlib.sha256(rel.encode("utf-8")).hexdigest()[:16]
        verification_status = str(verification_results.get(verification_id, {}).get("status") or "")
        publication_fact_support_closed = verification_status in {"verified", "not_applicable"}
        maturity = str(meta.get("article_maturity") or "").lower()
        if root_key == "outputs" and maturity == "publishable_draft" and has_high_risk(text) and not publication_fact_support_closed:
            gap_types.append("publishable_output_needs_fact_support")
            reasons.append("publishable draft still needs publication-grade fact support")
        if source_records and sum(weights) < minimum * 0.8:
            gap_types.append("low_weighted_evidence")
            reasons.append(f"weighted evidence {sum(weights):.2f} is weak for artifact type")
        gap_types = sorted(set(gap_types))
        if not gap_types:
            continue
        for t in gap_types:
            type_counts[t] += 1
        priority = _gap_priority(root_key, gap_types, meta)
        priority_counts[priority] += 1
        gap_id = hashlib.sha256((rel + "|" + ",".join(gap_types)).encode("utf-8")).hexdigest()[:12]
        if "thin_evidence" in gap_types or "missing_authoritative_source" in gap_types:
            action = "bounded_evidence_fill"
        elif "publishable_output_needs_fact_support" in gap_types:
            action = "verify_before_publish"
        elif "only_low_tier_sources" in gap_types:
            action = "limit_use_or_demote_to_needs_evidence"
        else:
            action = "review_evidence_boundary"
        gaps.append({
            "gap_id": gap_id,
            "priority": priority,
            "target_artifact": rel,
            "layer": root_key,
            "gap_type": gap_types,
            "why_needed": "; ".join(reasons) if reasons else "evidence boundary needs review",
            "current_evidence_count": len(source_records),
            "current_best_tier": min(tiers) if tiers else "none",
            "current_source_channels": sorted(set(channels)),
            "weighted_evidence": round(sum(weights), 2),
            "preferred_source_type": _preferred_source_types(gap_types),
            "max_sources_to_add": 3,
            "max_search_queries": 5,
            "max_reading_items": 3,
            "stop_condition": "stop when 2 A/B sources are found, budget is exhausted, or downgrade/park is recommended",
            "recommended_action": action,
            "status": "open",
        })
    order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    gaps.sort(key=lambda x: (order.get(x["priority"], 9), x["target_artifact"]))
    return {
        "gap_count": len(gaps),
        "priority_counts": dict(priority_counts),
        "gap_type_counts": dict(type_counts),
        "gaps": gaps,
    }


def render_evidence_gap_registry(result: dict[str, Any]) -> str:
    lines = [
        "# Evidence Gap Registry",
        "",
        "---",
        f"updated_at: {date.today().isoformat()}",
        "stage: system",
        f"status: {'open' if result['gap_count'] else 'clear'}",
        "---",
        "",
        "## Summary",
        "",
        f"- gap_count: {result['gap_count']}",
        "",
        "## Priority Counts",
        "",
    ]
    for key in ["P0", "P1", "P2", "P3"]:
        lines.append(f"- {key}: {result['priority_counts'].get(key, 0)}")
    lines += ["", "## Gap Type Counts", ""]
    if not result["gap_type_counts"]:
        lines.append("- None.")
    for key, value in sorted(result["gap_type_counts"].items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- {key}: {value}")
    lines += ["", "## Open Gaps", ""]
    if not result["gaps"]:
        lines.append("- None.")
    for item in result["gaps"][:300]:
        lines += [
            f"### {item['priority']} · `{item['gap_id']}`",
            "",
            f"- target: `{item['target_artifact']}`",
            f"- gap_type: {', '.join(item['gap_type'])}",
            f"- why_needed: {item['why_needed']}",
            f"- evidence: count={item['current_evidence_count']}, best_tier={item['current_best_tier']}, weighted={item['weighted_evidence']}, channels={', '.join(item['current_source_channels']) if item['current_source_channels'] else 'none'}",
            f"- preferred_source_type: {', '.join(item['preferred_source_type'])}",
            f"- budget: sources={item['max_sources_to_add']}, queries={item['max_search_queries']}, readings={item['max_reading_items']}",
            f"- stop_condition: {item['stop_condition']}",
            f"- recommended_action: {item['recommended_action']}",
            f"- status: {item['status']}",
            "",
        ]
    return "\n".join(lines).rstrip() + "\n"


def formal_artifact_files(cfg: dict[str, Any]) -> list[tuple[str, Path]]:
    items: list[tuple[str, Path]] = []
    for root_key in ("topic_pages", "reusable_assets", "outputs"):
        root = kb_path(cfg, root_key)
        for p in collect_markdown_files(root):
            items.append((root_key, p))
    return items


def _artifact_review_interval_days(root_key: str, path: Path, meta: dict[str, Any], text: str) -> int:
    output_type = str(meta.get("output_type") or "").lower()
    article_maturity = str(meta.get("article_maturity") or "").lower()
    asset_type = str(meta.get("asset_type") or "").lower()
    parts = {part.lower() for part in path.parts}
    if has_high_risk(text):
        return 14
    if root_key == "topic_pages":
        if "moc" in parts or "moc" in str(path).lower():
            return 90
        return 60
    if root_key == "reusable_assets":
        if asset_type in {"expression", "expressions", "金句表达", "definition", "metaphor"}:
            return 180
        return 90
    if root_key == "outputs":
        if article_maturity == "publishable_draft":
            return 14
        if article_maturity == "article_draft" or "文章草稿" in output_type:
            return 30
        if "方案" in output_type or "solution" in output_type:
            return 60
        return 90
    return 90


def lifecycle_audit(cfg: dict[str, Any]) -> dict[str, Any]:
    base = Path(cfg["ai_knowledge_base"])
    items = []
    counts: Counter[str] = Counter()
    for root_key, p in formal_artifact_files(cfg):
        text = p.read_text("utf-8", errors="replace")
        meta, _body = split_frontmatter(text)
        status = str(meta.get("lifecycle_status") or meta.get("status") or "").strip().strip('"')
        issues: list[str] = []
        actions: list[str] = []
        if not str(meta.get("lifecycle_status") or "").strip():
            issues.append("missing_lifecycle_status")
            actions.append("add_lifecycle_status")
        elif status not in LIFECYCLE_STATUSES:
            issues.append("invalid_lifecycle_status")
            actions.append("normalize_lifecycle_status")
        evidence = meta.get("evidence_from", meta.get("supported_by", []))
        if not isinstance(evidence, list) or len(evidence) == 0:
            issues.append("missing_evidence_from")
            actions.append("demote_to_needs_evidence")
        output_status = str(meta.get("article_maturity") or meta.get("publish_status") or "").lower()
        if root_key == "outputs" and ("needs_revision" in output_status or "rejected" in output_status):
            issues.append("output_not_reusable")
            actions.append("demote_to_needs_revision")
        if issues:
            for issue in issues:
                counts[issue] += 1
            items.append({
                "file": str(p.relative_to(base)),
                "layer": root_key,
                "lifecycle_status": status,
                "issues": issues,
                "recommended_actions": sorted(set(actions)),
            })
    return {
        "artifact_count": len(formal_artifact_files(cfg)),
        "issue_count": len(items),
        "issue_type_counts": dict(counts),
        "items": items,
    }


def render_lifecycle_audit(result: dict[str, Any]) -> str:
    lines = [
        "# Lifecycle Audit",
        "",
        "---",
        f"updated_at: {date.today().isoformat()}",
        "stage: system",
        f"status: {'needs_action' if result['issue_count'] else 'clear'}",
        "---",
        "",
        "## Summary",
        "",
        f"- artifact_count: {result['artifact_count']}",
        f"- issue_count: {result['issue_count']}",
    ]
    for key, value in sorted(result["issue_type_counts"].items()):
        lines.append(f"- {key}: {value}")
    lines += ["", "## Items", ""]
    if not result["items"]:
        lines.append("- None.")
    for item in result["items"][:500]:
        lines.append(f"- `{item['file']}`: {', '.join(item['issues'])}; action={', '.join(item['recommended_actions'])}")
    return "\n".join(lines).rstrip() + "\n"


def knowledge_health_audit(cfg: dict[str, Any]) -> dict[str, Any]:
    base = Path(cfg["ai_knowledge_base"])
    today = date.today()
    items = []
    counts: Counter[str] = Counter()
    for root_key, p in formal_artifact_files(cfg):
        text = p.read_text("utf-8", errors="replace")
        meta, _body = split_frontmatter(text)
        health = str(meta.get("health_status") or "").strip().strip('"')
        reviewed = _parse_date(meta.get("last_health_reviewed_at")) or _parse_date(meta.get("updated_at")) or _parse_date(meta.get("created_at"))
        interval = _artifact_review_interval_days(root_key, p, meta, text)
        issues: list[str] = []
        actions: list[str] = []
        if not health:
            issues.append("missing_health_status")
            actions.append("add_health_status_review_due")
        elif health not in HEALTH_STATUSES:
            issues.append("invalid_health_status")
            actions.append("normalize_health_status")
        elif health != "healthy":
            issues.append(health)
            actions.append("perform_health_review")
        if not _parse_date(meta.get("updated_at")):
            issues.append("missing_updated_at")
            actions.append("repair_updated_at")
        if reviewed is None:
            issues.append("missing_review_date")
            actions.append("perform_health_review")
        else:
            age = (today - reviewed).days
            if age > interval:
                issues.append("review_due")
                actions.append("perform_health_review")
        if has_high_risk(text) and (reviewed is None or (today - reviewed).days > 14):
            issues.append("stale_fact_risk")
            actions.append("verify_or_demote_to_needs_evidence")
        evidence = meta.get("evidence_from", meta.get("supported_by", []))
        if not isinstance(evidence, list) or len(evidence) == 0:
            issues.append("weak_evidence")
            actions.append("mark_needs_evidence")
        if issues:
            for issue in issues:
                counts[issue] += 1
            items.append({
                "file": str(p.relative_to(base)),
                "layer": root_key,
                "health_status": health,
                "review_interval_days": interval,
                "issues": sorted(set(issues)),
                "recommended_actions": sorted(set(actions)),
            })
    return {
        "artifact_count": len(formal_artifact_files(cfg)),
        "issue_count": len(items),
        "issue_type_counts": dict(counts),
        "items": items,
    }


def render_knowledge_health(result: dict[str, Any]) -> str:
    lines = [
        "# Knowledge Health Audit",
        "",
        "---",
        f"updated_at: {date.today().isoformat()}",
        "stage: system",
        f"status: {'needs_action' if result['issue_count'] else 'healthy'}",
        "---",
        "",
        "## Summary",
        "",
        f"- artifact_count: {result['artifact_count']}",
        f"- issue_count: {result['issue_count']}",
    ]
    for key, value in sorted(result["issue_type_counts"].items()):
        lines.append(f"- {key}: {value}")
    lines += ["", "## Items", ""]
    if not result["items"]:
        lines.append("- None.")
    for item in result["items"][:500]:
        lines.append(f"- `{item['file']}`: {', '.join(item['issues'])}; action={', '.join(item['recommended_actions'])}")
    return "\n".join(lines).rstrip() + "\n"


def _frontmatter_value_line(key: str, value: str) -> str:
    return f'{key}: "{value}"'


def _set_frontmatter_field(text: str, key: str, value: str, after_keys: list[str] | None = None) -> tuple[str, bool]:
    if not text.startswith("---\n"):
        return text, False
    end = text.find("\n---", 4)
    if end == -1:
        return text, False
    fm_raw = text[4:end].strip("\n")
    body = text[end + len("\n---"):]
    lines = fm_raw.splitlines()
    new_line = _frontmatter_value_line(key, value)
    for i, line in enumerate(lines):
        if re.match(rf"^{re.escape(key)}:\s*", line):
            if line == new_line:
                return text, False
            lines[i] = new_line
            return "---\n" + "\n".join(lines).rstrip() + "\n---" + body, True
    insert_at = len(lines)
    for candidate in after_keys or []:
        for i, line in enumerate(lines):
            if re.match(rf"^{re.escape(candidate)}:\s*", line):
                insert_at = i + 1
    lines.insert(insert_at, new_line)
    return "---\n" + "\n".join(lines).rstrip() + "\n---" + body, True


def _initial_lifecycle_status(root_key: str, path: Path, meta: dict[str, Any]) -> str:
    current = str(meta.get("status") or "").strip().strip('"')
    if current in LIFECYCLE_STATUSES:
        return current
    maturity = str(meta.get("article_maturity") or "").strip().strip('"')
    output_type = str(meta.get("output_type") or "").strip()
    if root_key == "outputs":
        if maturity == "publishable_draft":
            return "active"
        if maturity == "article_draft" or "文章草稿" in output_type:
            return "draft"
        if "复盘" in output_type or "review" in output_type.lower():
            return "active"
        return "draft"
    if root_key == "topic_pages":
        return "active"
    if root_key == "reusable_assets":
        return "active"
    return "draft"


def initialize_lifecycle_health(cfg: dict[str, Any], apply: bool = False) -> dict[str, Any]:
    base = Path(cfg["ai_knowledge_base"])
    today = date.today().isoformat()
    planned = []
    changed_count = 0
    for root_key, p in formal_artifact_files(cfg):
        raw = p.read_text("utf-8", errors="replace")
        meta, _body = split_frontmatter(raw)
        if not meta:
            continue
        lifecycle = str(meta.get("lifecycle_status") or "").strip().strip('"') or _initial_lifecycle_status(root_key, p, meta)
        if lifecycle not in LIFECYCLE_STATUSES:
            lifecycle = _initial_lifecycle_status(root_key, p, meta)
        fields = [
            ("lifecycle_status", lifecycle, ["status"]),
            ("health_status", str(meta.get("health_status") or "").strip().strip('"') or "review_due", ["lifecycle_status"]),
            ("last_health_reviewed_at", str(meta.get("last_health_reviewed_at") or "").strip().strip('"') or today, ["health_status"]),
            ("next_review_at", str(meta.get("next_review_at") or "").strip().strip('"') or today, ["last_health_reviewed_at"]),
            ("updated_at", today, ["created_at"]),
        ]
        fixed = raw
        changed_fields = []
        for key, value, after_keys in fields:
            fixed2, changed = _set_frontmatter_field(fixed, key, value, after_keys)
            if changed:
                changed_fields.append(key)
                fixed = fixed2
        if changed_fields:
            planned.append({"file": str(p.relative_to(base)), "fields": changed_fields})
            if apply:
                p.write_text(fixed, encoding="utf-8")
                changed_count += 1
    normalize = None
    if apply and changed_count:
        normalize = normalize_filename_dates(cfg, apply=True, touch_updated_at=False)
    return {
        "apply": apply,
        "artifact_count": len(formal_artifact_files(cfg)),
        "metadata_change_count": len(planned),
        "written_count": changed_count,
        "planned": planned,
        "normalize": normalize,
    }


def quality_gate(cfg: dict[str, Any]) -> dict[str, Any]:
    template_issues = []
    # Template for 10-layer files: 20 fields in exact order
    _10_TEMPLATE = ["stage", "status", "theme_cluster", "tags", "related_sources",
                    "related_topics", "related_assets", "related_outputs", "moc",
                    "obsidian_links_updated", "account", "author", "processed_at",
                    "published_at", "saved_at", "source_file", "source_type", "url",
                    "created_at", "updated_at"]
    _10_ROOT = kb_path(cfg, "source_refinements")
    if _10_ROOT.exists():
        for p in collect_markdown_files(_10_ROOT):
            raw = p.read_text("utf-8", errors="ignore")
            if not raw.startswith("---"):
                continue
            parts2 = raw.split("---", 2)
            if len(parts2) < 3:
                continue
            fm_keys = []
            for line in parts2[1].split(chr(10)):
                m2 = re.match(r"^(\w[\w_]*):", line)
                if m2 and not line.startswith(" ") and not line.startswith(chr(9)):
                    fm_keys.append(m2.group(1))
            if fm_keys == _10_TEMPLATE:
                continue
            rel = str(p.relative_to(Path(cfg["ai_knowledge_base"])))
            if len(fm_keys) != len(_10_TEMPLATE):
                extra = [k for k in fm_keys if k not in _10_TEMPLATE]
                missing = [k for k in _10_TEMPLATE if k not in fm_keys]
                template_issues.append({"file": rel, "error": f"field_mismatch: extra={extra}, missing={missing}"})
            else:
                for i, (a, b) in enumerate(zip(fm_keys, _10_TEMPLATE)):
                    if a != b:
                        template_issues.append({"file": rel, "error": f"order_mismatch at pos {i+1}: expected '{b}', got '{a}'"})
                        break
    date_issues = []
    for root_key in ("source_refinements", "topic_pages", "reusable_assets", "outputs"):
        root = kb_path(cfg, root_key)
        if not root.exists():
            continue
        for p in collect_markdown_files(root):
            raw = p.read_text("utf-8", errors="ignore")
            if not raw.startswith("---"):
                continue
            if "created_at:" not in raw:
                rel = str(p.relative_to(Path(cfg["ai_knowledge_base"])))
                date_issues.append(rel)
            elif "updated_at:" not in raw:
                rel = str(p.relative_to(Path(cfg["ai_knowledge_base"])))
                date_issues.append(rel)
    filename_dates = filename_date_audit(cfg)
    source_quality = source_quality_audit(cfg)
    evidence_gaps = evidence_gap_audit(cfg)
    evidence_intake = evidence_intake_audit(cfg)
    editorial_quality = editorial_quality_audit(cfg)
    yaml_issues = []
    for root_key in ("source_refinements", "topic_pages", "reusable_assets", "outputs"):
        root = kb_path(cfg, root_key)
        if not root.exists():
            continue
        for p in collect_markdown_files(root):
            raw = p.read_text("utf-8", errors="ignore")
            if not raw.startswith("---"):
                continue
            parts = raw.split("---", 2)
            if len(parts) < 3:
                continue
            fm = parts[1]
            # Check for Chinese quotes inside YAML double-quoted strings — breaks parsing
            # e.g. "微软发布"组织AI准备度"评价方法论" has Chinese " inside YAML "
            import re as _re
            _in_str = False
            _has_broken_quotes = False
            for _c in fm:
                if _c == '"':
                    _in_str = not _in_str
            # Count odd number of unescaped double-quotes on lines with both Chinese and ASCII quotes
            for _line in fm.split('\n'):
                _ascii_dq = _line.count('"') - _line.count('\"')
                # Find Chinese quotes inside the line
                if ('\u201c' in _line or '\u201d' in _line) and _ascii_dq > 0:
                    _has_broken_quotes = True
            if _has_broken_quotes:
                rel = str(p.relative_to(Path(cfg["ai_knowledge_base"])))
                yaml_issues.append({"file": rel, "error": "chinese_quotes_in_yaml_string"})
                continue
            # Full YAML parse for 20/30/40 files only
                try:
                    import yaml as _y
                    _y.safe_load(fm)
                except Exception as e:
                    rel = str(p.relative_to(Path(cfg["ai_knowledge_base"])))
                    yaml_issues.append({"file": rel, "error": str(e).split('\n')[0][:80]})
    relation = relation_audit(cfg)
    portability = portability_audit(cfg)
    topic_pages = topic_page_audit(cfg)
    assets = asset_audit(cfg)
    lifecycle = lifecycle_audit(cfg)
    health = knowledge_health_audit(cfg)
    outputs = [evaluate_output_file(Path(cfg["ai_knowledge_base"]), p) for p in collect_markdown_files(kb_path(cfg, "outputs"))]
    verification = verification_status(cfg)
    output_review = output_review_status(cfg)
    blockers = []
    warnings = []
    if template_issues:
        blockers.append({"gate": "template", "issue": "10_layer_field_mismatch_or_order", "count": len(template_issues)})
    if date_issues:
        blockers.append({"gate": "dates", "issue": "missing_created_at_or_updated_at", "count": len(date_issues)})
    if filename_dates["issue_count"]:
        blockers.append({"gate": "filename_dates", "issue": "filename_date_prefix_or_date_order_invalid", "count": filename_dates["issue_count"]})
    if yaml_issues:
        blockers.append({"gate": "yaml", "issue": "invalid_yaml_frontmatter", "count": len(yaml_issues)})
    if relation["unresolved_count"]:
        blockers.append({"gate": "relations", "issue": "unresolved_wikilinks", "count": relation["unresolved_count"]})
    if relation["duplicate_aliases"]:
        warnings.append({"gate": "relations", "issue": "duplicate_aliases", "count": len(relation["duplicate_aliases"])})
    if portability["issue_count"]:
        blockers.append({"gate": "portability", "issue": "portable_artifact_leakage", "count": portability["issue_count"]})
    if topic_pages["issue_count"]:
        blockers.append({"gate": "topic_pages", "issue": "invalid_topic_page_shape", "count": topic_pages["issue_count"]})
    if assets["asset_issue_count"]:
        blockers.append({"gate": "assets", "issue": "asset_relation_or_type_issues", "count": assets["asset_issue_count"]})
    if assets["output_issue_count"]:
        blockers.append({"gate": "outputs", "issue": "missing_parent_topic_or_related_assets", "count": assets["output_issue_count"]})
    if lifecycle["issue_count"]:
        warnings.append({"gate": "lifecycle", "issue": "artifacts_need_lifecycle_review_or_demotion_decision", "count": lifecycle["issue_count"]})
    if health["issue_count"]:
        warnings.append({"gate": "knowledge_health", "issue": "artifacts_need_health_review", "count": health["issue_count"]})
    def evidence_minimum(root_key: str, meta: dict[str, Any], path: Path) -> int:
        if root_key == "topic_pages":
            if "MOC" in path.parts or "moc" in {part.lower() for part in path.parts}:
                return 0
            return 3
        if root_key == "reusable_assets":
            asset_type = str(meta.get("asset_type") or "").strip().lower()
            if asset_type in {"case", "case-pattern", "anti-case", "expression", "definition", "distinction", "warning", "metaphor"}:
                return 1
            return 3
        output_type = str(meta.get("output_type") or "").strip().lower()
        status = str(meta.get("status") or "").strip().lower()
        if output_type in {"review", "review-record", "复盘记录"} or status in {"review", "review_record"}:
            return 1
        if output_type in {"feynman", "费曼解释"}:
            return 2
        return 3

    # Check evidence_from in 20/30/40 artifacts with artifact-specific thresholds.
    kb = Path(cfg["ai_knowledge_base"])
    evidence_missing = 0
    evidence_insufficient = 0
    for root_key in ("topic_pages", "reusable_assets", "outputs"):
        root = kb_path(cfg, root_key)
        for p in collect_markdown_files(root):
            meta, _body = split_frontmatter(p.read_text("utf-8", errors="replace"))
            ef = meta.get("evidence_from", meta.get("supported_by", []))
            minimum = evidence_minimum(root_key, meta, p)
            if minimum == 0:
                continue
            if not isinstance(ef, list) or len(ef) == 0:
                evidence_missing += 1
            elif len(ef) < minimum:
                evidence_insufficient += 1
    if evidence_missing:
        blockers.append({"gate": "evidence", "issue": "artifacts_missing_evidence_from_refinements", "count": evidence_missing})
    if evidence_insufficient:
        blockers.append({"gate": "evidence", "issue": "artifacts_insufficient_evidence_for_type", "count": evidence_insufficient})
    needs_revision = [item for item in outputs if item["status"] != "usable"]
    if needs_revision:
        blockers.append({"gate": "output_quality", "issue": "outputs_need_revision", "count": len(needs_revision)})
    if output_review["blocking_review_count"]:
        blockers.append({"gate": "output_review", "issue": "outputs_rejected_or_need_revision", "count": output_review["blocking_review_count"]})
    if output_review["pending_review_count"]:
        warnings.append({"gate": "output_review", "issue": "outputs_pending_rubric_review", "count": output_review["pending_review_count"]})
    if verification["unresolved_output_count"]:
        blockers.append({"gate": "verification", "issue": "unresolved_output_fact_verification", "count": verification["unresolved_output_count"]})
    if verification["pending_count"]:
        warnings.append({"gate": "verification", "issue": "pending_fact_verification", "count": verification["pending_count"]})
    weak_sources = source_quality["tier_counts"].get("D", 0) + source_quality["flag_counts"].get("stale_high_sensitivity", 0)
    if weak_sources:
        warnings.append({"gate": "source_quality", "issue": "low_tier_or_stale_sources_should_not_drive_promotion", "count": weak_sources})
    if evidence_gaps["gap_count"]:
        warnings.append({"gate": "evidence_gaps", "issue": "artifacts_need_bounded_evidence_fill_or_downgrade_decision", "count": evidence_gaps["gap_count"]})
    if not evidence_intake["passed"]:
        warnings.append({"gate": "evidence_intake", "issue": "system_evidence_fill_intake_skeleton_missing", "count": evidence_intake["missing_count"]})
    editorial_attention = editorial_quality["needs_attention_count"]
    if editorial_attention:
        warnings.append({"gate": "editorial_quality", "issue": "outputs_need_editorial_revision_or_argument_repair", "count": editorial_attention})
    return {
        "passed": not blockers,
        "blockers": blockers,
        "warnings": warnings,
        "template_issues": template_issues,
        "date_issues": date_issues,
        "filename_date_issues": filename_dates["issues"],
        "yaml_issues": yaml_issues,
        "summary": {
            "relations": {"unresolved": relation["unresolved_count"], "duplicate_aliases": len(relation["duplicate_aliases"])},
            "portability_issues": portability["issue_count"],
            "topic_page_issues": topic_pages["issue_count"],
            "asset_issues": assets["asset_issue_count"],
            "output_relation_issues": assets["output_issue_count"],
            "outputs_need_revision": len(needs_revision),
            "outputs_pending_review": output_review["pending_review_count"],
            "outputs_blocked_by_review": output_review["blocking_review_count"],
            "verification_pending": verification["pending_count"],
            "verification_unresolved_outputs": verification["unresolved_output_count"],
            "filename_date_issues": filename_dates["issue_count"],
            "lifecycle_issues": lifecycle["issue_count"],
            "knowledge_health_issues": health["issue_count"],
            "source_quality_tiers": source_quality["tier_counts"],
            "source_quality_flags": source_quality["flag_counts"],
            "evidence_gap_count": evidence_gaps["gap_count"],
            "evidence_gap_priorities": evidence_gaps["priority_counts"],
            "evidence_gap_types": evidence_gaps["gap_type_counts"],
            "evidence_intake_passed": evidence_intake["passed"],
            "evidence_intake_missing": evidence_intake["missing_count"],
            "editorial_quality_statuses": editorial_quality["status_counts"],
            "editorial_weak_dimensions": editorial_quality["weak_dimension_counts"],
        },
    }


def render_quality_gate(result: dict[str, Any]) -> str:
    lines = [
        "# Quality Gate",
        "",
        "---",
        f"updated_at: {date.today().isoformat()}",
        "stage: system",
        f"status: {'passed' if result['passed'] else 'blocked'}",
        "---",
        "",
        "## Summary",
        "",
        f"- passed: {str(result['passed']).lower()}",
    ]
    for key, value in result["summary"].items():
        lines.append(f"- {key}: {value}")
    lines += ["", "## Blockers", ""]
    if not result["blockers"]:
        lines.append("- None.")
    for item in result["blockers"]:
        lines.append(f"- {item['gate']}: {item['issue']} ({item['count']})")
    lines += ["", "## Warnings", ""]
    if not result["warnings"]:
        lines.append("- None.")
    for item in result["warnings"]:
        lines.append(f"- {item['gate']}: {item['issue']} ({item['count']})")
    return "\n".join(lines).rstrip() + "\n"


def package_lint() -> dict[str, Any]:
    return lint_release_package(SKILL_ROOT)


def cmd_init(args: argparse.Namespace) -> None:
    config = args.config
    if config.exists():
        cfg = load_config(config)
    else:
        if not args.ai_knowledge_base:
            raise SystemExit("--ai-knowledge-base is required when creating a config")
        cfg = {
            "name": args.name,
            "version": 1,
            "language": args.language,
            "researcher": {
                "id": args.researcher_id or slug(args.name),
                "name": args.researcher_name or args.name,
                "domain": args.research_domain,
                "role": "researcher",
                "isolation": "independent_workspace",
                "shared_methods": [],
            },
            "source_libraries": {"ebooks": args.ebooks, "articles": args.articles, "public_accounts": args.public_accounts},
            "ai_knowledge_base": args.ai_knowledge_base,
            "mapping": {"system": args.system_dir, "source_refinements": args.source_refinements_dir, "topic_pages": args.topic_pages_dir, "reusable_assets": args.reusable_assets_dir, "outputs": args.outputs_dir},
            "source_refinement_subdirs": {"ebooks": args.ebooks_subdir, "articles": args.articles_subdir, "public_accounts": args.public_accounts_subdir},
            "topic_page_subdirs": {"pages": args.topic_pages_subdir, "moc": args.moc_subdir},
            "reusable_asset_subdirs": {"methods": args.methods_subdir, "cases": args.cases_subdir, "expressions": args.expressions_subdir, "frameworks": args.frameworks_subdir},
            "output_subdirs": {"feynman": args.feynman_subdir, "article_drafts": args.article_drafts_subdir, "solution_materials": args.solution_materials_subdir, "reviews": args.reviews_subdir},
            "promotion_rules": {"min_sources_for_topic": 3, "allow_user_requested_topic": True, "fact_check_before_public_output": True},
            "pipeline": {"chunk_size": 5000, "default_batch_size": 10, "max_attempts": 3, "lease_minutes": 120, "runtime_storage": "local", "runtime_namespace": args.researcher_id or slug(args.name), "artifact_retention_days": 7},
        }
    if args.apply:
        require_valid_config(cfg)
        ensure_tree(cfg)
        write_config(config, cfg)
    print(json.dumps({"config": str(config), "apply": args.apply, "ai_knowledge_base": cfg["ai_knowledge_base"]}, ensure_ascii=False, indent=2))


def cmd_audit(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    require_valid_config(cfg)
    print(json.dumps(audit(cfg, include_hashes=args.hashes), ensure_ascii=False, indent=2))


def cmd_normalize_index(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    require_valid_config(cfg)
    index = system_file(cfg, "processed-index.jsonl")
    rows, errors = read_index_objects(index)
    normalized = [normalize_index_obj(row) for row in rows]
    seen = Counter(row["source_id"] for row in normalized)
    duplicates = [source_id for source_id, count in seen.items() if count > 1]
    result = {"input_rows": len(rows), "parse_errors": errors, "duplicate_source_ids": duplicates, "fields": INDEX_FIELDS}
    if args.apply:
        backup = backup_file(index)
        write_jsonl(index, normalized)
        result["written"] = str(index)
        result["backup"] = str(backup) if backup else None
        append_operation_log(cfg, "normalize-index", f"Normalized {len(normalized)} rows, {len(result.get('parse_errors', []))} errors", 
                             {"rows": len(normalized), "errors": len(result.get('parse_errors', []))})
    else:
        if args.out:
            write_jsonl(args.out, normalized)
            result["written_preview"] = str(args.out)
        else:
            result["preview_rows"] = normalized[:5]
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_promote(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    require_valid_config(cfg)
    if args.apply:
        ensure_tree(cfg)
    rows, errors = read_index_objects(system_file(cfg, "processed-index.jsonl"))
    normalized = [normalize_index_obj(row) for row in rows]
    cluster_rules = args.cluster_rules
    if cluster_rules is None:
        configured = cfg.get("promotion_rules", {}).get("cluster_rules")
        if configured:
            candidate = Path(configured)
            cluster_rules = candidate if candidate.is_absolute() else Path(cfg["ai_knowledge_base"]) / candidate
    rules = load_cluster_rules(cluster_rules)
    if "default_min_sources" not in rules:
        rules["default_min_sources"] = cfg.get("promotion_rules", {}).get("min_sources_for_topic", 3)
    clusters = cluster_rows(normalized, rules)
    result = {"index_rows": len(normalized), "parse_errors": errors, "clusters": clusters}
    if args.apply:
        system_file(cfg, "topic-clusters.md").write_text(render_topic_clusters(clusters), encoding="utf-8")
        system_file(cfg, "promotion-review.md").write_text(render_promotion_review(clusters, len(normalized)), encoding="utf-8")
        system_file(cfg, "asset-output-candidates.md").write_text(render_asset_output_candidates(clusters), encoding="utf-8")
        append_promotion_decisions(cfg, promotion_decision_rows(clusters, decision_context="promote"))
        result["written"] = [str(system_file(cfg, "topic-clusters.md")), str(system_file(cfg, "promotion-review.md")), str(system_file(cfg, "asset-output-candidates.md"))]
        write_run_checkpoint(cfg, objective="promotion_review", stage="medium_cost_review", cost_tier="medium", status="waiting_for_approval", clusters=clusters, written=result["written"])
        result["checkpoint"] = str(system_file(cfg, "active-run-state.json"))
        if args.create_stubs:
            result["stub_artifacts"] = write_stub_artifacts(cfg, clusters)
        append_operation_log(cfg, "promote", f"Generated {len(clusters)} clusters from {len(normalized)} index rows",
                             {"clusters": len(clusters), "index_rows": len(normalized)})
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_verification_queue(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    require_valid_config(cfg)
    items = verification_items(cfg)
    if args.apply:
        write_jsonl(system_file(cfg, "verification-queue.jsonl"), items)
    print(json.dumps({"items": len(items), "written": str(system_file(cfg, "verification-queue.jsonl")) if args.apply else None, "queue": items}, ensure_ascii=False, indent=2))


def cmd_verify_claim(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    require_valid_config(cfg)
    row = verification_result_row(args)
    append_verification_result(cfg, row)
    status = verification_status(cfg)
    if args.apply_status:
        system_file(cfg, "verification-status.md").write_text(render_verification_status(status), encoding="utf-8")
    print(json.dumps({"written": str(system_file(cfg, "verification-results.jsonl")), "status_written": str(system_file(cfg, "verification-status.md")) if args.apply_status else None, "result": row, "pending_count": status["pending_count"], "unresolved_output_count": status["unresolved_output_count"]}, ensure_ascii=False, indent=2))


def cmd_verification_status(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    require_valid_config(cfg)
    result = verification_status(cfg)
    if args.apply:
        system_file(cfg, "verification-status.md").write_text(render_verification_status(result), encoding="utf-8")
    print(json.dumps({"written": str(system_file(cfg, "verification-status.md")) if args.apply else None, **result}, ensure_ascii=False, indent=2))


def cmd_evaluate_outputs(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    require_valid_config(cfg)
    base = Path(cfg["ai_knowledge_base"])
    output_root = kb_path(cfg, "outputs")
    results = [evaluate_output_file(base, p) for p in collect_markdown_files(output_root)]
    if args.apply:
        system_file(cfg, "output-quality-review.md").write_text(render_output_quality(results), encoding="utf-8")
    print(json.dumps({"outputs": len(results), "written": str(system_file(cfg, "output-quality-review.md")) if args.apply else None, "results": results}, ensure_ascii=False, indent=2))


def cmd_audit_editorial_quality(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    require_valid_config(cfg)
    result = editorial_quality_audit(cfg)
    if args.apply:
        system_file(cfg, "editorial-quality-review.md").write_text(render_editorial_quality(result), encoding="utf-8")
        append_operation_log(cfg, "audit-editorial-quality", f"Reviewed {result['output_count']} outputs; needs_attention={result['needs_attention_count']}",
                             {"outputs": result["output_count"], "needs_attention": result["needs_attention_count"], "statuses": result["status_counts"]})
    print(json.dumps({"written": str(system_file(cfg, "editorial-quality-review.md")) if args.apply else None, **result}, ensure_ascii=False, indent=2))
    if args.strict and result["needs_attention_count"]:
        raise SystemExit(2)


def cmd_output_review_status(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    require_valid_config(cfg)
    result = output_review_status(cfg)
    if args.apply:
        system_file(cfg, "output-review-status.md").write_text(render_output_review_status(result), encoding="utf-8")
    print(json.dumps({"written": str(system_file(cfg, "output-review-status.md")) if args.apply else None, **result}, ensure_ascii=False, indent=2))


def cmd_record_output_review(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    require_valid_config(cfg)
    row = output_review_result_row(args)
    append_output_review_result(cfg, row)
    status = output_review_status(cfg)
    if args.apply_status:
        system_file(cfg, "output-review-status.md").write_text(render_output_review_status(status), encoding="utf-8")
    print(json.dumps({"written": str(system_file(cfg, "output-review-results.jsonl")), "status_written": str(system_file(cfg, "output-review-status.md")) if args.apply_status else None, "result": row, "pending_review_count": status["pending_review_count"], "blocking_review_count": status["blocking_review_count"]}, ensure_ascii=False, indent=2))


def cmd_audit_assets(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    require_valid_config(cfg)
    result = asset_audit(cfg)
    if args.apply:
        system_file(cfg, "asset-relation-audit.md").write_text(render_asset_audit(result), encoding="utf-8")
    print(json.dumps({"written": str(system_file(cfg, "asset-relation-audit.md")) if args.apply else None, **result}, ensure_ascii=False, indent=2))


def cmd_audit_source_quality(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    require_valid_config(cfg)
    result = source_quality_audit(cfg)
    if args.apply:
        system_file(cfg, "source-quality-audit.md").write_text(render_source_quality_audit(result), encoding="utf-8")
    print(json.dumps({"written": str(system_file(cfg, "source-quality-audit.md")) if args.apply else None, **result}, ensure_ascii=False, indent=2))
    if args.strict and result["tier_counts"].get("D", 0):
        raise SystemExit(2)


def cmd_audit_lifecycle(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    require_valid_config(cfg)
    result = lifecycle_audit(cfg)
    if args.apply:
        system_file(cfg, "lifecycle-audit.md").write_text(render_lifecycle_audit(result), encoding="utf-8")
    print(json.dumps({"written": str(system_file(cfg, "lifecycle-audit.md")) if args.apply else None, **result}, ensure_ascii=False, indent=2))
    if args.strict and result["issue_count"]:
        raise SystemExit(2)


def cmd_audit_knowledge_health(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    require_valid_config(cfg)
    result = knowledge_health_audit(cfg)
    if args.apply:
        system_file(cfg, "knowledge-health.md").write_text(render_knowledge_health(result), encoding="utf-8")
    print(json.dumps({"written": str(system_file(cfg, "knowledge-health.md")) if args.apply else None, **result}, ensure_ascii=False, indent=2))
    if args.strict and result["issue_count"]:
        raise SystemExit(2)


def cmd_init_lifecycle_health(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    require_valid_config(cfg)
    result = initialize_lifecycle_health(cfg, apply=args.apply)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_audit_relations(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    require_valid_config(cfg)
    result = relation_audit(cfg)
    if args.apply:
        system_file(cfg, "relation-audit.md").write_text(render_relation_audit(result), encoding="utf-8")
    print(json.dumps({"written": str(system_file(cfg, "relation-audit.md")) if args.apply else None, **result}, ensure_ascii=False, indent=2))


def cmd_audit_portability(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    require_valid_config(cfg)
    result = portability_audit(cfg)
    if args.apply:
        system_file(cfg, "portability-audit.md").write_text(render_portability_audit(result), encoding="utf-8")
    print(json.dumps({"written": str(system_file(cfg, "portability-audit.md")) if args.apply else None, **result}, ensure_ascii=False, indent=2))


def cmd_audit_topic_pages(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    require_valid_config(cfg)
    result = topic_page_audit(cfg)
    if args.apply:
        system_file(cfg, "topic-page-audit.md").write_text(render_topic_page_audit(result), encoding="utf-8")
    print(json.dumps({"written": str(system_file(cfg, "topic-page-audit.md")) if args.apply else None, **result}, ensure_ascii=False, indent=2))


def cmd_audit_filename_dates(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    require_valid_config(cfg)
    result = filename_date_audit(cfg)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_normalize_filename_dates(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    require_valid_config(cfg)
    result = normalize_filename_dates(cfg, apply=args.apply, touch_updated_at=args.touch_updated_at)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_quality_gate(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    require_valid_config(cfg)
    result = quality_gate(cfg)
    if args.apply:
        system_file(cfg, "quality-gate.md").write_text(render_quality_gate(result), encoding="utf-8")
        append_operation_log(cfg, "quality-gate", f"Gate {'passed' if result['passed'] else 'blocked'}: {result['summary']}",
                             {"passed": result["passed"], "blockers": len(result.get("blockers", [])), "warnings": len(result.get("warnings", []))})
    print(json.dumps({"written": str(system_file(cfg, "quality-gate.md")) if args.apply else None, **result}, ensure_ascii=False, indent=2))
    if args.strict and not result["passed"]:
        raise SystemExit(2)


def cmd_audit_evidence_gaps(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    require_valid_config(cfg)
    result = evidence_gap_audit(cfg)
    if args.apply:
        system_file(cfg, "evidence-gap-registry.md").write_text(render_evidence_gap_registry(result), encoding="utf-8")
        append_operation_log(cfg, "audit-evidence-gaps", f"Found {result['gap_count']} bounded evidence gaps",
                             {"gap_count": result["gap_count"], "priorities": result["priority_counts"]})
    print(json.dumps({"written": str(system_file(cfg, "evidence-gap-registry.md")) if args.apply else None, **result}, ensure_ascii=False, indent=2))
    if args.strict and result["gap_count"]:
        raise SystemExit(2)


def cmd_init_evidence_intake(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    require_valid_config(cfg)
    result = init_evidence_intake(cfg, apply=args.apply)
    audit = evidence_intake_audit(cfg)
    if args.apply:
        system_file(cfg, "evidence-intake-audit.md").write_text(render_evidence_intake_audit(audit), encoding="utf-8")
        system_file(cfg, "source-capabilities.md").write_text(render_source_capabilities(cfg, audit), encoding="utf-8")
        append_operation_log(cfg, "init-evidence-intake", f"Initialized evidence intake skeleton; missing after init={audit['missing_count']}",
                             {"created": result["created_count"], "missing_after_init": audit["missing_count"]})
    print(json.dumps({"written": [str(system_file(cfg, "evidence-intake-audit.md")), str(system_file(cfg, "source-capabilities.md"))] if args.apply else [], **result, "audit": audit}, ensure_ascii=False, indent=2))


def cmd_audit_evidence_intake(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    require_valid_config(cfg)
    result = evidence_intake_audit(cfg)
    if args.apply:
        system_file(cfg, "evidence-intake-audit.md").write_text(render_evidence_intake_audit(result), encoding="utf-8")
        system_file(cfg, "source-capabilities.md").write_text(render_source_capabilities(cfg, result), encoding="utf-8")
    print(json.dumps({"written": [str(system_file(cfg, "evidence-intake-audit.md")), str(system_file(cfg, "source-capabilities.md"))] if args.apply else [], **result}, ensure_ascii=False, indent=2))
    if args.strict and not result["passed"]:
        raise SystemExit(2)


def cmd_gate_10(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    require_valid_config(cfg)
    result = gate_10(cfg, batch_name=args.batch, batch_threshold=args.threshold)
    if args.apply:
        system_file(cfg, "gate-10.md").write_text(render_gate_10(result), encoding="utf-8")
        result["written"] = str(system_file(cfg, "gate-10.md"))
        append_operation_log(cfg, "gate-10", f"Scanned {result['scanned']} refinements, {result['passed_count']} passed, {result['failed_count']} failed, {result.get('blocker_count', 0)} blockers", 
                             {"scanned": result["scanned"], "passed": result["passed_count"], "failed": result["failed_count"], "blockers": result.get("blocker_count", 0)})
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["passed"] and args.strict:
        raise SystemExit(2)


def cmd_check_refinement(args: argparse.Namespace) -> None:
    """Check a single refinement file and return JSON result. Used by kb_pipeline.py."""
    path = Path(args.file)
    if not path.exists():
        print(json.dumps({"passed": False, "blockers": ["file_not_found"]}))
        raise SystemExit(2)
    try:
        result = check_refinement(path)
    except Exception as e:
        print(json.dumps({"passed": False, "blockers": [f"check_error: {e}"]}))
        raise SystemExit(2)
    print(json.dumps({"passed": result["passed"], "blockers": result.get("blockers", []), "warnings": result.get("warnings", [])}, ensure_ascii=False))
    if not result["passed"]:
        raise SystemExit(2)




def cmd_sync_relations(args: argparse.Namespace) -> None:
    """Sync related_sources for all refinements based on theme_cluster matching."""
    cfg = load_config(args.config)
    require_valid_config(cfg)
    ref_dir = kb_path(cfg, "source_refinements")
    if not ref_dir.exists():
        print(json.dumps({"error": "source_refinements_dir_not_found"}))
        raise SystemExit(2)
    
    # Build cluster map from frontmatter
    from collections import defaultdict
    cluster_map = defaultdict(list)
    files_list = []
    for f in sorted(collect_markdown_files(ref_dir)):
        text = f.read_text("utf-8", errors="replace")
        m = re.search(r'^theme_cluster:\s*"([^"]+)"', text, re.M)
        cluster = m.group(1) if m else "AI知识管理"
        fname = f.stem
        cluster_map[cluster].append(fname)
        files_list.append((f, cluster, fname))
    
    # For each file, set related_sources to up to 5 peers in same cluster
    updated = 0
    for f, cluster, fname in files_list:
        peers = [n for n in cluster_map[cluster] if n != fname]
        if not peers:
            continue
        selected = peers[:5]
        link_lines = "\n".join(f'  - "[[{p}]]"' for p in selected)
        
        text = f.read_text("utf-8", errors="replace")
        old_pattern = re.compile(r'^related_sources:\s*\[\s*\]', re.M)
        if old_pattern.search(text):
            text = old_pattern.sub(f'related_sources:\n{link_lines}', text)
            f.write_text(text, encoding="utf-8")
            updated += 1
    
    result = {"updated": updated}
    print(json.dumps(result, ensure_ascii=False, indent=2))



def cmd_package_lint(args: argparse.Namespace) -> None:
    result = package_lint()
    if args.apply and result["passed"]:
        refresh_source_hash(SKILL_ROOT)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.strict and not result["passed"]:
        raise SystemExit(2)


def doctor(cfg: dict[str, Any], config_path: Path) -> dict[str, Any]:
    errors = validate_config(cfg)
    source_checks = []
    for name, raw in sorted(cfg.get("source_libraries", {}).items()):
        if not raw:
            source_checks.append({"name": name, "configured": False, "exists": False, "readable": False})
            continue
        path = Path(raw).expanduser()
        source_checks.append({"name": name, "configured": True, "exists": path.is_dir(), "readable": path.is_dir()})
    base = Path(cfg.get("ai_knowledge_base", "")).expanduser() if cfg.get("ai_knowledge_base") else None
    missing_configured_sources = any(item["configured"] and not item["exists"] for item in source_checks)
    return {
        "healthy": not errors and not missing_configured_sources and bool(base) and (base.exists() or base.parent.exists()),
        "config": str(config_path),
        "config_errors": errors,
        "ai_knowledge_base": {"path": str(base) if base else "", "exists": bool(base and base.exists()), "parent_exists": bool(base and base.parent.exists())},
        "source_libraries": source_checks,
        "python": sys.version.split()[0],
    }


def cmd_validate_config(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    errors = validate_config(cfg)
    print(json.dumps({"valid": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(2)


def cmd_doctor(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    result = doctor(cfg, args.config)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["healthy"]:
        raise SystemExit(2)


def cmd_run(args: argparse.Namespace) -> None:
    """Run deterministic stages and expose the cognitive work still pending."""
    cfg = load_config(args.config)
    require_valid_config(cfg)
    if args.apply:
        ensure_tree(cfg)
    audit_result = audit(cfg, include_hashes=args.hashes)
    rows, parse_errors = read_index_objects(system_file(cfg, "processed-index.jsonl"))
    normalized = [normalize_index_obj(row) for row in rows]
    configured = cfg.get("promotion_rules", {}).get("cluster_rules")
    rules_path = None
    if configured:
        candidate = Path(configured)
        rules_path = candidate if candidate.is_absolute() else Path(cfg["ai_knowledge_base"]) / candidate
    rules = load_cluster_rules(rules_path)
    rules.setdefault("default_min_sources", cfg.get("promotion_rules", {}).get("min_sources_for_topic", 3))
    clusters = cluster_rows(normalized, rules)
    verification = verification_items(cfg)
    verification_state = verification_status(cfg)
    output_review_state = output_review_status(cfg)
    output_root = kb_path(cfg, "outputs")
    evaluations = [evaluate_output_file(Path(cfg["ai_knowledge_base"]), p) for p in collect_markdown_files(output_root)]
    portability = portability_audit(cfg)
    topic_pages = topic_page_audit(cfg)
    gate10 = gate_10(cfg)
    written: list[str] = []
    if args.apply:
        if gate10.get("passed"):
            system_file(cfg, "gate-10.md").write_text(render_gate_10(gate10), encoding="utf-8")
            written.append(str(system_file(cfg, "gate-10.md")))
            append_operation_log(cfg, "gate-10", f"Scanned {gate10['scanned']} refinements, {gate10['passed_count']} passed",
                                 {"scanned": gate10["scanned"], "passed": gate10["passed_count"], "failed": gate10.get("failed_count", 0)})
        system_file(cfg, "topic-clusters.md").write_text(render_topic_clusters(clusters), encoding="utf-8")
        system_file(cfg, "promotion-review.md").write_text(render_promotion_review(clusters, len(normalized)), encoding="utf-8")
        system_file(cfg, "asset-output-candidates.md").write_text(render_asset_output_candidates(clusters), encoding="utf-8")
        write_jsonl(system_file(cfg, "verification-queue.jsonl"), verification)
        system_file(cfg, "verification-status.md").write_text(render_verification_status(verification_state), encoding="utf-8")
        system_file(cfg, "output-quality-review.md").write_text(render_output_quality(evaluations), encoding="utf-8")
        system_file(cfg, "output-review-status.md").write_text(render_output_review_status(output_review_state), encoding="utf-8")
        system_file(cfg, "portability-audit.md").write_text(render_portability_audit(portability), encoding="utf-8")
        system_file(cfg, "topic-page-audit.md").write_text(render_topic_page_audit(topic_pages), encoding="utf-8")
        append_promotion_decisions(cfg, promotion_decision_rows(clusters, decision_context="run"))
        gate = quality_gate(cfg)
        system_file(cfg, "quality-gate.md").write_text(render_quality_gate(gate), encoding="utf-8")
        append_operation_log(cfg, "run", f"Audit: {audit_result['source_count']} sources, {audit_result['unprocessed_count']} unprocessed. Clusters: {len(clusters)}. Gate: {gate['passed']}.",
                             {"sources": audit_result["source_count"], "unprocessed": audit_result["unprocessed_count"], "clusters": len(clusters), "quality_gate_passed": gate["passed"]})
        written = [str(system_file(cfg, name)) for name in ("topic-clusters.md", "promotion-review.md", "asset-output-candidates.md", "verification-queue.jsonl", "verification-status.md", "output-quality-review.md", "output-review-status.md", "portability-audit.md", "topic-page-audit.md", "quality-gate.md")]
        write_run_checkpoint(cfg, objective="deterministic_run", stage="medium_cost_review", cost_tier="medium", status="waiting_for_approval", clusters=clusters, written=written)
        obsidian = cfg.get("integrations", {}).get("obsidian", {})
        if obsidian.get("enabled"):
            linker = Path(__file__).with_name("obsidian_linker.py")
            proc = subprocess.run([sys.executable, str(linker), "--config", str(args.config), "--apply"], check=True, text=True, capture_output=True)
            written.extend(json.loads(proc.stdout).get("changed", []))
    print(json.dumps({
        "apply": args.apply,
        "audit": audit_result,
        "processed_index_parse_errors": parse_errors,
        "clusters": len(clusters),
        "verification_items": len(verification),
        "verification_pending": verification_state["pending_count"],
        "verification_unresolved_outputs": verification_state["unresolved_output_count"],
        "outputs_evaluated": len(evaluations),
        "gate10_scanned": gate10.get("scanned", 0),
        "gate10_passed": gate10.get("passed", False),
        "outputs_pending_review": output_review_state["pending_review_count"],
        "outputs_blocked_by_review": output_review_state["blocking_review_count"],
        "portability_issues": portability["issue_count"],
        "topic_page_issues": topic_pages["issue_count"],
        "quality_gate_passed": quality_gate(cfg)["passed"],
        "next_action": (
            "refine_unprocessed_sources" if audit_result["unprocessed_count"]
            else "add_sources" if audit_result["source_count"] == 0
            else "review_promotions_and_outputs"
        ),
        "written": written,
    }, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init")
    p_init.add_argument("--config", required=True, type=Path)
    p_init.add_argument("--ai-knowledge-base")
    p_init.add_argument("--ebooks", default="")
    p_init.add_argument("--articles", default="")
    p_init.add_argument("--public-accounts", default="")
    p_init.add_argument("--name", default="my-knowledge-base")
    p_init.add_argument("--researcher-id")
    p_init.add_argument("--researcher-name")
    p_init.add_argument("--research-domain", default="general research")
    p_init.add_argument("--language", default="zh-CN")
    p_init.add_argument("--system-dir", default=DEFAULT_MAPPING["system"])
    p_init.add_argument("--source-refinements-dir", default=DEFAULT_MAPPING["source_refinements"])
    p_init.add_argument("--topic-pages-dir", default=DEFAULT_MAPPING["topic_pages"])
    p_init.add_argument("--reusable-assets-dir", default=DEFAULT_MAPPING["reusable_assets"])
    p_init.add_argument("--outputs-dir", default=DEFAULT_MAPPING["outputs"])
    p_init.add_argument("--ebooks-subdir", default=DEFAULT_SOURCE_SUBDIRS["ebooks"])
    p_init.add_argument("--articles-subdir", default=DEFAULT_SOURCE_SUBDIRS["articles"])
    p_init.add_argument("--public-accounts-subdir", default=DEFAULT_SOURCE_SUBDIRS["public_accounts"])
    p_init.add_argument("--topic-pages-subdir", default=DEFAULT_TOPIC_PAGE_SUBDIRS["pages"])
    p_init.add_argument("--moc-subdir", default=DEFAULT_TOPIC_PAGE_SUBDIRS["moc"])
    p_init.add_argument("--methods-subdir", default=DEFAULT_REUSABLE_ASSET_SUBDIRS["methods"])
    p_init.add_argument("--cases-subdir", default=DEFAULT_REUSABLE_ASSET_SUBDIRS["cases"])
    p_init.add_argument("--expressions-subdir", default=DEFAULT_REUSABLE_ASSET_SUBDIRS["expressions"])
    p_init.add_argument("--frameworks-subdir", default=DEFAULT_REUSABLE_ASSET_SUBDIRS["frameworks"])
    p_init.add_argument("--feynman-subdir", default=DEFAULT_OUTPUT_SUBDIRS["feynman"])
    p_init.add_argument("--article-drafts-subdir", default=DEFAULT_OUTPUT_SUBDIRS["article_drafts"])
    p_init.add_argument("--solution-materials-subdir", default=DEFAULT_OUTPUT_SUBDIRS["solution_materials"])
    p_init.add_argument("--reviews-subdir", default=DEFAULT_OUTPUT_SUBDIRS["reviews"])
    p_init.add_argument("--apply", action="store_true")
    p_init.set_defaults(func=cmd_init)

    p_audit = sub.add_parser("audit")
    p_audit.add_argument("--config", required=True, type=Path)
    p_audit.add_argument("--hashes", action="store_true")
    p_audit.set_defaults(func=cmd_audit)

    p_norm = sub.add_parser("normalize-index")
    p_norm.add_argument("--config", required=True, type=Path)
    p_norm.add_argument("--out", type=Path)
    p_norm.add_argument("--apply", action="store_true")
    p_norm.set_defaults(func=cmd_normalize_index)

    p_promote = sub.add_parser("promote")
    p_promote.add_argument("--config", required=True, type=Path)
    p_promote.add_argument("--cluster-rules", type=Path)
    p_promote.add_argument("--apply", action="store_true")
    p_promote.add_argument("--create-stubs", action="store_true")
    p_promote.set_defaults(func=cmd_promote)

    p_verify = sub.add_parser("verification-queue")
    p_verify.add_argument("--config", required=True, type=Path)
    p_verify.add_argument("--apply", action="store_true")
    p_verify.set_defaults(func=cmd_verification_queue)

    p_verify_claim = sub.add_parser("verify-claim")
    p_verify_claim.add_argument("--config", required=True, type=Path)
    p_verify_claim.add_argument("--id", required=True)
    p_verify_claim.add_argument("--status", required=True)
    p_verify_claim.add_argument("--claim", default="")
    p_verify_claim.add_argument("--evidence", default="")
    p_verify_claim.add_argument("--note", default="")
    p_verify_claim.add_argument("--verifier", default="codex")
    p_verify_claim.add_argument("--apply-status", action="store_true")
    p_verify_claim.set_defaults(func=cmd_verify_claim)

    p_verify_status = sub.add_parser("verification-status")
    p_verify_status.add_argument("--config", required=True, type=Path)
    p_verify_status.add_argument("--apply", action="store_true")
    p_verify_status.set_defaults(func=cmd_verification_status)

    p_eval = sub.add_parser("evaluate-outputs")
    p_eval.add_argument("--config", required=True, type=Path)
    p_eval.add_argument("--apply", action="store_true")
    p_eval.set_defaults(func=cmd_evaluate_outputs)

    p_editorial_quality = sub.add_parser("audit-editorial-quality")
    p_editorial_quality.add_argument("--config", required=True, type=Path)
    p_editorial_quality.add_argument("--apply", action="store_true")
    p_editorial_quality.add_argument("--strict", action="store_true")
    p_editorial_quality.set_defaults(func=cmd_audit_editorial_quality)

    p_output_review = sub.add_parser("output-review")
    p_output_review.add_argument("--config", required=True, type=Path)
    p_output_review.add_argument("--apply", action="store_true")
    p_output_review.set_defaults(func=cmd_output_review_status)

    p_record_output_review = sub.add_parser("record-output-review")
    p_record_output_review.add_argument("--config", required=True, type=Path)
    p_record_output_review.add_argument("--file", required=True)
    p_record_output_review.add_argument("--status", required=True)
    p_record_output_review.add_argument("--scores", default="")
    p_record_output_review.add_argument("--note", default="")
    p_record_output_review.add_argument("--reviewer", default="codex")
    p_record_output_review.add_argument("--apply-status", action="store_true")
    p_record_output_review.set_defaults(func=cmd_record_output_review)

    p_asset_audit = sub.add_parser("audit-assets")
    p_asset_audit.add_argument("--config", required=True, type=Path)
    p_asset_audit.add_argument("--apply", action="store_true")
    p_asset_audit.set_defaults(func=cmd_audit_assets)

    p_source_quality = sub.add_parser("audit-source-quality")
    p_source_quality.add_argument("--config", required=True, type=Path)
    p_source_quality.add_argument("--apply", action="store_true")
    p_source_quality.add_argument("--strict", action="store_true")
    p_source_quality.set_defaults(func=cmd_audit_source_quality)

    p_evidence_gaps = sub.add_parser("audit-evidence-gaps")
    p_evidence_gaps.add_argument("--config", required=True, type=Path)
    p_evidence_gaps.add_argument("--apply", action="store_true")
    p_evidence_gaps.add_argument("--strict", action="store_true")
    p_evidence_gaps.set_defaults(func=cmd_audit_evidence_gaps)

    p_init_evidence_intake = sub.add_parser("init-evidence-intake")
    p_init_evidence_intake.add_argument("--config", required=True, type=Path)
    p_init_evidence_intake.add_argument("--apply", action="store_true")
    p_init_evidence_intake.set_defaults(func=cmd_init_evidence_intake)

    p_audit_evidence_intake = sub.add_parser("audit-evidence-intake")
    p_audit_evidence_intake.add_argument("--config", required=True, type=Path)
    p_audit_evidence_intake.add_argument("--apply", action="store_true")
    p_audit_evidence_intake.add_argument("--strict", action="store_true")
    p_audit_evidence_intake.set_defaults(func=cmd_audit_evidence_intake)

    p_lifecycle_audit = sub.add_parser("audit-lifecycle")
    p_lifecycle_audit.add_argument("--config", required=True, type=Path)
    p_lifecycle_audit.add_argument("--apply", action="store_true")
    p_lifecycle_audit.add_argument("--strict", action="store_true")
    p_lifecycle_audit.set_defaults(func=cmd_audit_lifecycle)

    p_health_audit = sub.add_parser("audit-knowledge-health")
    p_health_audit.add_argument("--config", required=True, type=Path)
    p_health_audit.add_argument("--apply", action="store_true")
    p_health_audit.add_argument("--strict", action="store_true")
    p_health_audit.set_defaults(func=cmd_audit_knowledge_health)

    p_init_lifecycle_health = sub.add_parser("init-lifecycle-health")
    p_init_lifecycle_health.add_argument("--config", required=True, type=Path)
    p_init_lifecycle_health.add_argument("--apply", action="store_true")
    p_init_lifecycle_health.set_defaults(func=cmd_init_lifecycle_health)

    p_relation_audit = sub.add_parser("audit-relations")
    p_relation_audit.add_argument("--config", required=True, type=Path)
    p_relation_audit.add_argument("--apply", action="store_true")
    p_relation_audit.set_defaults(func=cmd_audit_relations)

    p_portability_audit = sub.add_parser("audit-portability")
    p_portability_audit.add_argument("--config", required=True, type=Path)
    p_portability_audit.add_argument("--apply", action="store_true")
    p_portability_audit.set_defaults(func=cmd_audit_portability)

    p_topic_page_audit = sub.add_parser("audit-topic-pages")
    p_topic_page_audit.add_argument("--config", required=True, type=Path)
    p_topic_page_audit.add_argument("--apply", action="store_true")
    p_topic_page_audit.set_defaults(func=cmd_audit_topic_pages)

    p_filename_dates = sub.add_parser("audit-filename-dates")
    p_filename_dates.add_argument("--config", required=True, type=Path)
    p_filename_dates.set_defaults(func=cmd_audit_filename_dates)

    p_normalize_filename_dates = sub.add_parser("normalize-filename-dates")
    p_normalize_filename_dates.add_argument("--config", required=True, type=Path)
    p_normalize_filename_dates.add_argument("--apply", action="store_true")
    p_normalize_filename_dates.add_argument("--touch-updated-at", action="store_true", help="Set updated_at to today's date while normalizing filenames.")
    p_normalize_filename_dates.set_defaults(func=cmd_normalize_filename_dates)

    p_quality_gate = sub.add_parser("quality-gate")
    p_quality_gate.add_argument("--config", required=True, type=Path)
    p_quality_gate.add_argument("--apply", action="store_true")
    p_quality_gate.add_argument("--strict", action="store_true")
    p_quality_gate.set_defaults(func=cmd_quality_gate)

    p_gate_10 = sub.add_parser("gate-10")
    p_gate_10.add_argument("--config", required=True, type=Path)
    p_gate_10.add_argument("--batch", default=None, help="Batch name for reporting")
    p_gate_10.add_argument("--threshold", type=float, default=0.3, help="Batch model-text repeat threshold (default 0.3)")
    p_gate_10.add_argument("--strict", action="store_true", help="Exit non-zero on failure")
    p_gate_10.add_argument("--apply", action="store_true", help="Write gate-10.md report")
    p_gate_10.set_defaults(func=cmd_gate_10)

    p_check = sub.add_parser("check-refinement")
    p_check.add_argument("--file", required=True, type=str, help="Path to a single refinement markdown file to check")
    p_check.set_defaults(func=cmd_check_refinement)

    p_sync = sub.add_parser("sync-relations")
    p_sync.add_argument("--config", required=True, type=Path)
    p_sync.set_defaults(func=cmd_sync_relations)

    p_package_lint = sub.add_parser("package-lint")
    p_package_lint.add_argument("--strict", action="store_true")
    p_package_lint.add_argument("--apply", action="store_true", help="Write .source_hash after passing")
    p_package_lint.set_defaults(func=cmd_package_lint)

    p_validate = sub.add_parser("validate-config")
    p_validate.add_argument("--config", required=True, type=Path)
    p_validate.set_defaults(func=cmd_validate_config)

    p_doctor = sub.add_parser("doctor")
    p_doctor.add_argument("--config", required=True, type=Path)
    p_doctor.set_defaults(func=cmd_doctor)

    p_run = sub.add_parser("run")
    p_run.add_argument("--config", required=True, type=Path)
    p_run.add_argument("--hashes", action="store_true")
    p_run.add_argument("--apply", action="store_true")
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
