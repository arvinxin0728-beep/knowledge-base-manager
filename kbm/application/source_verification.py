"""Source quality weighting and high-risk claim verification governance."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any

from kbm.domain.markdown import collect_markdown_files, split_frontmatter
from kbm.platform.clock import now_iso
from kbm.platform.dates import parse_date as _parse_date
from kbm.platform.jsonl import read_jsonl_objects as read_index_objects
from kbm.platform.paths import kb_path, system_file

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

def _infer_source_channel(meta: dict[str, Any], path: Path, text: str) -> str:
    raw_type = str(meta.get("source_type") or "").lower()
    source_file = str(meta.get("source_file") or "")
    url = str(meta.get("url") or "").lower()
    name = f"{path.name} {source_file}".lower()
    if raw_type in {"ebook", "book"} or "电子书" in path.parts or any(x in source_file.lower() for x in [".epub", ".pdf"]):
        return "book"
    if "paper" in raw_type or "arxiv" in url or "doi.org" in url or "论文" in name:
        return "paper"
    if any(x in url for x in [".gov", "gov.cn", "stats.gov", "sec.gov"]) or ("非官方" not in name and any(x in name for x in ["官方", "标准", "白皮书"])):
        return "official_doc"
    if any(x in name for x in ["报告", "研究", "白皮书", "财报"]):
        return "report"
    if raw_type in {"public_account_article", "wechat", "public_account"} or "公众号" in path.parts:
        return "public_account"
    if any(x in name for x in ["教程", "指南", "插件", "安装", "配置", "手把手"]):
        return "tool_doc"
    if raw_type in {"web_article", "article", "web"}:
        return "web_article"
    return "unknown"


def _infer_source_entity_type(meta: dict[str, Any], path: Path, text: str) -> str:
    account = str(meta.get("account") or meta.get("author") or "").lower()
    url = str(meta.get("url") or "").lower()
    title_blob = f"{path.name} {account}".lower()
    if any(x in url for x in [".gov", "gov.cn", "sec.gov"]):
        return "official"
    if any(x in title_blob for x in ["麦肯锡", "mckinsey", "贝恩", "bain", "bcg", "中金", "斯坦福", "微软", "华为", "红杉"]):
        return "institution"
    if any(x in title_blob for x in ["专访", "访谈", "人物"]):
        return "expert"
    if account:
        return "practitioner"
    return "unknown"


def _infer_evidence_mode(channel: str, path: Path, text: str) -> str:
    blob = f"{path.name}\n{text[:4000]}".lower()
    if channel in {"official_doc", "paper"}:
        return "primary_data"
    if channel == "book":
        return "theory"
    if any(x in blob for x in ["数据显示", "研究报告", "财报", "白皮书", "according to", "report"]):
        return "cited_report"
    if any(x in blob for x in ["案例", "复盘", "实战", "我用", "我们做", "亲历"]):
        return "firsthand_case"
    if any(x in blob for x in ["教程", "安装", "配置", "步骤", "手把手", "how to"]):
        return "tutorial"
    if any(x in blob for x in ["杀疯", "炸了", "暴利", "月入", "必看", "保姆级", "颠覆"]):
        return "marketing"
    if any(x in blob for x in ["观点", "认为", "判断", "启发"]):
        return "opinion"
    return "summary"


def _source_time_sensitivity(channel: str, evidence_mode: str, text: str) -> str:
    if has_high_risk(text) or channel in {"tool_doc", "report", "official_doc"} or evidence_mode in {"primary_data", "cited_report", "tutorial", "marketing"}:
        return "high"
    if channel in {"public_account", "web_article"}:
        return "medium"
    return "low"


def _source_freshness_score(meta: dict[str, Any], channel: str, sensitivity: str) -> int:
    saved = _parse_date(meta.get("saved_at")) or _parse_date(meta.get("published_at")) or _parse_date(meta.get("created_at"))
    if not saved:
        return 3 if sensitivity != "high" else 2
    age_days = (date.today() - saved).days
    if sensitivity == "low":
        return 5 if age_days <= 3650 else 4
    if sensitivity == "medium":
        if age_days <= 180:
            return 5
        if age_days <= 730:
            return 4
        return 2
    if age_days <= 90:
        return 5
    if age_days <= 365:
        return 3
    return 1


def classify_source_quality(meta: dict[str, Any], path: Path, text: str) -> dict[str, Any]:
    channel = _infer_source_channel(meta, path, text)
    entity = _infer_source_entity_type(meta, path, text)
    mode = _infer_evidence_mode(channel, path, text)
    sensitivity = _source_time_sensitivity(channel, mode, text)
    authority = 2
    if channel in {"paper", "official_doc", "book"}:
        authority = 5
    elif channel == "report" or entity == "institution":
        authority = 4
    elif entity in {"expert", "practitioner"}:
        authority = 3
    evidence_strength = 2
    if mode in {"primary_data", "theory"}:
        evidence_strength = 5
    elif mode in {"cited_report", "firsthand_case"}:
        evidence_strength = 4
    elif mode == "tutorial":
        evidence_strength = 3
    elif mode == "marketing":
        evidence_strength = 1
    freshness = _source_freshness_score(meta, channel, sensitivity)
    bias_risk = "low"
    if mode == "marketing":
        bias_risk = "high"
    elif channel in {"public_account", "web_article"} or mode in {"opinion", "summary"}:
        bias_risk = "medium"
    score = authority + evidence_strength + freshness
    if bias_risk == "high":
        score -= 3
    elif bias_risk == "medium":
        score -= 1
    if has_high_risk(text) and mode not in {"primary_data", "cited_report"}:
        score -= 1
    if score >= 13:
        tier = "A"
        weight = 1.3
    elif score >= 10:
        tier = "B"
        weight = 1.0
    elif score >= 7:
        tier = "C"
        weight = 0.6
    else:
        tier = "D"
        weight = 0.25
    flags = []
    if bias_risk == "high":
        flags.append("marketing_or_title_bait")
    if sensitivity == "high" and freshness <= 2:
        flags.append("stale_high_sensitivity")
    if has_high_risk(text) and mode not in {"primary_data", "cited_report"}:
        flags.append("high_fact_risk_without_primary_evidence")
    if channel == "public_account" and tier in {"C", "D"}:
        flags.append("use_as_scene_or_lead_not_core_evidence")
    return {
        "source_channel": channel,
        "source_entity_type": entity,
        "source_evidence_mode": mode,
        "source_time_sensitivity": sensitivity,
        "source_quality_tier": tier,
        "source_authority": authority,
        "source_freshness": freshness,
        "source_evidence_strength": evidence_strength,
        "source_bias_risk": bias_risk,
        "promotion_weight": weight,
        "score": score,
        "flags": flags,
    }


def source_quality_audit(cfg: dict[str, Any]) -> dict[str, Any]:
    base = Path(cfg["ai_knowledge_base"])
    root = kb_path(cfg, "source_refinements")
    items = []
    tier_counts: Counter[str] = Counter()
    channel_counts: Counter[str] = Counter()
    flag_counts: Counter[str] = Counter()
    for p in collect_markdown_files(root):
        text = p.read_text("utf-8", errors="replace")
        meta, _body = split_frontmatter(text)
        result = classify_source_quality(meta, p, text)
        rel = str(p.relative_to(base))
        tier_counts[result["source_quality_tier"]] += 1
        channel_counts[result["source_channel"]] += 1
        for flag in result["flags"]:
            flag_counts[flag] += 1
        items.append({"file": rel, **result})
    items.sort(key=lambda x: (x["source_quality_tier"], x["promotion_weight"], x["file"]))
    return {
        "source_count": len(items),
        "tier_counts": dict(tier_counts),
        "channel_counts": dict(channel_counts),
        "flag_counts": dict(flag_counts),
        "items": items,
    }


def render_source_quality_audit(result: dict[str, Any]) -> str:
    lines = [
        "# Source Quality Audit",
        "",
        "---",
        f"updated_at: {date.today().isoformat()}",
        "stage: system",
        "status: active",
        "---",
        "",
        "## Summary",
        "",
        f"- source_count: {result['source_count']}",
        "",
        "## Tier Counts",
        "",
    ]
    for key in ["A", "B", "C", "D"]:
        lines.append(f"- {key}: {result['tier_counts'].get(key, 0)}")
    lines += ["", "## Channel Counts", ""]
    for key, value in sorted(result["channel_counts"].items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- {key}: {value}")
    lines += ["", "## Flags", ""]
    if not result["flag_counts"]:
        lines.append("- None.")
    for key, value in sorted(result["flag_counts"].items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- {key}: {value}")
    lines += ["", "## Low-Tier / High-Risk Sources", ""]
    risky = [item for item in result["items"] if item["source_quality_tier"] in {"C", "D"} or item["flags"]]
    if not risky:
        lines.append("- None.")
    for item in risky[:300]:
        flags = ",".join(item["flags"]) if item["flags"] else "-"
        lines.append(f"- `{item['file']}` tier={item['source_quality_tier']} channel={item['source_channel']} mode={item['source_evidence_mode']} freshness={item['source_freshness']} weight={item['promotion_weight']} flags={flags}")
    return "\n".join(lines).rstrip() + "\n"


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



def _source_for_verification_id(cfg: dict[str, Any], vid: str) -> Path | None:
    """Find the source file for a verification item by scanning refinements."""
    ref_root = kb_path(cfg, "source_refinements")
    for p in collect_markdown_files(ref_root):
        text = p.read_text("utf-8", errors="ignore")
        h = hashlib.sha256(str(p.relative_to(Path(cfg["ai_knowledge_base"]))).encode("utf-8")).hexdigest()[:16]
        if h == vid:
            return p
    return None



def verification_status(cfg: dict[str, Any]) -> dict[str, Any]:
    queue = verification_items(cfg)
    latest = latest_verification_results(cfg)
    # Mark verification results as stale if the source file has been rewritten
    stale_results = set()
    for vid, vrow in latest.items():
        src_file = _source_for_verification_id(cfg, vid)
        if src_file and src_file.exists():
            vtime = vrow.get("verified_at", "")
            mtime = datetime.fromtimestamp(src_file.stat().st_mtime).isoformat()
            if vtime < mtime:
                stale_results.add(vid)
    merged = []
    counts: Counter[str] = Counter()
    for item in queue:
        resolved = latest.get(item["id"])
        if resolved and item["id"] in stale_results:
            resolved["status"] = "stale"
            counts["stale"] += 1
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
