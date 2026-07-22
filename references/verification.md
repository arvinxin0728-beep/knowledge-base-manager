# Verification Workflow

Use this reference when materials contain market data, company claims, rankings, financial/legal/medical claims, product capability claims, personnel incidents, or public-facing accusations.

## Queue

Run:

```bash
python3 scripts/kb_manager.py verification-queue --config <kb-config> --apply
```

This creates `<system>/verification-queue.jsonl` with files that need checking.

The queue is rebuildable. Do not treat it as the permanent record of verification decisions.

## Result Ledger

Record verification decisions in `<system>/verification-results.jsonl`:

```bash
python3 scripts/kb_manager.py verify-claim \
  --config <kb-config> \
  --id <queue-item-id> \
  --status verified \
  --claim "specific claim checked" \
  --evidence "official URL or local evidence path" \
  --note "short result" \
  --apply-status
```

Allowed statuses:

- `pending`
- `verified`
- `rejected`
- `insufficient_evidence`
- `not_applicable`

Then refresh the merged report:

```bash
python3 scripts/kb_manager.py verification-status --config <kb-config> --apply
```

This writes `<system>/verification-status.md`.

## Verification Fields

Each queue item should be resolved by adding or tracking:

- `status`: `pending`, `verified`, `rejected`, `insufficient_evidence`
- `claim`: the specific claim being checked
- `source_file`: local file containing the claim
- `verify_with`: primary source, official documentation, financial filing, reputable report, or live test
- `evidence_url_or_path`: where the check was performed
- `verified_at`: date
- `note`: short result

## Rule

Do not upgrade high-risk claims into public articles, business decisions, or recommendations until verification is complete. Internal topic pages may keep them as source-derived leads.

`quality-gate` treats unresolved verification items in output artifacts as blockers. Pending verification in source refinements or topic pages remains a warning unless the user is making a public, business-critical, legal, medical, financial, or current-fact output.
