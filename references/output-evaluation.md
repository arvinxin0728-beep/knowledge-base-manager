# Output Evaluation

Use this reference when reviewing files under `40-outputs`.

## Deterministic Review

Run:

```bash
python3 scripts/kb_manager.py evaluate-outputs --config <kb-config> --apply
```

This writes `<system>/output-quality-review.md`.

## Minimum Output Checks

A usable output should have:

1. Source theme or topic page reference.
2. Audience, task, or scenario.
3. Core message or answer.
4. Fact boundary or verification note.
5. Evidence boundary: what the output is based on and which source/theme supports it.
6. Scope or limits: where the output applies, does not apply, or still needs verification.
7. Enough substance to be useful, not only a placeholder.
8. No `TBD`, `TODO`, or equivalent unfinished placeholders.

The script performs a mechanical first pass. Codex should still do a human-quality review for argument strength, evidence quality, and style.

## Rubric Review

For reusable or public-facing outputs, create a review surface:

```bash
python3 scripts/kb_manager.py output-review --config <kb-config> --apply
```

Record the review result:

```bash
python3 scripts/kb_manager.py record-output-review \
  --config <kb-config> \
  --file "<relative-output-file>" \
  --status usable \
  --scores '{"argument_clarity":4,"evidence_strength":4,"portability":5,"scope_control":4,"actionability":4,"reuse_value":4}' \
  --note "short review result" \
  --apply-status
```

Allowed statuses:

- `usable`
- `needs_revision`
- `rejected`
- `not_applicable`

Review dimensions use a 1-5 score:

- `argument_clarity`
- `evidence_strength`
- `portability`
- `scope_control`
- `actionability`
- `reuse_value`

Before declaring a generation task complete, run:

```bash
python3 scripts/kb_manager.py quality-gate --config <kb-config> --apply --strict
```

`quality-gate` treats mechanically weak outputs and rubric-reviewed outputs marked `needs_revision` or `rejected` as blockers, alongside relation, portability, topic-page, asset, and unresolved output-verification issues.
