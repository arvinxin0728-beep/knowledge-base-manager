# Evidence Gaps and Bounded Evidence Fill

Use this reference when a topic page, reusable asset, or output cannot become healthy because supporting sources are missing, weak, stale, one-sided, or too dependent on low-authority material.

## Principle

Do not loop endlessly. Convert vague weakness into a bounded evidence gap.

The goal is not to complete all research. The goal is to decide, within a fixed budget, whether to strengthen, limit, downgrade, park, or abandon an artifact.

System-found evidence must pass the source intake and extraction controls before it can become durable evidence. See `source-intake-and-extraction.md` when a candidate source is a PDF, OCR-prone file, unsupported format, garbled extraction, or externally discovered source.

## Evidence gap fields

Each gap should record:

```yaml
gap_id:
target_artifact:
gap_type:
why_needed:
current_evidence_count:
current_best_tier:
current_source_channels:
preferred_source_type:
max_sources_to_add:
max_search_queries:
max_reading_items:
stop_condition:
recommended_action:
status: open
```

## Gap types

- `missing_authoritative_source`: no A/B source supports an important artifact.
- `only_low_tier_sources`: evidence exists but is mostly C/D tier.
- `single_channel_evidence`: sources are too concentrated in one channel, commonly public accounts.
- `high_fact_risk_without_primary_evidence`: fact-risk content lacks primary/current evidence.
- `stale_high_sensitivity_evidence`: time-sensitive source evidence is stale.
- `thin_evidence`: evidence count is below the artifact minimum.
- `missing_counterpoint`: the topic has one-sided evidence and needs opposing or alternative views.
- `publishable_output_needs_fact_support`: article/output is close to publication but lacks verification-grade sources.

## Budget rules

Default bounded fill budget:

- `max_sources_to_add: 3`
- `max_search_queries: 5`
- `max_reading_items: 3`

Never continue just because more material may exist. Stop when:

- enough A/B evidence is found;
- the budget is exhausted;
- the artifact should be downgraded or parked;
- external research is required beyond the current knowledge-base run.

## Resolution states

- `filled`: evidence is sufficient now.
- `partially_filled`: improved but still limited.
- `not_found`: not found within budget.
- `not_worth_pursuing`: artifact value does not justify further research.
- `downgrade_recommended`: artifact should become `needs_evidence`, `needs_revision`, or draft.
- `park_recommended`: keep for possible future use, not active reuse.
- `external_research_required`: needs deliberate external research.

## Deterministic command

Use:

```bash
python3 scripts/kb_manager.py audit-evidence-gaps --config <config> --apply
```

This command creates the registry. It must not browse, ingest new sources, or mutate formal artifacts.

Before filling a gap with system-found evidence, initialize and audit the intake skeleton:

```bash
python3 scripts/kb_manager.py init-evidence-intake --config <config> --apply
python3 scripts/kb_manager.py audit-evidence-intake --config <config> --apply
```
