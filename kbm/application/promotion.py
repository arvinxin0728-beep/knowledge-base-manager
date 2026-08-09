"""Topic clustering, promotion scoring, and artifact candidate decisions."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from kbm.domain.naming import safe_stem

_REUSE_KEYWORDS = frozenset({"方法", "方法论", "工作流", "框架", "模板", "practice", "workflow", "framework", "template", "pipeline", "method", "pattern"})
_OUTPUT_KEYWORDS = frozenset({"输出", "写作", "表达", "报告", "解释", "方案", "write", "output", "explain", "report", "draft", "article", "feynman"})


def load_cluster_rules(path: Path | None) -> dict[str, Any]:
    if path and path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    default = Path(__file__).resolve().parents[2] / "references" / "portable-cluster-rules.json"
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
    is_auto = bool(rule.get("auto_discovered"))
    has_question = bool(rule.get("question"))
    if is_auto and not has_question and source_count >= min_sources:
        has_question = True
    asset_type = rule.get("asset_type") or "unclassified"
    has_reuse = asset_type != "unclassified" or bool(rule.get("reusable_asset"))
    if is_auto and not has_reuse:
        all_topics = {t.lower() for m in members for t in m.get("topics", [])}
        if all_topics & _REUSE_KEYWORDS or source_count >= min_sources * 2:
            has_reuse = True
    has_output = bool(rule.get("output_type") or rule.get("output_intent") or rule.get("active_project"))
    if is_auto and not has_output:
        all_topics = {t.lower() for m in members for t in m.get("topics", [])}
        if all_topics & _OUTPUT_KEYWORDS or source_count >= min_sources * 2:
            has_output = True
    risk_controlled = risk != "high" or bool(rule.get("verification_required", False))
    # Quality weighting: reduce score if cluster has thin content
    if is_auto and source_count >= min_sources:
        rich_count = 0
        for m in members:
            of = m.get("output_file", "")
            if of and Path(of).exists():
                try:
                    _t = Path(of).read_text("utf-8", errors="replace")
                    _b = [l for l in _t.split(chr(10)) if l.strip().startswith(("1.", "2.", "3.", "4.")) and len(l.strip()) > 40]
                    if len(_b) >= 3: rich_count += 1
                except: pass
        rich_ratio = rich_count / source_count if source_count > 0 else 0
        if rich_ratio < 0.05:
            has_question = False
            has_reuse = False
            has_output = False
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
    lines = ["# Promotion Review", "", "---", f"updated_at: {date.today().isoformat()}", "stage: system", "status: active", f"processed_index_count: {index_count}", "---", "", "## Score Rules", "", "| Dimension | Point |", "|---|---:|", "| 3+ relevant sources after semantic merging | 1 |", "| Clear non-placeholder question | 1 |", "| Proven reusable method/case/expression/framework | 1 |", "| Output intent or active project | 1 |", "| Fact risk controlled or marked | 1 |", "", "Repeated source count does not prove reusability. Auto-discovered clusters earn question/reuse/output points based on source count and content quality. A quality override strips these points if fewer than 15% of member refinements have 3+ substantive core bullets.", "", "## Promotion Decisions", "", "| Cluster | Sources | Score | Asset type | Action |", "|---|---:|---:|---|---|"]
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
