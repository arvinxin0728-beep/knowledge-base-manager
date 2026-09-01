"""Gate-10 source-refinement validation and batch quality reporting."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

from kbm.domain.markdown import collect_markdown_files, extract_sections, split_frontmatter
from kbm.platform.paths import kb_path

KNOWN_TEMPLATE_PATTERNS = [
    r"任务定义\s*->\s*工具/Skill 封装\s*->\s*权限与数据接入\s*->\s*自动执行\s*->\s*复盘迭代",
    r"材料倾向于把 AI 能力包装为可执行流程或可复用 Skill",
    r"解决如何把一个具体任务拆成 Agent、工具、权限、输入输出和执行链路的问题",
    r"材料将问题拆解、结构表达或模型复用作为核心",
    r"可作为 Agent/Skill 场景库案例",
    r"文章的结构线索集中在",
]

REFINEMENT_PROBLEM_SECTIONS = ["文章解决的问题", "文章/书籍解决的问题", "Problem addressed"]
REFINEMENT_ESSENTIAL_SECTIONS = ["一句话价值", "核心观点", "可连接主题"]
REFINEMENT_ESSENTIAL_ALIASES = {
    "一句话价值": ["One-line value", "One line value"],
    "核心观点": ["Core claims", "Core points", "Core argument"],
    "可连接主题": ["Connected topics", "Related topics"],
    "可复用模型": ["Reusable models or cases", "Reusable models"],
    "可复用案例": ["Reusable cases"],
    "候选提升": ["Promotion candidate"],
}


def check_refinement(path: Path, known_templates: list[str] | None = None, essential_aliases: dict[str, list[str]] | None = None, require_theme_cluster_at_refinement: bool = True) -> dict[str, Any]:
    return _check_refinement(path, known_templates, None, essential_aliases, require_theme_cluster_at_refinement)


BOILERPLATE_TOPICS_DEFAULT = frozenset({"Agent工作流", "Skill设计", "自动化系统", "内容生产", "表达写作", "AI写作"})


def resolve_essential_aliases(quality_cfg: dict[str, Any]) -> dict[str, list[str]]:
    """Merge a researcher's renamed-section aliases on top of the generic defaults.

    A researcher whose refinement template renames a canonical section (for example
    "核心观点" -> "核心知识点") only needs to declare the extra alias in
    ``quality.essential_aliases``; unrelated canonical names and their built-in
    English aliases keep working unchanged.
    """
    merged: dict[str, list[str]] = {key: list(values) for key, values in REFINEMENT_ESSENTIAL_ALIASES.items()}
    for canonical, extra_aliases in quality_cfg.get("essential_aliases", {}).items():
        existing = merged.setdefault(canonical, [])
        for alias in extra_aliases:
            if alias not in existing:
                existing.append(alias)
    return merged


def _check_refinement(path: Path, known_templates: list[str] | None = None, boilerplate_topics: set[str] | None = None, essential_aliases: dict[str, list[str]] | None = None, require_theme_cluster_at_refinement: bool = True) -> dict[str, Any]:
    """Run structural and content checks on a single refinement file.

    Returns blockers (must-fix) and warnings (informational).
    """
    if boilerplate_topics is None:
        boilerplate_topics = BOILERPLATE_TOPICS_DEFAULT
    if essential_aliases is None:
        essential_aliases = REFINEMENT_ESSENTIAL_ALIASES
    blockers: list[str] = []
    warnings: list[str] = []
    try:
        text = path.read_text("utf-8", errors="replace")
    except Exception as e:
        return {"file": str(path), "passed": False, "blockers": [f"unreadable: {e}"], "warnings": [], "issues": [f"unreadable: {e}"]}

    meta, body = split_frontmatter(text)
    sections = extract_sections(body)
    # Normalize renamed/English section names to their canonical Chinese equivalents
    _section_normalization = {}
    for cn, aliases in essential_aliases.items():
        for alias in aliases:
            if alias in sections:
                _section_normalization[cn] = sections[alias]
    sections.update(_section_normalization)

    has_problem = any(key in sections for key in REFINEMENT_PROBLEM_SECTIONS)
    if not has_problem:
        blockers.append(f"missing_problem_section (expected one of: {', '.join(REFINEMENT_PROBLEM_SECTIONS)})")

    essential = list(REFINEMENT_ESSENTIAL_SECTIONS)
    for section in essential:
        if section not in sections:
            aliases = essential_aliases.get(section, [])
            if not any(a in sections for a in aliases):
                blockers.append(f"missing_section: {section}")

    # 可复用模型 and 候选提升 are important but may be absent
    for section in ["可复用模型", "候选提升"]:
        if section not in sections:
            aliases = essential_aliases.get(section, [])
            if not any(a in sections for a in aliases):
                warnings.append(f"missing_section: {section}")

    # 可复用案例 is optional - not every source has one
    if "可复用案例" not in sections:
        aliases = essential_aliases.get("可复用案例", [])
        if not any(a in sections for a in aliases):
            warnings.append("missing_section: 可复用案例")

    # related_sources being empty is a warning, not a blocker
    related = meta.get("related_sources", [])
    if isinstance(related, list) and len(related) == 0:
        warnings.append("empty_related_sources")

    # theme_cluster must be a valid, non-placeholder value. Some researchers assign
    # theme_cluster during promotion review rather than at initial refinement time;
    # for them an empty cluster at gate-10 stage is expected, not a defect — only an
    # explicit placeholder string is a real error.
    cluster = meta.get("theme_cluster", "")
    if not cluster and not require_theme_cluster_at_refinement:
        warnings.append("missing_theme_cluster: not yet assigned — expected until promotion review runs")
    elif not cluster or cluster in ("未归类", "未分类"):
        if not cluster and not meta:
            warnings.append("missing_theme_cluster: no frontmatter metadata — add theme_cluster when metadata is available")
        else:
            blockers.append(f"invalid_theme_cluster: '{cluster}' is a placeholder, assign a real cluster")
    elif cluster == "AI知识管理":
        warnings.append(f"generic_theme_cluster: '{cluster}' — consider a more specific cluster if possible")

    # Content: core points boilerplate check
    core = sections.get("核心观点", "")
    core_lines = [l for l in core.split("\n") if l.strip()]
    if not core_lines:
        blockers.append("empty_core_points")
    else:
        template_hits = 0
        for line in core_lines:
            if any(re.search(ptn, line) for ptn in (known_templates or KNOWN_TEMPLATE_PATTERNS)):
                template_hits += 1
        if template_hits == len(core_lines):
            blockers.append("all_core_points_are_template_boilerplate")

    # Content: 可复用模型 should not be template
    model_text = sections.get("可复用模型", "") or sections.get("Reusable models or cases", "")
    if model_text:
        for ptn in (known_templates or KNOWN_TEMPLATE_PATTERNS):
            if re.search(ptn, model_text):
                blockers.append("template_model_text")
                break

    connected = sections.get("可连接主题", "") or sections.get("Connected topics", "") or sections.get("Related topics", "")
    if connected:
        topic_items = {line.strip().lstrip("- ").strip() for line in connected.split("\n") if line.strip() and line.strip().lstrip("- ").strip()}
        overlap = topic_items & boilerplate_topics
        if len(overlap) >= 4:
            blockers.append("generic_connected_topics_ge_4_boilerplate")

    # Content: 可复用案例 should not be template
    case_text = sections.get("可复用案例", "") or sections.get("Reusable cases", "")
    if case_text:
        for ptn in (known_templates or KNOWN_TEMPLATE_PATTERNS):
            if re.search(ptn, case_text):
                blockers.append("template_case_text")
                break

    # --- Placeholder: no section should contain placeholder text ---
    PLACEHOLDER_PATTERNS = [
        r"本文基于原文内容进行精炼提取[。.]?",
        r"（待补充[^）]*）",
        r"（核心观点已写入）",
        r"阅读原文获取具体[内容模型案例][。.]?",
    ]
    for _section_name, _section_text in sections.items():
        for _pp in PLACEHOLDER_PATTERNS:
            if re.search(_pp, _section_text):
                blockers.append(f"placeholder_in_{_section_name}: '{_section_text[:40]}'")
                break

    # --- Model quality: 可复用模型 should be a model, not a paraphrase ---
    model_text = sections.get("可复用模型", "")
    one_line = sections.get("一句话价值", "")
    # Block: model identical to one-line value (lazy paraphrase)
    if model_text and one_line and model_text.strip() == one_line.strip():
        blockers.append("model_equals_one_line_value: model is just a copy of the one-line summary")
    # Block: model too short to be a real model
    if model_text and len(model_text.strip()) < 30:
        blockers.append("model_too_short: < 30 chars, not a meaningful model")
    # Warning: model lacks structural elements
    if model_text and len(model_text) >= 30:
        has_structure = any(k in model_text for k in ("→", "->", "第一步", "第二步", "第三", "第一", "首先", "然后", "阶段", "步骤", "层级", "层"))
        if not has_structure:
            warnings.append("model_lacks_structure: consider adding flow (→), steps, or layers")

    # --- Problem quality: 文章解决的问题 should identify a problem, not just paraphrase ---
    problem_section = sections.get("文章解决的问题", sections.get("文章/书籍解决的问题", ""))
    if problem_section and one_line and problem_section.strip() == one_line.strip():
        blockers.append("problem_equals_one_line_value: problem statement is just a copy of the one-line summary")
    if problem_section and len(problem_section.strip()) < 30:
        blockers.append("problem_too_short: < 30 chars, not a meaningful problem statement")
    if problem_section and len(problem_section) >= 30:
        has_problem_lang = any(k in problem_section for k in ("如何", "怎么", "为什么", "是什么", "怎样", "痛点", "解决", "问题", "困难", "挑战"))
        if not has_problem_lang:
            warnings.append("problem_lacks_framing: consider stating what problem the article solves")

    # --- Depth: 核心观点 should have substantive detail ---
    core = sections.get("核心观点", "")
    if core:
        core_lines = [l.strip() for l in core.split("\n") if l.strip() and not l.strip().startswith("!") and not l.strip().startswith("[") and len(l.strip()) > 10]
        # Check: at least 2 substantive bullet points
        bullet_count = sum(1 for l in core.split("\n") if re.match(r'^\s*[\d\.\-]', l) and len(l.strip()) > 30)
        if bullet_count == 0 and len(core_lines) <= 1:
            warnings.append("shallow_core_points: no substantive bullets found")
        # Check: core points are not just extracted metadata lines
        first_bullet = ""
        for l in core.split("\n"):
            l = l.strip()
            if l.startswith(("1.", "2.", "3.", "4.", "5.", "- ")) and len(l) > 15:
                first_bullet = l
                break
        if first_bullet and re.match(r'^[\d\.-]+\s*(url|https?|http|id|created_at|source_file|author)', first_bullet, re.I):
            blockers.append("metadata_in_core_points: core points contain metadata instead of article content")
        elif not first_bullet:
            warnings.append("shallow_core_points: no substantive bullet points found")
    
    # --- Depth: 可复用模型 should be specific, not generic one-liner ---
    model_text = sections.get("可复用模型", "") or sections.get("Reusable models or cases", "")
    if model_text and len(model_text.strip()) < 40:
        warnings.append("shallow_model: model text too short (< 40 chars)")
    elif model_text and len(model_text.strip()) < 20:
        blockers.append("too_short_model: model text is < 20 chars")

    # --- Depth: total refinement should have meaningful content ---
    total_body_len = len(body.replace("\n", " ").strip()) if body else 0
    if total_body_len < 200:
        warnings.append(f"shallow_refinement: only {total_body_len} chars of body content")

    return {
        "file": str(path),
        "passed": len(blockers) == 0,
        "issues": blockers + warnings,
        "blockers": blockers,
        "warnings": warnings,
        "theme_cluster": meta.get("theme_cluster", ""),
    }

def gate_10(cfg: dict[str, Any], batch_name: str | None = None, batch_threshold: float = 0.3, known_templates: list[str] | None = None) -> dict[str, Any]:
    src_root = kb_path(cfg, "source_refinements")
    if not src_root.exists():
        return {"passed": False, "batch": batch_name, "scanned": 0, "error": "source_refinements_dir_not_found"}

    files = collect_markdown_files(src_root)
    quality_cfg = cfg.get("quality", {})
    if known_templates is None:
        known_templates = quality_cfg.get("template_patterns", KNOWN_TEMPLATE_PATTERNS)
    boilerplate_set = set(quality_cfg.get("boilerplate_topics", list(BOILERPLATE_TOPICS_DEFAULT)))
    batch_threshold = batch_threshold or quality_cfg.get("batch_model_repeat_threshold", 0.3)
    essential_aliases = resolve_essential_aliases(quality_cfg)
    require_theme_cluster_at_refinement = quality_cfg.get("require_theme_cluster_at_refinement", True)

    results = []
    for f in files:
        result = _check_refinement(f, known_templates, boilerplate_set, essential_aliases, require_theme_cluster_at_refinement)
        results.append(result)

    total = len(results)
    failures = [r for r in results if not r["passed"]]
    passed_count = total - len(failures)
    blocker_count = sum(len(r.get("blockers", [])) for r in results)

    model_texts: list[str] = []
    for f in files:
        try:
            text = f.read_text("utf-8", errors="replace")
            _, body = split_frontmatter(text)
            sections = extract_sections(body)
            model_texts.append(sections.get("可复用模型", "").strip())
        except Exception:
            model_texts.append("")

    model_counter: dict[str, int] = {}
    for t in model_texts:
        if t.strip():
            model_counter[t.strip()] = model_counter.get(t.strip(), 0) + 1

    batch_issues: list[str] = []
    repeat_rate = 0.0
    if model_counter and total > 0:
        most_common_text = max(model_counter, key=model_counter.get)
        most_common_count = model_counter[most_common_text]
        repeat_rate = most_common_count / total
        if repeat_rate >= batch_threshold:
            snippet = most_common_text[:60].replace("\n", " ")
            batch_issues.append(f"model_text_repeat_rate_{repeat_rate:.0%} ({most_common_count}/{total} files share '{snippet}...')")

    return {
        "passed": len(failures) == 0 and not batch_issues,
        "batch": batch_name or "all",
        "batch_threshold": batch_threshold,
        "scanned": total,
        "passed_count": passed_count,
        "failed_count": len(failures),
        "failures": failures,
        "blocker_count": blocker_count,
        "batch_model_repeat_rate": round(repeat_rate, 4),
        "batch_issues": batch_issues,
        "gate": "10",
    }



def render_gate_10(result: dict[str, Any]) -> str:
    lines = [
        "# Gate-10: Source Refinement Quality",
        "",
        "---",
        f"updated_at: {date.today().isoformat()}",
        f"batch: {result['batch']}",
        f"status: {'passed' if result['passed'] else 'blocked'}",
        f"scanned: {result['scanned']}",
        f"passed: {result['passed_count']}",
        f"failed: {result['failed_count']}",
        f"blocker_issues: {result.get('blocker_count', 0)}",
        f"batch_model_repeat_rate: {result['batch_model_repeat_rate']:.0%}",
        "---",
        "",
    ]
    if result["batch_issues"]:
        lines.append("## Batch-Level Issues")
        for issue in result["batch_issues"]:
            lines.append(f"- {issue}")
        lines.append("")
    if result["failures"]:
        # Separate blocker-only failures from warning-only failures
        blocker_failures = [f for f in result["failures"] if f.get("blockers")]
        warning_failures = [f for f in result["failures"] if not f.get("blockers") and f.get("warnings")]
        if blocker_failures:
            lines.append("## Blockers (must fix before commit)")
            for f in blocker_failures:
                lines.append(f"- {f['file']}: {', '.join(f.get('blockers', []))}")
            lines.append("")
        if warning_failures:
            lines.append("## Warnings (review recommended, not blocking)")
            for f in warning_failures:
                w = f.get("warnings", f.get("issues", []))
                lines.append(f"- {f['file']}: {', '.join(w[:5])}")
            lines.append("")
    if result["passed"]:
        lines.append("## Result: PASSED")
    else:
        lines.append("## Result: BLOCKED --- fix blocker issues and/or batch issues before committing")
    return "\n".join(lines).rstrip() + "\n"

