# Promotion Control and Resume

Use this reference for multi-stage work that moves knowledge beyond source refinement into topic pages, reusable assets, or outputs.

The source-processing pipeline has its own SQLite ledger. Promotion and output work needs a separate human-control layer because it consumes model judgment, changes the knowledge structure, and may create high-cost artifacts.

## Cost Tiers

| Tier | Purpose | Inputs | Allowed result |
|---|---|---|---|
| Low-cost scan | Find opportunities without rereading everything. | Index, titles, tags, existing source refinements, topic pages, MOCs. | Candidate report, counts, risk flags, next-step recommendation. |
| Medium-cost review | Decide what deserves promotion. | Candidate sources, topic pages, asset-output matrix, limited source rereads. | `asset-output-candidates.md`, updated `topic-clusters.md`, updated `promotion-review.md`, approval request. |
| High-cost generation | Create durable 20/30/40 artifacts. | Approved candidates, minimal supporting sources, explicit target artifact types. | Topic pages, reusable assets, outputs, link refresh, quality review. |

Default to the lowest tier that can answer the user's request. Do not do high-cost generation just because enough material exists.

## Human Approval Gates

Ask for explicit user approval before continuing when the next stage changes cost, risk, or structure.

| Gate | Ask before | Reason |
|---|---|---|
| A. Large source batch | Processing a large batch, a new library, or an ambiguous source set. | Controls token and time cost. |
| B. Topic structure change | Creating new topic structure, merging clusters, splitting clusters, or changing MOC organization. | Changes the knowledge map. |
| C. High-cost asset/output generation | Creating or substantially rewriting heavy 30-reusable-assets or 40-outputs from candidates. | Consumes judgment and may create reusable public artifacts. Heavy artifacts usually need `evidence_from` listing ≥3 supporting source refinements. Lightweight cases and expressions may use one strong source with explicit attribution and fact boundary. |
| D. External verification | Browsing, fact-checking, or validating company, market, legal, medical, financial, or current claims. | Adds external dependency and may change conclusions. |
| E. Destructive or source-library mutation | Deleting, moving, renaming, deduping, or normalizing source-library files. | Changes user-owned source material. |

The user can grant scope-limited approval with phrases such as "process 30 articles", "continue this stage", "create outputs for this cluster", or "apply your recommendation". Treat that approval as applying only to the stated batch, stage, or artifact set.

If the next step changes artifact type, cost tier, risk level, or source-library state, stop and ask again.

## Work That Does Not Need Extra Approval

Proceed without another confirmation when the user has already asked for maintenance and the operation is read-only, deterministic, or directly follows from files just written:

- audit, status, counts, and source discovery;
- low-cost candidate scans;
- deterministic report refreshes under `00-system`;
- Obsidian frontmatter, relation, MOC, and link refresh after creating or updating knowledge files;
- output evaluation and verification queue refresh after generation;
- checkpoint writes to record progress.

## Checkpoint Files

Store run state inside the mapped system directory, not inside the portable skill:

- `<ai_knowledge_base>/00-system/active-run-state.json`
- `<ai_knowledge_base>/00-system/run-log.jsonl`
- `<ai_knowledge_base>/00-system/asset-output-candidates.md`
- `<ai_knowledge_base>/00-system/promotion-decision.jsonl`
- `<ai_knowledge_base>/00-system/quality-gate.md`

Use the localized mapped directory names when the user's configuration maps `00-system` to another folder.

`active-run-state.json` is the latest resumable state. `run-log.jsonl` is append-only transition history. `promotion-decision.jsonl` is the idempotent decision ledger for cluster promotion results. `asset-output-candidates.md` is the human-readable approval surface. `quality-gate.md` records whether the knowledge base is blocked by relation, portability, topic-page, asset, output-quality, or verification issues.

## Checkpoint Schema

Use this shape for `active-run-state.json`:

```json
{
  "schema_version": 1,
  "run_id": "YYYYMMDD-HHMMSS-short-objective",
  "objective": "What the user asked for",
  "status": "waiting_for_approval",
  "current_stage": "medium_cost_review",
  "cost_tier": "medium",
  "started_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "approved_scope": {
    "source_types": ["public_account_article"],
    "limit": 30,
    "artifact_types": []
  },
  "completed_steps": [],
  "pending_steps": [],
  "source_cursor": {
    "processed_count_before": 0,
    "processed_count_after": 0,
    "last_source": ""
  },
  "candidates": [],
  "approved_candidates": [],
  "generated_files": [],
  "last_successful_command": "",
  "next_recommended_action": "",
  "stop_reason": ""
}
```

Allowed `status` values:

- `running`
- `waiting_for_approval`
- `paused_by_user`
- `completed`
- `failed`

Append each material transition to `run-log.jsonl` with `run_id`, timestamp, event type, stage, summary, and affected files.

Append or refresh promotion decisions in `promotion-decision.jsonl` whenever `promote --apply` or `run --apply` updates cluster actions. Each row should record the cluster, question, source count, score, action, artifact type, fact risk, evidence source ids, approval requirement, and whether the item has been approved. Re-running the same deterministic review on the same day should not create duplicate decision rows.

## Resume Protocol

At the start of a multi-stage request:

1. Inspect `active-run-state.json` if it exists.
2. If status is `running`, `waiting_for_approval`, `paused_by_user`, or `failed`, decide whether the current user request continues that run.
3. Resume from the last completed step when the objective and scope match.
4. Start a new run only when the user request is unrelated, the prior run is `completed`, or the user explicitly asks to restart.
5. Never reprocess already committed sources; use the pipeline ledger and `processed-index.jsonl`.

When the user stops, pauses, or rejects the next stage, do not treat the work as failed. Write `active-run-state.json` with `status: "paused_by_user"` or `status: "waiting_for_approval"` and record the exact next safe action.

## Approval Surface

Before Gate C high-cost generation, produce or update `asset-output-candidates.md` with:

- candidate cluster or artifact title;
- supporting source count and representative sources;
- proposed artifact type;
- expected token/cost tier;
- expected output location;
- evidence strength;
- fact-risk level;
- reason to generate now;
- reason to defer if not approved.

Candidate reports must classify opportunities instead of leaving them as `unclassified`. Use concrete pools: `topic_candidates`, `case_candidates`, `expression_candidates`, `framework_candidates`, `method_candidates`, `output_candidates`, and `moc_split_candidates`. For each item record `candidate_id`, `artifact_type`, `parent_topic`, `source_refs`, `evidence_strength`, `fact_risk`, and `recommended_action`.

Do not generate the full artifact until the user approves the candidate or asks for that artifact directly.

After generating, splitting, merging, or rewriting 20/30/40 artifacts, run `quality-gate --apply --strict`. If it fails, the task is not complete; either fix blockers or record the run as `paused_by_user`, `waiting_for_approval`, or `failed` with the next safe action.

Deterministic promotion stubs are not durable knowledge artifacts. If `promote --create-stubs` is used, write stubs under `<system>/stubs/` only. Do not place `TBD` stub files directly in formal topic-page, reusable-asset, or output folders.
