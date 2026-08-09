"""Evidence-intake workspace initialization and audit services."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Callable

from kbm.platform.paths import kb_path, system_file


def evidence_intake_root(cfg: dict[str, Any]) -> Path:
    return kb_path(cfg, "system") / "evidence-intake"


def system_evidence_refinement_root(cfg: dict[str, Any]) -> Path:
    subdir = cfg.get("source_refinement_subdirs", {}).get("system_evidence_fill", "系统补证")
    return kb_path(cfg, "source_refinements") / subdir


def evidence_intake_expected_dirs(cfg: dict[str, Any]) -> dict[str, list[Path]]:
    intake = evidence_intake_root(cfg)
    fill = system_evidence_refinement_root(cfg)
    return {
        "system_intake": [
            intake / "candidates", intake / "extracted", intake / "needs-ocr",
            intake / "needs-manual-review", intake / "rejected",
        ],
        "system_evidence_refinements": [
            fill, fill / "官方文档", fill / "研究论文", fill / "行业报告",
            fill / "案例材料", fill / "临时事实核查", fill / "待人工确认",
        ],
    }


def init_evidence_intake(
    cfg: dict[str, Any],
    apply: bool = False,
    prepare_system: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    if prepare_system is not None:
        prepare_system(cfg)
    expected = evidence_intake_expected_dirs(cfg)
    created: list[dict[str, str]] = []
    existing: list[dict[str, str]] = []
    for group, paths in expected.items():
        for path in paths:
            item = {"group": group, "path": str(path)}
            if path.exists():
                existing.append(item)
                continue
            created.append(item)
            if apply:
                path.mkdir(parents=True, exist_ok=True)
    ledger = system_file(cfg, "evidence-fill-ledger.jsonl")
    if apply and not ledger.exists():
        ledger.parent.mkdir(parents=True, exist_ok=True)
        ledger.write_text("", encoding="utf-8")
    return {
        "apply": apply,
        "created_count": len(created),
        "existing_count": len(existing),
        "created": created,
        "existing": existing,
        "ledger": str(ledger),
        "system_evidence_refinement_root": str(system_evidence_refinement_root(cfg)),
    }


def evidence_intake_audit(cfg: dict[str, Any]) -> dict[str, Any]:
    missing: list[dict[str, str]] = []
    present: list[dict[str, str]] = []
    for group, paths in evidence_intake_expected_dirs(cfg).items():
        for path in paths:
            item = {"group": group, "path": str(path)}
            (present if path.exists() and path.is_dir() else missing).append(item)
    ledger = system_file(cfg, "evidence-fill-ledger.jsonl")
    ledger_ok = ledger.exists()
    if not ledger_ok:
        missing.append({"group": "active_ledger", "path": str(ledger)})
    return {
        "passed": not missing,
        "missing_count": len(missing),
        "present_count": len(present),
        "ledger": str(ledger),
        "ledger_exists": ledger_ok,
        "system_evidence_refinement_root": str(system_evidence_refinement_root(cfg)),
        "missing": missing,
        "present": present,
    }


def render_evidence_intake_audit(result: dict[str, Any]) -> str:
    lines = [
        "# Evidence Intake Audit", "", "---",
        f"updated_at: {date.today().isoformat()}", "stage: system",
        f"status: {'passed' if result['passed'] else 'missing'}", "---", "",
        "## Summary", "", f"- passed: {str(result['passed']).lower()}",
        f"- missing_count: {result['missing_count']}",
        f"- present_count: {result['present_count']}",
        f"- ledger_exists: {str(result['ledger_exists']).lower()}",
        f"- ledger: `{result['ledger']}`",
        f"- system_evidence_refinement_root: `{result['system_evidence_refinement_root']}`",
        "", "## Missing", "",
    ]
    lines.extend(
        [f"- {item['group']}: `{item['path']}`" for item in result["missing"]]
        or ["- None."]
    )
    lines.extend(["", "## Present", ""])
    lines.extend(
        [f"- {item['group']}: `{item['path']}`" for item in result["present"]]
        or ["- None."]
    )
    return "\n".join(lines).rstrip() + "\n"


def render_source_capabilities(cfg: dict[str, Any], intake: dict[str, Any]) -> str:
    del cfg  # Reserved for future adapter-specific capability reporting.
    lines = [
        "# Source Capabilities", "", "---",
        f"updated_at: {date.today().isoformat()}", "stage: system", "status: active",
        "---", "", "## Intake Boundary", "",
        "- Unreadable, garbled, unsupported, or permission-uncertain sources must not enter source refinements.",
        "- System-found evidence must be isolated in evidence-intake first.",
        "- Durable system-found evidence may enter the source-refinement layer only under the separate system evidence fill directory.",
        "- Fact-check-only evidence stays in the ledger unless deliberately promoted.",
        "", "## Extraction Quality States", "", "- extract_ok",
        "- extract_needs_cleanup", "- ocr_required", "- layout_complex",
        "- mojibake_failed", "- manual_review_required", "- unsupported_source",
        "", "## Current Skeleton", "",
        f"- evidence_intake_audit_passed: {str(intake['passed']).lower()}",
        f"- system_evidence_refinement_root: `{intake['system_evidence_refinement_root']}`",
    ]
    return "\n".join(lines).rstrip() + "\n"
