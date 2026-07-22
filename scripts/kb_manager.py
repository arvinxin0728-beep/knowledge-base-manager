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

DEFAULT_MAPPING = {
    "system": "00-system",
    "source_refinements": "10-source-refinements",
    "topic_pages": "20-topic-pages",
    "reusable_assets": "30-reusable-assets",
    "outputs": "40-outputs",
}

DEFAULT_SOURCE_SUBDIRS = {
    "ebooks": "ebooks",
    "articles": "articles",
    "public_accounts": "public-accounts",
}

DEFAULT_TOPIC_PAGE_SUBDIRS = {
    "pages": "pages",
    "moc": "moc",
}

DEFAULT_OUTPUT_SUBDIRS = {
    "feynman": "feynman-explanations",
    "article_drafts": "article-drafts",
    "solution_materials": "solution-materials",
    "reviews": "reviews",
}

DEFAULT_REUSABLE_ASSET_SUBDIRS = {
    "methods": "methods",
    "cases": "cases",
    "expressions": "expressions",
    "frameworks": "frameworks",
}

SOURCE_EXTS = {".md", ".markdown", ".txt", ".html", ".htm", ".pdf", ".epub", ".docx"}
SKILL_ROOT = Path(__file__).resolve().parents[1]
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


def deep_defaults(value: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    """Fill missing nested defaults without overwriting user configuration."""
    out = dict(value)
    for key, default in defaults.items():
        if key not in out:
            out[key] = default
        elif isinstance(out[key], dict) and isinstance(default, dict):
            out[key] = deep_defaults(out[key], default)
    return out


def config_defaults() -> dict[str, Any]:
    return {
        "version": 1,
        "language": "zh-CN",
        "source_libraries": {},
        "mapping": dict(DEFAULT_MAPPING),
        "source_refinement_subdirs": dict(DEFAULT_SOURCE_SUBDIRS),
        "topic_page_subdirs": dict(DEFAULT_TOPIC_PAGE_SUBDIRS),
        "reusable_asset_subdirs": dict(DEFAULT_REUSABLE_ASSET_SUBDIRS),
        "output_subdirs": dict(DEFAULT_OUTPUT_SUBDIRS),
        "promotion_rules": {
            "min_sources_for_topic": 3,
            "allow_user_requested_topic": True,
            "fact_check_before_public_output": True,
        },
        "integrations": {"obsidian": {"enabled": False}},
        "pipeline": {"chunk_size": 5000, "default_batch_size": 10, "max_attempts": 3, "lease_minutes": 120, "runtime_storage": "legacy", "artifact_retention_days": 7},
    }
HIGH_RISK_PATTERNS = {
    "market_data": r"市场规模|增长率|同比|环比|渗透率|GMV|收入|利润|财报|业绩",
    "ranking": r"排行榜|排名|十大|TOP\s*\d",
    "finance": r"融资|估值|债务|收益率|股票|金融",
    "company_or_personnel_event": r"开除|裁员|违法|诉讼|处罚",
    "medical_or_legal": r"医疗|法律",
    "report_claim": r"研究报告|数据显示|官方称|\d{4}.*报告|报告：",
    "quantified_improvement": r"提升\s*\d|提升\s*[0-9]+%|下降\s*\d|下降\s*[0-9]+%",
    "forecast": r"预测|预计|未来\d+年",
}


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        cfg = json.load(f)
    return deep_defaults(cfg, config_defaults())


def validate_config(cfg: dict[str, Any]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if cfg.get("version") != 1:
        errors.append({"field": "version", "error": "unsupported_version"})
    base_raw = cfg.get("ai_knowledge_base")
    if not isinstance(base_raw, str) or not base_raw.strip():
        errors.append({"field": "ai_knowledge_base", "error": "required_absolute_path"})
    elif not Path(base_raw).expanduser().is_absolute():
        errors.append({"field": "ai_knowledge_base", "error": "must_be_absolute"})
    for key in DEFAULT_MAPPING:
        value = cfg.get("mapping", {}).get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append({"field": f"mapping.{key}", "error": "required_relative_path"})
        elif Path(value).is_absolute() or ".." in Path(value).parts:
            errors.append({"field": f"mapping.{key}", "error": "must_stay_inside_ai_knowledge_base"})
    for key, value in cfg.get("source_libraries", {}).items():
        if value and not Path(value).expanduser().is_absolute():
            errors.append({"field": f"source_libraries.{key}", "error": "must_be_absolute"})
    pipeline = cfg.get("pipeline", {})
    if pipeline.get("runtime_storage") not in {"local", "legacy"}:
        errors.append({"field": "pipeline.runtime_storage", "error": "must_be_local_or_legacy"})
    retention = pipeline.get("artifact_retention_days")
    if not isinstance(retention, int) or retention < 0:
        errors.append({"field": "pipeline.artifact_retention_days", "error": "must_be_non_negative_integer"})
    return errors


def require_valid_config(cfg: dict[str, Any]) -> None:
    errors = validate_config(cfg)
    if errors:
        raise SystemExit(json.dumps({"valid": False, "errors": errors}, ensure_ascii=False, indent=2))


def write_config(path: Path, cfg: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def kb_path(cfg: dict[str, Any], key: str) -> Path:
    return Path(cfg["ai_knowledge_base"]) / cfg["mapping"][key]


def topic_pages_content_dir(cfg: dict[str, Any]) -> Path:
    subdir = cfg.get("topic_page_subdirs", {}).get("pages")
    root = kb_path(cfg, "topic_pages")
    return root / subdir if subdir else root


def topic_pages_moc_dir(cfg: dict[str, Any]) -> Path:
    subdir = cfg.get("topic_page_subdirs", {}).get("moc")
    root = kb_path(cfg, "topic_pages")
    return root / subdir if subdir else root


def system_file(cfg: dict[str, Any], name: str) -> Path:
    return kb_path(cfg, "system") / name


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def ensure_system_files(cfg: dict[str, Any]) -> None:
    system = kb_path(cfg, "system")
    system.mkdir(parents=True, exist_ok=True)
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
        p = system / name
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


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_stem(value: str) -> str:
    value = re.sub(r"[\\/:*?\"<>|\n\r\t]+", "", value).strip()
    value = re.sub(r"\s+", "", value)
    return value[:80] or "untitled"


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


def read_index_objects(index: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    if not index.exists():
        return rows, errors
    for lineno, line in enumerate(index.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            errors.append({"line": lineno, "error": str(exc)})
    return rows, errors


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


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
    processed_paths, processed_hashes, processed_count = read_processed(cfg)
    sources = iter_sources(cfg)
    unprocessed = []
    for p in sources:
        processed = str(p) in processed_paths
        sha = None
        if include_hashes:
            sha = file_sha256(p)
            processed = processed or sha in processed_hashes
        if not processed:
            unprocessed.append({"path": str(p), "sha256": sha})
    return {
        "ai_knowledge_base": cfg.get("ai_knowledge_base"),
        "source_count": len(sources),
        "processed_index_count": processed_count,
        "unprocessed_count": len(unprocessed),
        "unprocessed": unprocessed,
    }


def load_cluster_rules(path: Path | None) -> dict[str, Any]:
    if path and path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    default = Path(__file__).resolve().parents[1] / "references" / "portable-cluster-rules.json"
    if default.exists():
        return json.loads(default.read_text(encoding="utf-8"))
    return {"clusters": []}


def source_matches_cluster(row: dict[str, Any], cluster: dict[str, Any]) -> bool:
    tags = [str(t).lower() for t in cluster.get("tags", [])]
    keywords = [str(t).lower() for t in cluster.get("keywords", [])]
    blob = " ".join([row.get("title", ""), row.get("source_type", ""), " ".join(row.get("topics", []))]).lower()
    return any(tag.lower() in [t.lower() for t in row.get("topics", [])] for tag in cluster.get("tags", [])) or any(k and k in blob for k in keywords + tags)


def cluster_rows(rows: list[dict[str, Any]], rules: dict[str, Any]) -> list[dict[str, Any]]:
    clusters = []
    used_ids: set[str] = set()
    for raw_cluster in rules.get("clusters", []):
        members = [row for row in rows if source_matches_cluster(row, raw_cluster)]
        for row in members:
            used_ids.add(row["source_id"])
        if members or raw_cluster.get("user_requested") or raw_cluster.get("active_project"):
            clusters.append(build_cluster(raw_cluster, members, rules))
    by_topic: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["source_id"] in used_ids:
            continue
        for topic in row.get("topics", []):
            by_topic[topic].append(row)
    min_sources = int(rules.get("default_min_sources", 3))
    for topic, members in sorted(by_topic.items(), key=lambda item: (-len(item[1]), item[0])):
        if len(members) >= min_sources:
            clusters.append(build_cluster({"id": safe_stem(topic), "name": topic, "tags": [topic], "risk": "medium", "auto_discovered": True}, members, rules))
    return sorted(clusters, key=lambda c: (-c["score"], -c["source_count"], c["name"]))


def build_cluster(rule: dict[str, Any], members: list[dict[str, Any]], rules: dict[str, Any]) -> dict[str, Any]:
    min_sources = int(rule.get("min_sources") or rules.get("default_min_sources") or 3)
    source_count = len(members)
    risk = rule.get("risk", "medium")
    has_question = bool(rule.get("question")) and not bool(rule.get("auto_discovered"))
    asset_type = rule.get("asset_type") or "unclassified"
    has_reuse = asset_type != "unclassified" or bool(rule.get("reusable_asset"))
    has_output = bool(rule.get("output_type") or rule.get("output_intent") or rule.get("active_project"))
    risk_controlled = risk != "high" or bool(rule.get("verification_required", True))
    score = 0
    score += 1 if source_count >= min_sources else 0
    score += 1 if has_question else 0
    score += 1 if has_reuse else 0
    score += 1 if has_output else 0
    score += 1 if risk_controlled else 0
    evidence_gate = source_count >= min_sources or bool(rule.get("user_requested") or rule.get("active_project"))
    if not evidence_gate:
        action = "candidate_only"
    elif score <= 1:
        action = "candidate_only"
    elif score <= 3:
        action = "topic_page"
    elif score == 4:
        action = "topic_page_and_asset"
    else:
        action = "topic_page_asset_output"
    if risk == "high" and action == "topic_page_asset_output":
        action = "topic_page_and_asset_verify_before_output"
    return {
        "id": rule.get("id") or safe_stem(rule.get("name", "cluster")),
        "name": rule.get("name") or rule.get("id") or "Untitled Cluster",
        "question": rule.get("question") or "",
        "auto_discovered": bool(rule.get("auto_discovered")),
        "tags": rule.get("tags", []),
        "risk": risk,
        "score": score,
        "action": action,
        "source_count": source_count,
        "sources": [{"source_id": m["source_id"], "title": m.get("title"), "source_path": m.get("source_path"), "output_file": m.get("output_file")} for m in members],
        "asset_type": asset_type,
        "output_type": rule.get("output_type", "unclassified"),
        "fact_check_required": bool(rule.get("fact_check_required", risk in {"medium", "high"})),
        "non_promotion_reason": non_promotion_reason(score, source_count, min_sources, has_question, has_output, risk, evidence_gate),
    }


def non_promotion_reason(score: int, source_count: int, min_sources: int, has_question: bool, has_output: bool, risk: str, evidence_gate: bool) -> str:
    reasons = []
    if source_count < min_sources:
        reasons.append("insufficient_sources")
    if not has_question:
        reasons.append("unclear_question")
    if not has_output:
        reasons.append("no_output_intent")
    if risk == "high":
        reasons.append("high_fact_risk")
    return ",".join(reasons) if not evidence_gate or score <= 1 else ""


def render_topic_clusters(clusters: list[dict[str, Any]]) -> str:
    lines = ["# Topic Clusters", "", "---", f"updated_at: {date.today().isoformat()}", "stage: system", "status: active", "---", "", "Topic clusters merge raw tags into answerable questions. They are promotion units, not folders or single keywords.", ""]
    for c in clusters:
        lines += [f"## {c['name']}", "", f"- id: `{c['id']}`", f"- question: {c.get('question') or 'TBD'}", f"- auto_discovered: {str(c.get('auto_discovered', False)).lower()}", f"- source_count: {c['source_count']}", f"- promotion_score: {c['score']}/5", f"- action: `{c['action']}`", f"- asset_type: `{c.get('asset_type', 'unclassified')}`", f"- fact_check_required: {str(c.get('fact_check_required')).lower()}", f"- risk: {c.get('risk')}", "", "### Sources"]
        for source in c.get("sources", [])[:30]:
            lines.append(f"- {source.get('title')}")
        if not c.get("sources"):
            lines.append("- No matched sources yet.")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_promotion_review(clusters: list[dict[str, Any]], index_count: int) -> str:
    lines = ["# Promotion Review", "", "---", f"updated_at: {date.today().isoformat()}", "stage: system", "status: active", f"processed_index_count: {index_count}", "---", "", "## Score Rules", "", "| Dimension | Point |", "|---|---:|", "| 3+ relevant sources after semantic merging | 1 |", "| Clear non-placeholder question | 1 |", "| Proven reusable method/case/expression/framework | 1 |", "| Output intent or active project | 1 |", "| Fact risk controlled or marked | 1 |", "", "Repeated source count does not prove reusability. Auto-discovered placeholder topics do not earn the question-clarity point.", "", "## Promotion Decisions", "", "| Cluster | Sources | Score | Asset type | Action |", "|---|---:|---:|---|---|"]
    for c in clusters:
        lines.append(f"| {c['name']} | {c['source_count']} | {c['score']} | {c.get('asset_type', 'unclassified')} | {c['action']} |")
    lines += ["", "## Not Promoted / Cautions", ""]
    cautions = [c for c in clusters if c.get("non_promotion_reason") or c.get("fact_check_required")]
    if not cautions:
        lines.append("- None.")
    for c in cautions:
        reason = c.get("non_promotion_reason") or "fact_check_required"
        lines.append(f"- `{c['name']}`: {reason}")
    return "\n".join(lines).rstrip() + "\n"


def artifact_candidates(c: dict[str, Any]) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    action = c.get("action", "")
    if action in {"topic_page", "topic_page_and_asset", "topic_page_asset_output", "topic_page_and_asset_verify_before_output"}:
        candidates.append({
            "artifact_type": "topic_page",
            "location": "20-topic-pages",
            "cost_tier": "high",
            "approval_required": "yes",
        })
    asset_type = c.get("asset_type", "unclassified")
    if action in {"topic_page_and_asset", "topic_page_asset_output", "topic_page_and_asset_verify_before_output"} and asset_type != "unclassified":
        candidates.append({
            "artifact_type": asset_type,
            "location": "30-reusable-assets",
            "cost_tier": "high",
            "approval_required": "yes",
        })
    if action == "topic_page_asset_output":
        candidates.append({
            "artifact_type": c.get("output_type", "feynman"),
            "location": "40-outputs",
            "cost_tier": "high",
            "approval_required": "yes",
        })
    return candidates


def render_asset_output_candidates(clusters: list[dict[str, Any]]) -> str:
    lines = [
        "# Asset and Output Candidates",
        "",
        "---",
        f"updated_at: {date.today().isoformat()}",
        "stage: system",
        "status: waiting_for_approval",
        "---",
        "",
        "This file is the approval surface for high-cost topic, asset, and output generation. It lists what can be generated, why, and what should remain deferred.",
        "",
    ]
    any_candidate = False
    for c in clusters:
        candidates = artifact_candidates(c)
        if not candidates:
            continue
        any_candidate = True
        lines += [
            f"## {c['name']}",
            "",
            f"- cluster_id: `{c['id']}`",
            f"- question: {c.get('question') or 'TBD'}",
            f"- source_count: {c['source_count']}",
            f"- promotion_score: {c['score']}/5",
            f"- evidence_strength: {'strong' if c['score'] >= 4 else 'medium'}",
            f"- fact_risk: {c.get('risk')}",
            f"- fact_check_required: {str(c.get('fact_check_required')).lower()}",
            f"- reason_to_generate_now: {c.get('action')}",
            f"- defer_if_not_approved: keep as candidate and update the topic page or promotion review only",
            "",
            "### Proposed Artifacts",
            "",
            "| Artifact type | Expected location | Cost tier | Approval required |",
            "|---|---|---|---|",
        ]
        for item in candidates:
            lines.append(f"| {item['artifact_type']} | {item['location']} | {item['cost_tier']} | {item['approval_required']} |")
        lines += ["", "### Representative Sources"]
        for source in c.get("sources", [])[:10]:
            lines.append(f"- {source.get('title')}")
        if not c.get("sources"):
            lines.append("- No matched sources yet.")
        lines.append("")
    if not any_candidate:
        lines.append("- No high-cost asset or output candidates passed the current promotion gates.")
    return "\n".join(lines).rstrip() + "\n"


def promotion_decision_rows(clusters: list[dict[str, Any]], *, decision_context: str) -> list[dict[str, Any]]:
    ts = now_iso()
    rows = []
    for c in clusters:
        rows.append({
            "schema_version": 1,
            "decided_at": ts,
            "decision_context": decision_context,
            "cluster_id": c.get("id"),
            "cluster_name": c.get("name"),
            "question": c.get("question") or "",
            "source_count": c.get("source_count"),
            "promotion_score": c.get("score"),
            "action": c.get("action"),
            "asset_type": c.get("asset_type", "unclassified"),
            "output_type": c.get("output_type", "unclassified"),
            "fact_check_required": c.get("fact_check_required"),
            "risk": c.get("risk"),
            "non_promotion_reason": c.get("non_promotion_reason") or "",
            "approval_required": bool(artifact_candidates(c)),
            "approved": False,
            "evidence_source_ids": [s.get("source_id") for s in c.get("sources", []) if s.get("source_id")],
        })
    return rows


def append_promotion_decisions(cfg: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    path = system_file(cfg, "promotion-decision.jsonl")
    path.parent.mkdir(parents=True, exist_ok=True)
    existing_keys = set()
    existing, _errors = read_index_objects(path)
    for row in existing:
        existing_keys.add((row.get("decided_at", "")[:10], row.get("decision_context"), row.get("cluster_id"), row.get("action")))
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            key = (row.get("decided_at", "")[:10], row.get("decision_context"), row.get("cluster_id"), row.get("action"))
            if key in existing_keys:
                continue
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            existing_keys.add(key)


def write_run_checkpoint(cfg: dict[str, Any], *, objective: str, stage: str, cost_tier: str, status: str, clusters: list[dict[str, Any]], written: list[str]) -> None:
    ts = now_iso()
    candidate_items = [
        {
            "cluster_id": c.get("id"),
            "name": c.get("name"),
            "score": c.get("score"),
            "action": c.get("action"),
            "source_count": c.get("source_count"),
            "fact_check_required": c.get("fact_check_required"),
        }
        for c in clusters
        if artifact_candidates(c)
    ]
    run_id = f"{date.today().isoformat()}-{safe_stem(objective)[:40]}"
    state = {
        "schema_version": 1,
        "run_id": run_id,
        "objective": objective,
        "status": status,
        "current_stage": stage,
        "cost_tier": cost_tier,
        "started_at": ts,
        "updated_at": ts,
        "approved_scope": {"source_types": [], "limit": None, "artifact_types": []},
        "completed_steps": ["topic_clusters_refreshed", "promotion_review_refreshed", "asset_output_candidates_refreshed"],
        "pending_steps": ["human_approval_for_high_cost_generation"],
        "source_cursor": {"processed_count_before": None, "processed_count_after": None, "last_source": ""},
        "candidates": candidate_items,
        "approved_candidates": [],
        "generated_files": written,
        "last_successful_command": objective,
        "next_recommended_action": "Review asset-output-candidates.md and approve a cluster or artifact type before generating 20/30/40 content.",
        "stop_reason": "waiting_for_human_approval",
    }
    system_file(cfg, "active-run-state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log_event = {
        "run_id": run_id,
        "timestamp": ts,
        "event": status,
        "stage": stage,
        "summary": state["next_recommended_action"],
        "affected_files": written,
    }
    with system_file(cfg, "run-log.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(log_event, ensure_ascii=False) + "\n")


def subdir_for_asset(cfg: dict[str, Any], asset_type: str) -> str:
    asset_map = cfg.get("reusable_asset_subdirs", {})
    return asset_map.get(asset_type, asset_map.get("methods", "methods"))


def subdir_for_output(cfg: dict[str, Any], output_type: str) -> str:
    output_map = cfg.get("output_subdirs", {})
    return output_map.get(output_type, output_map.get("feynman", "feynman-explanations"))


def write_stub_artifacts(cfg: dict[str, Any], clusters: list[dict[str, Any]]) -> list[str]:
    written = []
    stub_root = kb_path(cfg, "system") / "stubs"
    for c in clusters:
        name = safe_stem(c["name"])
        if c["score"] >= 2:
            p = stub_root / "20-topic-pages" / f"{name}.md"
            if not p.exists():
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(render_topic_stub(c), encoding="utf-8")
                written.append(str(p))
        if c["score"] >= 4:
            p = stub_root / "30-reusable-assets" / subdir_for_asset(cfg, c.get("asset_type", "methods")) / f"{name}-asset.md"
            if not p.exists():
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(render_asset_stub(c), encoding="utf-8")
                written.append(str(p))
        if c["score"] >= 5 and c.get("action") == "topic_page_asset_output":
            p = stub_root / "40-outputs" / subdir_for_output(cfg, c.get("output_type", "feynman")) / f"{name}-output.md"
            if not p.exists():
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(render_output_stub(c), encoding="utf-8")
                written.append(str(p))
    return written


def render_topic_stub(c: dict[str, Any]) -> str:
    sources = "\n".join(f"- {s.get('title')}" for s in c.get("sources", [])[:20]) or "- TBD"
    return f"""# {c['name']}

---
stage: topic-page
version: v0.1
created_at: {date.today().isoformat()}
status: draft
confidence: low
source_count: {c['source_count']}
promotion_score: {c['score']}
fact_check_required: {str(c.get('fact_check_required')).lower()}
---

## Topic Question

{c.get('question') or 'TBD'}

## Current Judgment

TBD. This deterministic stub marks the cluster as promoted; Codex should synthesize the current judgment from source refinements before formal use.

## Supporting Sources

{sources}

## Core Model

TBD.

## What Is Reliable

TBD.

## What Is Uncertain

- Fact risk: {c.get('risk')}

## Output-Ready Material

TBD.

## Assets To Extract

TBD.

## Next Actions

- Review source refinements.
- Replace this stub with a synthesized topic page.
"""


def render_asset_stub(c: dict[str, Any]) -> str:
    return f"""# {c['name']} Asset

---
stage: reusable-asset
asset_type: {c.get('asset_type', 'methods')}
created_at: {date.today().isoformat()}
status: draft
source_theme: {c['name']}
fact_check_required: {str(c.get('fact_check_required')).lower()}
---

## Reusable Unit

TBD. Extract the method, case, expression, checklist, or framework from the related topic page.

## When To Use

TBD.

## Source Boundary

Generated as a deterministic promotion stub. Confirm against source refinements before reuse.
"""


def render_output_stub(c: dict[str, Any]) -> str:
    return f"""# {c['name']} Output

---
stage: output
output_type: {c.get('output_type', 'feynman')}
created_at: {date.today().isoformat()}
status: draft
source_theme: {c['name']}
fact_check_required: {str(c.get('fact_check_required')).lower()}
---

## Audience / Scenario

TBD.

## Core Message

TBD.

## Draft

TBD. Generate this from the topic page, not directly from raw sources.

## Verification Notes

- Fact risk: {c.get('risk')}
"""


def collect_markdown_files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted([p for p in path.rglob("*.md") if p.is_file()], key=lambda p: str(p))


def risk_signals(text: str) -> list[str]:
    signals = [name for name, pattern in HIGH_RISK_PATTERNS.items() if re.search(pattern, text, flags=re.I)]
    if "fact_check_required: true" in text.lower():
        signals.append("fact_check_required")
    return sorted(set(signals))


def has_high_risk(text: str) -> bool:
    return bool(risk_signals(text))


def verification_items(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    roots = [kb_path(cfg, "source_refinements"), kb_path(cfg, "topic_pages"), kb_path(cfg, "outputs")]
    items = []
    seen = set()
    for root in roots:
        for p in collect_markdown_files(root):
            text = p.read_text(encoding="utf-8", errors="ignore")
            if not has_high_risk(text):
                continue
            rel = str(p.relative_to(Path(cfg["ai_knowledge_base"])))
            if rel in seen:
                continue
            seen.add(rel)
            reasons = risk_signals(text)
            items.append({
                "id": hashlib.sha256(rel.encode("utf-8")).hexdigest()[:16],
                "file": rel,
                "risk_signals": sorted(set(reasons))[:12],
                "status": "pending",
                "claim": "",
                "verify_with": "primary source or reliable current source before public/business-critical use",
            })
    return items


VALID_VERIFICATION_STATUSES = {"pending", "verified", "rejected", "insufficient_evidence", "not_applicable"}


def verification_result_row(args: argparse.Namespace) -> dict[str, Any]:
    status = args.status
    if status not in VALID_VERIFICATION_STATUSES:
        raise SystemExit(f"--status must be one of: {', '.join(sorted(VALID_VERIFICATION_STATUSES))}")
    return {
        "schema_version": 1,
        "id": args.id,
        "status": status,
        "claim": args.claim or "",
        "evidence_url_or_path": args.evidence or "",
        "verified_at": now_iso(),
        "verifier": args.verifier or "codex",
        "note": args.note or "",
    }


def append_verification_result(cfg: dict[str, Any], row: dict[str, Any]) -> None:
    path = system_file(cfg, "verification-results.jsonl")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def latest_verification_results(cfg: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows, _errors = read_index_objects(system_file(cfg, "verification-results.jsonl"))
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row.get("id"):
            latest[str(row["id"])] = row
    return latest


def verification_status(cfg: dict[str, Any]) -> dict[str, Any]:
    queue = verification_items(cfg)
    latest = latest_verification_results(cfg)
    merged = []
    counts: Counter[str] = Counter()
    for item in queue:
        resolved = latest.get(item["id"])
        if resolved:
            merged_item = {**item, "status": resolved.get("status", "pending"), "verification": resolved}
        else:
            merged_item = item
        counts[str(merged_item.get("status", "pending"))] += 1
        merged.append(merged_item)
    return {
        "items": merged,
        "counts": dict(counts),
        "pending_count": sum(1 for item in merged if item.get("status") == "pending"),
        "unresolved_output_count": sum(1 for item in merged if item.get("status") == "pending" and str(item.get("file", "")).startswith(cfg["mapping"]["outputs"] + "/")),
        "result_rows": len(latest),
    }


def render_verification_status(result: dict[str, Any]) -> str:
    lines = [
        "# Verification Status",
        "",
        "---",
        f"updated_at: {date.today().isoformat()}",
        "stage: system",
        "status: active",
        "---",
        "",
        "## Summary",
        "",
        f"- pending_count: {result['pending_count']}",
        f"- unresolved_output_count: {result['unresolved_output_count']}",
        f"- result_rows: {result['result_rows']}",
    ]
    for key, value in sorted(result["counts"].items()):
        lines.append(f"- {key}: {value}")
    lines += ["", "## Items", ""]
    if not result["items"]:
        lines.append("- None.")
    for item in result["items"][:300]:
        lines.append(f"- `{item['id']}` `{item['status']}` `{item['file']}` signals={','.join(item.get('risk_signals', []))}")
    return "\n".join(lines).rstrip() + "\n"


def evaluate_output_file(base: Path, p: Path) -> dict[str, Any]:
    text = p.read_text(encoding="utf-8", errors="ignore")
    body = re.sub(r"---.*?---", "", text, flags=re.S).strip()
    checks = {
        "has_source_theme": "source_theme:" in text,
        "has_audience_or_scenario": bool(re.search(r"## (Audience|读者|场景|目标|Audience / Scenario)", text, re.I)),
        "has_core_message": bool(re.search(r"## (Core Message|核心观点|核心信息|主题问题)", text, re.I)),
        "has_fact_boundary": "fact_check_required" in text or "核查" in text or "Verification" in text,
        "has_evidence_boundary": bool(re.search(r"来源|证据|Supporting|Evidence|based on|基于", body, re.I)),
        "has_scope_or_limits": bool(re.search(r"边界|限制|不适用|uncertain|limits|scope|verification", body, re.I)),
        "not_empty_draft": len(body) > 250,
        "no_placeholders": not bool(re.search(r"\bTBD\b|待补充|TODO", text, re.I)),
    }
    score = sum(1 for ok in checks.values() if ok)
    status = "usable" if score >= max(6, len(checks) - 1) and checks["no_placeholders"] else "needs_revision"
    return {"file": str(p.relative_to(base)), "score": score, "status": status, "checks": checks}


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


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    raw = text[4:end].strip()
    body = text[end + len("\n---"):].lstrip("\n")
    meta: dict[str, Any] = {}
    current = None
    for line in raw.splitlines():
        if not line.strip():
            continue
        if re.match(r"^[A-Za-z0-9_\-]+:\s*", line):
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            current = key
            if value == "":
                meta[key] = []
            elif value.lower() in {"true", "false"}:
                meta[key] = value.lower() == "true"
            else:
                meta[key] = value.strip('"')
        elif line.lstrip().startswith("- ") and current:
            if not isinstance(meta.get(current), list):
                meta[current] = []
            meta[current].append(line.strip()[2:].strip('"'))
    return meta, body


def markdown_title(path: Path, text: str) -> str:
    _meta, body = split_frontmatter(text)
    match = re.search(r"(?m)^#\s+(.+)$", body)
    return match.group(1).strip() if match else path.stem


def clean_link_target(value: str) -> str:
    target = str(value).split("|", 1)[0].split("#", 1)[0].strip()
    return target


def wikilink_targets(text: str) -> list[str]:
    return [clean_link_target(x) for x in re.findall(r"\[\[([^\]]+)\]\]", text)]


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


def quality_gate(cfg: dict[str, Any]) -> dict[str, Any]:
    relation = relation_audit(cfg)
    portability = portability_audit(cfg)
    topic_pages = topic_page_audit(cfg)
    assets = asset_audit(cfg)
    outputs = [evaluate_output_file(Path(cfg["ai_knowledge_base"]), p) for p in collect_markdown_files(kb_path(cfg, "outputs"))]
    verification = verification_status(cfg)
    output_review = output_review_status(cfg)
    blockers = []
    warnings = []
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
    return {
        "passed": not blockers,
        "blockers": blockers,
        "warnings": warnings,
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
    issues = []
    files = sorted([p for p in SKILL_ROOT.rglob("*") if p.is_file()], key=lambda p: str(p))
    required_release_files = ["LICENSE", "CHANGELOG.md", "SECURITY.md", "INSTALL.zh-CN.md"]
    for rel in required_release_files:
        if not (SKILL_ROOT / rel).exists():
            issues.append({"file": rel, "issue": "missing_release_file"})
    readme = SKILL_ROOT / "README.md"
    if not readme.exists():
        issues.append({"file": "README.md", "issue": "missing_chinese_readme"})
    else:
        readme_text = readme.read_text(encoding="utf-8", errors="ignore")
        required_readme_terms = [
            "面向产出的研究型知识管理系统",
            "核心模型",
            "安装方式",
            "第一次使用",
            "质量边界",
            "README 维护规则",
            "原文库",
            "source_libraries",
            "跨平台使用",
            "脚本模式",
            "v0.1.0-beta",
            "package-lint --strict",
        ]
        for term in required_readme_terms:
            if term not in readme_text:
                issues.append({"file": "README.md", "issue": "readme_missing_required_section", "term": term})
        tracked_for_readme = [
            p for p in files
            if p.name != "README.md"
            and p.suffix.lower() in {".md", ".json", ".yaml", ".yml", ".py", ".rb"}
            and not str(p.relative_to(SKILL_ROOT)).startswith("tests/")
            and "__pycache__" not in p.parts
        ]
        if tracked_for_readme:
            newest = max(tracked_for_readme, key=lambda p: p.stat().st_mtime)
            if readme.stat().st_mtime + 1 < newest.stat().st_mtime:
                issues.append({
                    "file": "README.md",
                    "issue": "readme_older_than_skill_sources",
                    "newest_source": str(newest.relative_to(SKILL_ROOT)),
                })
    for p in files:
        rel = str(p.relative_to(SKILL_ROOT))
        if ".bak" in p.name or p.suffix in {".tmp", ".orig"}:
            issues.append({"file": rel, "issue": "temporary_or_backup_file"})
        if rel.startswith("references/8xx"):
            issues.append({"file": rel, "issue": "user_profile_must_not_live_in_default_references"})
        if "__pycache__" in p.parts:
            issues.append({"file": rel, "issue": "python_cache_file"})
        if p.suffix.lower() in {".md", ".json", ".yaml", ".yml", ".py", ".rb"}:
            text = p.read_text(encoding="utf-8", errors="ignore")
            if rel.startswith("tests/fixtures/") and "/Users/" in text:
                issues.append({"file": rel, "issue": "fixture_contains_absolute_user_path"})
            if rel == "SKILL.md" and "Current 8XX implementation" in text:
                issues.append({"file": rel, "issue": "main_skill_contains_user_specific_mapping"})
    return {"passed": not issues, "files_scanned": len(files), "issue_count": len(issues), "issues": issues}


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
            "source_libraries": {"ebooks": args.ebooks, "articles": args.articles, "public_accounts": args.public_accounts},
            "ai_knowledge_base": args.ai_knowledge_base,
            "mapping": {"system": args.system_dir, "source_refinements": args.source_refinements_dir, "topic_pages": args.topic_pages_dir, "reusable_assets": args.reusable_assets_dir, "outputs": args.outputs_dir},
            "source_refinement_subdirs": {"ebooks": args.ebooks_subdir, "articles": args.articles_subdir, "public_accounts": args.public_accounts_subdir},
            "topic_page_subdirs": {"pages": args.topic_pages_subdir, "moc": args.moc_subdir},
            "reusable_asset_subdirs": {"methods": args.methods_subdir, "cases": args.cases_subdir, "expressions": args.expressions_subdir, "frameworks": args.frameworks_subdir},
            "output_subdirs": {"feynman": args.feynman_subdir, "article_drafts": args.article_drafts_subdir, "solution_materials": args.solution_materials_subdir, "reviews": args.reviews_subdir},
            "promotion_rules": {"min_sources_for_topic": 3, "allow_user_requested_topic": True, "fact_check_before_public_output": True},
            "pipeline": {"chunk_size": 5000, "default_batch_size": 10, "max_attempts": 3, "lease_minutes": 120, "runtime_storage": "local", "artifact_retention_days": 7},
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
        backup = index.with_suffix(index.suffix + f".bak-{date.today().isoformat()}")
        if index.exists() and not backup.exists():
            shutil.copy2(index, backup)
        write_jsonl(index, normalized)
        result["written"] = str(index)
        result["backup"] = str(backup)
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


def cmd_quality_gate(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    require_valid_config(cfg)
    result = quality_gate(cfg)
    if args.apply:
        system_file(cfg, "quality-gate.md").write_text(render_quality_gate(result), encoding="utf-8")
    print(json.dumps({"written": str(system_file(cfg, "quality-gate.md")) if args.apply else None, **result}, ensure_ascii=False, indent=2))
    if args.strict and not result["passed"]:
        raise SystemExit(2)


def cmd_package_lint(args: argparse.Namespace) -> None:
    result = package_lint()
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
    written: list[str] = []
    if args.apply:
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

    p_quality_gate = sub.add_parser("quality-gate")
    p_quality_gate.add_argument("--config", required=True, type=Path)
    p_quality_gate.add_argument("--apply", action="store_true")
    p_quality_gate.add_argument("--strict", action="store_true")
    p_quality_gate.set_defaults(func=cmd_quality_gate)

    p_package_lint = sub.add_parser("package-lint")
    p_package_lint.add_argument("--strict", action="store_true")
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
