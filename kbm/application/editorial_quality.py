"""Editorial quality scoring and repair guidance."""

from __future__ import annotations

import re
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from kbm.application.output_quality import (
    evaluate_output_file, has_subheading as _has_subheading,
    section_text as _section_text, zh_char_count as _zh_char_count,
)
from kbm.domain.markdown import collect_markdown_files
from kbm.platform.paths import kb_path

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


