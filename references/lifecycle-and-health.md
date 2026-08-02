# Knowledge Lifecycle and Health Review

Use this reference when auditing knowledge promotion, demotion, rollback, lifecycle status, health status, stale knowledge, or periodic review.

## Core principle

A knowledge base must have both:

1. Promotion: moving source material into topic pages, reusable assets, and outputs.
2. Demotion: moving weak, stale, duplicated, unsupported, or low-value knowledge back into revision, evidence gathering, parking, or archival states.

Promotion without demotion creates content inflation. Health review prevents once-qualified knowledge from becoming silently obsolete.

## Lifecycle status

Formal knowledge artifacts in topic pages, reusable assets, and outputs may use:

- `candidate`: worth considering, not yet part of the trusted working set.
- `draft`: usable as a working draft but not yet stable.
- `active`: trusted enough for reuse in current thinking or output.
- `needs_revision`: structurally weak, unclear, repetitive, or below current quality standard.
- `needs_evidence`: claim or artifact may be useful, but evidence is missing or insufficient.
- `parked`: not wrong, but currently low-use, low-priority, or not connected to active questions.
- `superseded`: replaced by a newer or better artifact.
- `deprecated`: no longer recommended for reuse.
- `archived`: retained for traceability, not for active reuse.

Do not confuse lifecycle with publication status. A `publishable_draft` can still be `needs_evidence` if fact claims are not verified.

## Health status

Formal knowledge artifacts may use:

- `healthy`: current, evidenced, reusable, and structurally valid.
- `review_due`: review date has arrived or the artifact has not been reviewed under the current standard.
- `stale`: time-sensitive claims or operational advice are likely outdated.
- `weak_evidence`: evidence is absent, too thin, or not traceable.
- `conflicted`: overlaps with or contradicts another artifact.
- `low_reuse`: valid but rarely connected to active topics, assets, or outputs.
- `deprecated`: health review concluded it should not guide new work.

Recommended fields:

```yaml
lifecycle_status: active
health_status: healthy
last_health_reviewed_at: YYYY-MM-DD
next_review_at: YYYY-MM-DD
```

Keep `updated_at` for knowledge changes. Keep `last_health_reviewed_at` for review events. A pure health review may update `last_health_reviewed_at` without changing `updated_at` if no knowledge content changes.

## Demotion triggers

Recommend demotion or rollback when any condition holds:

- Missing or insufficient `evidence_from` for the artifact type.
- Failed current structure or quality gate.
- Publishable article fails genre, anti-fluff, evidence, or publication boundary rules.
- Time-sensitive claims are beyond review cycle.
- A newer artifact supersedes the same judgment.
- Duplicate aliases, unresolved links, or conflicting topic ownership make reuse unsafe.
- The artifact has no clear parent topic, active question, output scenario, or reusable asset role.

Default recommended actions:

| Finding | Recommended action |
|---|---|
| Missing lifecycle field | add lifecycle metadata; do not demote automatically |
| Missing health field | add health metadata; mark `review_due` until reviewed |
| Missing evidence | `needs_evidence` |
| Failed structure/anti-fluff | `needs_revision` |
| Outdated high-risk fact claims | `stale` or `needs_evidence` |
| Duplicate or superseded artifact | `superseded`, `parked`, or merge review |
| Valid but unused | `parked` after human confirmation |
| Wrong or harmful | `deprecated` or `archived` after human confirmation |

## Review cadence

Default maximum intervals:

- Topic pages: 60 days.
- Topic MOCs: 90 days.
- Reusable methods/frameworks: 90 days.
- Cases: 90 days.
- Expressions/golden lines: 180 days.
- Feynman explanations: 90 days.
- Solution materials: 60 days.
- Article drafts: 30 days.
- Publishable drafts: 14 days.
- High-risk fact-heavy outputs: 14 days.

Shorten the cadence for active projects, public publication, product/tool claims, market data, legal/medical/financial content, or rapidly changing AI/tooling topics.

## Operating rule

Audits should report recommended actions first. Do not automatically move, delete, archive, or demote formal artifacts unless the user explicitly asks for an apply-mode lifecycle migration and the target files are resolved.

When the user asks “what should I do next,” prioritize:

1. Blockers that make reuse unsafe.
2. `needs_evidence` and `needs_revision`.
3. `review_due` / `stale` high-value artifacts.
4. Superseded or duplicate consolidation.
5. Low-reuse parking/archive decisions.

## Deterministic commands

Use:

```bash
python3 scripts/kb_manager.py audit-lifecycle --config <config> --apply
python3 scripts/kb_manager.py audit-knowledge-health --config <config> --apply
python3 scripts/kb_manager.py init-lifecycle-health --config <config> --apply
```

`init-lifecycle-health --apply` is for approved migration of legacy promoted artifacts. It fills missing lifecycle and health fields, sets `health_status: review_due` instead of claiming `healthy`, updates `updated_at`, normalizes freshness filenames, and refreshes wikilinks.

Use these before claiming that promotion governance is complete.
