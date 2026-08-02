# Source Intake and Extraction Control

Use this reference when the knowledge system finds or receives source material whose format, readability, extraction quality, or permission boundary is uncertain.

## Principle

Unreadable or unverified sources must not enter formal source refinements.

If a source cannot be read with acceptable extraction quality:

1. do not refine it;
2. do not promote it;
3. do not cite it as evidence;
4. create an intake diagnostic record;
5. try bounded conversion/OCR only when allowed;
6. park, reject, or ask for human decision when still unresolved.

This prevents bad extraction from contaminating topic pages, reusable assets, and outputs.

## Intake zones

Create a system intake area:

```text
00-system/evidence-intake/
├── candidates/
├── extracted/
├── needs-ocr/
├── needs-manual-review/
└── rejected/
```

Create a separate source-refinement area for system-found durable evidence:

```text
10-source-refinements/system-evidence-fill/
├── official-docs/
├── papers/
├── reports/
├── cases/
├── fact-check-only/
└── needs-human-confirmation/
```

In a localized profile, folder names may be translated, but the roles must remain distinct.

## Source origin policy

System-found evidence may enter the source-refinement layer only after intake and extraction quality checks.

Do not mix it with user-saved/manual source libraries. Use a separate subdirectory and explicit metadata:

```yaml
source_origin: system_evidence_fill
evidence_gap_id:
target_artifact:
discovery_method: bounded_evidence_fill
human_approved:
storage_policy: durable_refinement
```

Default rule:

- user-saved material: may support promotion according to normal source quality rules.
- system evidence fill material: may fill an existing evidence gap; it must not create a new topic expansion loop unless human-approved.
- fact-check-only material: stays in the evidence ledger unless deliberately promoted to durable refinement.
- failed/uncertain material: stays in intake and cannot support 20/30/40 artifacts.

## Extraction quality states

Use these states before source refinement:

- `extract_ok`: readable enough for refinement.
- `extract_needs_cleanup`: usable after bounded cleanup.
- `ocr_required`: no usable text layer or image/scanned source.
- `layout_complex`: tables, columns, equations, footnotes, or page layout may distort meaning.
- `mojibake_failed`: garbled characters or encoding failure.
- `manual_review_required`: machine cannot make a safe decision.
- `unsupported_source`: unsupported type or access boundary.

Only `extract_ok` and approved `extract_needs_cleanup` may enter formal source refinement.

## Diagnostic record

Each uncertain source should produce a diagnostic record:

```yaml
source_id:
source_file:
source_url:
detected_format:
detected_problem:
attempted_extractors:
extraction_quality_score:
failure_reason:
recommended_next_action:
human_decision_required:
status:
```

## Bounded repair budget

Do not loop on difficult sources.

Default repair limits:

- maximum extractor attempts: 2
- maximum OCR attempts: 1
- maximum sample pages before decision: 20
- stop when extraction passes, budget is exhausted, permission is unclear, or human decision is required.

## Durable vs ledger-only storage

| Source use | Storage | Enters source refinements | Can support 20/30/40 |
|---|---|---:|---:|
| Book, paper, report, official document, high-quality case | system-evidence-fill source-refinement subdirectory + ledger | yes | yes |
| Temporary fact check such as version/date/price/current status | evidence-fill ledger | no by default | only current output/check |
| Low-quality, unreadable, inaccessible, or irrelevant source | rejected / needs-review intake zone | no | no |

## Commands

Initialize and audit the intake skeleton:

```bash
python3 scripts/kb_manager.py init-evidence-intake --config <config> --apply
python3 scripts/kb_manager.py audit-evidence-intake --config <config> --apply
```

The initialization command may create directories and empty ledgers. It must not browse, ingest, OCR, refine, promote, or mutate existing formal artifacts.
