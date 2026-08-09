"""Mechanical output quality and article maturity evaluation."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any


def section_text(body: str, heading: str) -> str:
    match = re.search(rf"(?ms)^##\s+{re.escape(heading)}\s*$\n(.*?)(?=^##\s+|\Z)", body)
    return match.group(1).strip() if match else ""


def has_subheading(body: str, heading: str) -> bool:
    return bool(re.search(rf"(?m)^###\s+{re.escape(heading)}\s*$", body))


def zh_char_count(text: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", text))


def article_maturity(text: str, body: str) -> tuple[str, dict[str, bool]]:
    draft = section_text(body, "正文草稿") or body
    zh_chars = zh_char_count(draft)
    h3_count = len(re.findall(r"(?m)^###\s+", draft))
    editorial_card = section_text(body, "发布编辑卡片")
    memorable_lines = section_text(body, "可复用金句")
    checks = {
        "article_body_1500_zh": zh_chars >= 1500,
        "article_body_2500_zh": zh_chars >= 2500,
        "article_3plus_sections": h3_count >= 3 or len(re.findall(r"(?m)^第[一二三四五六七八九十]+", draft)) >= 3,
        "article_4plus_sections": h3_count >= 4,
        "article_has_hook": bool(re.search(r"开头|钩子|故事|场景|很多人|你有没有|为什么", draft)),
        "article_has_reader_problem": bool(re.search(r"读者问题|问题|困惑|痛点|为什么", text)),
        "article_has_examples": bool(re.search(r"案例|例子|比如|例如|场景|客户|团队", draft)),
        "article_has_counterpoint": bool(re.search(r"但是|反过来|误区|不是.*而是|真正的问题|矛盾", draft)),
        "article_has_actionable_end": bool(re.search(r"最后|所以|建议|下一步|你可以|行动|清单", draft[-800:])),
        "article_has_fact_boundary": "fact_check_required" in text or "核查" in text or "事实边界" in text,
        "article_has_genre": has_subheading(editorial_card, "文章体裁"),
        "article_has_title_candidates": bool(section_text(body, "标题候选")),
        "article_has_publish_angle": (
            "publish_angle:" in text or bool(section_text(body, "发布角度"))
            or has_subheading(editorial_card, "选题切口") or has_subheading(editorial_card, "选题角度")
        ),
        "article_has_key_scenes": (
            bool(section_text(body, "关键场景")) or has_subheading(editorial_card, "关键证据/素材")
            or has_subheading(editorial_card, "关键素材")
        ),
        "article_has_memorable_lines": len(re.findall(r"(?m)^-\s+", memorable_lines)) >= 5,
        "article_has_publish_fact_check": bool(section_text(body, "发布前核查")),
    }
    publishable_keys = [
        "article_body_2500_zh", "article_4plus_sections", "article_has_hook",
        "article_has_reader_problem", "article_has_examples", "article_has_counterpoint",
        "article_has_actionable_end", "article_has_fact_boundary", "article_has_genre",
        "article_has_title_candidates", "article_has_publish_angle", "article_has_key_scenes",
        "article_has_memorable_lines", "article_has_publish_fact_check",
    ]
    if all(checks[key] for key in publishable_keys):
        return "publishable_draft", checks
    if all(checks[key] for key in [
        "article_body_1500_zh", "article_3plus_sections", "article_has_reader_problem",
        "article_has_examples", "article_has_fact_boundary",
    ]):
        return "article_draft", checks
    return "article_seed", checks


def evaluate_output_file(base: Path, path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="ignore")
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
    maturity = None
    relative = str(path.relative_to(base))
    if "文章草稿" in relative or 'output_type: "文章草稿"' in text or "output_type: 文章草稿" in text:
        maturity, article_checks = article_maturity(text, body)
        checks.update(article_checks)
    score = sum(1 for passed in checks.values() if passed)
    status = "usable" if score >= max(6, len(checks) - 1) and checks["no_placeholders"] else "needs_revision"
    required_article = [
        "has_source_theme", "has_audience_or_scenario", "has_core_message", "has_fact_boundary",
        "has_evidence_boundary", "has_scope_or_limits", "not_empty_draft", "no_placeholders",
        "article_body_1500_zh", "article_3plus_sections", "article_has_reader_problem",
        "article_has_examples", "article_has_fact_boundary",
    ]
    if maturity == "article_seed":
        status = "needs_revision"
    elif maturity in {"article_draft", "publishable_draft"} and all(checks.get(key, False) for key in required_article):
        status = "usable"
    return {"file": relative, "score": score, "status": status, "checks": checks, "article_maturity": maturity}


def render_output_quality(results: list[dict[str, Any]]) -> str:
    denominator = max((len(result["checks"]) for result in results), default=0)
    lines = ["# Output Quality Review", "", "---", f"updated_at: {date.today().isoformat()}", "stage: system", "status: active", "---", "", "## Summary", "", "| File | Score | Status |", "|---|---:|---|"]
    lines.extend(f"| `{result['file']}` | {result['score']}/{denominator} | {result['status']} |" for result in results)
    lines.extend(["", "## Checks", ""])
    for result in results:
        lines.append(f"### {result['file']}")
        lines.extend(f"- {key}: {'pass' if passed else 'fail'}" for key, passed in result["checks"].items())
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
