# Verified Closed Loops

Use this reference when running knowledge-base audits after a mechanism has been validated in practice. A closed loop is stronger than a rule: it must include trigger, action, state change, audit refresh, and a verified result.

## Principle

Do not treat a mechanism as complete just because the script can detect a problem. A mechanism is validated only when the system can:

1. detect the issue;
2. make or recommend the correct state transition;
3. record the decision and basis;
4. refresh deterministic reports;
5. pass quality gates or surface the remaining issue as a non-blocking warning with the correct next action.

## Closed loop 1: Evidence gap and bounded evidence fill

Use when an artifact lacks authoritative, diverse, fresh, or primary evidence.

Validated path:

```text
evidence gap detected
→ bounded candidate search
→ candidate record under system evidence intake
→ approved/refined sources enter 10-source-refinements/system-evidence
→ target artifact evidence_from is updated
→ verification result is recorded
→ evidence gap and quality gate are refreshed
```

Required records:

- `00-system/evidence-intake/candidates/<date> <gap_id> <target>.md`
- `00-system/active/evidence-fill-ledger.jsonl`
- source refinements under the configured system-evidence refinement directory
- verification result in `verification-results.jsonl`

Passing result:

- The target no longer has `single_channel_evidence` or `high_fact_risk_without_primary_evidence` if the added sources resolve those gaps.
- A publication-grade artifact must also have a verified or explicitly bounded verification result.
- `quality-gate` has no blockers.

If the evidence remains insufficient, do not force the artifact to healthy. Mark it `needs_evidence` / `weak_evidence` and leave the evidence gap open.

## Closed loop 2: Health review to healthy

Use when a `review_due` artifact appears to be current, evidenced, reusable, and structurally valid.

Validated path:

```text
review_due detected
→ review evidence, output quality, editorial quality, verification, and gates
→ update health metadata
→ add a health review record
→ refresh knowledge-health and quality-gate
```

Required state:

```yaml
lifecycle_status: active
health_status: healthy
last_health_reviewed_at: YYYY-MM-DD
next_review_at: YYYY-MM-DD
```

Required body record:

```markdown
## 健康评审记录

- reviewed_at:
- health_status:
- lifecycle_status:
- next_review_at:
- review_basis:
- remaining_boundary:
- review_decision:
```

Passing result:

- The artifact disappears from `knowledge-health.md`.
- `quality-gate` remains passed.
- `updated_at` is updated only if the review changed knowledge content or formal knowledge metadata. A pure review event may update `last_health_reviewed_at` without changing `updated_at`.

## Closed loop 3: Health review to weak evidence / needs evidence

Use when an artifact is structurally usable but not evidence-healthy.

Validated path:

```text
review_due detected
→ evidence gap confirms weak or narrow support
→ downgrade lifecycle/publication maturity
→ record insufficient evidence
→ refresh health, evidence gap, verification, and quality gate
```

Required state for a downgraded output:

```yaml
status: needs_evidence
lifecycle_status: needs_evidence
health_status: weak_evidence
article_maturity: article_draft
publish_status: needs_evidence_before_publication
last_health_reviewed_at: YYYY-MM-DD
next_review_at: YYYY-MM-DD
```

For non-article outputs, use the equivalent maturity/status fields available for that output type. Do not leave a downgraded article as `publishable_draft`.

Required verification result:

```text
status: insufficient_evidence
```

Passing result:

- The artifact remains in `knowledge-health.md` as `weak_evidence`, not `review_due`.
- The artifact remains in `evidence-gap-registry.md` if evidence is still weak.
- `verification_unresolved_outputs` is 0.
- `quality-gate` has no blockers; the remaining issue appears as a warning / next action.

## Link maintenance boundary

When running any closed loop that renames files, distinguish knowledge freshness from link maintenance:

- update `updated_at` only for the artifact whose knowledge content, evidence, lifecycle, health, or publication maturity changed;
- for backlinks changed only by wikilink migration, write `obsidian_links_updated`;
- do not cascade `updated_at` or filename-date changes across backlinks merely because a title changed.

This prevents maintenance activity from making stale knowledge look newly updated.
