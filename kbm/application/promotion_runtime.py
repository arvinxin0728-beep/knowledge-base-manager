"""Promotion decisions, resumable checkpoints, and safe system-area stubs."""

from __future__ import annotations

import json
from datetime import date
from typing import Any

from kbm.application.promotion import artifact_candidates
from kbm.domain.naming import safe_stem
from kbm.platform.clock import now_iso
from kbm.platform.jsonl import read_jsonl_objects as read_index_objects
from kbm.platform.paths import kb_path, system_file

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
