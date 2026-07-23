# Recoverable Processing Pipeline

Use this reference when processing many sources, resuming interrupted work, or operating across multiple Codex tasks.

This pipeline controls source extraction and source-refinement commits. For human approval gates, token-cost tiers, and resumable topic/asset/output promotion work, also read `promotion-control-and-resume.md`.

## State Model

```text
discovered -> extracted -> refining -> refined -> committed
                    |          |
                    +-> failed <-+
```

- `discovered`: source metadata is registered in SQLite.
- `extracted`: deterministic text and chunks exist under `<system>/runtime/artifacts/<job_id>/`.
- `refining`: a worker holds a time-limited lease and is generating a source refinement.
- `refined`: the AI-generated note and metadata passed validation and are staged durably.
- `committed`: the note is in `source_refinements` and its canonical index record is present.
- `failed`: extraction or refinement failed with stage, attempt count, and error recorded.

SQLite in the configured runtime directory is the task ledger. Markdown and `processed-index.jsonl` remain the portable knowledge artifacts.

For new installations, keep SQLite and intermediate artifacts in device-local application state by setting `pipeline.runtime_storage` to `local`. Legacy installations remain compatible and can be migrated explicitly; the synced knowledge base remains the home of portable configuration, indexes, and final knowledge artifacts.

## Batch Protocol

Initialize once:

```bash
python3 scripts/kb_pipeline.py --config <config> init
```

Discover sources and extract a bounded batch:

```bash
python3 scripts/kb_pipeline.py --config <config> prepare --limit 10
```

When a configuration contains multiple libraries, constrain a batch with `--source-type ebook`, `--source-type article`, or `--source-type public_account_article`. Apply the same filter to `claim`.

Claim extracted jobs before model work:

```bash
python3 scripts/kb_pipeline.py --config <config> claim --worker <stable-worker-name> --limit 5 --lease-minutes 120
```

For every claimed job:

1. Read `extracted_text` or the relevant records in `chunks_file`.
2. Follow `references/reading-and-refinement.md`.
3. Write a refinement Markdown file with every required heading.
4. Write metadata JSON with `title`, `topics`, `fact_risk`, and `fact_check_required`.
5. Submit the result before the lease expires:

```bash
python3 scripts/kb_pipeline.py --config <config> submit \
  --job-id <id> --lease-token <token> \
  --refinement <note.md> --metadata <metadata.json>
```
```

> **Gate-10 enforcement**: `submit` and `adopt-existing` automatically run `check-refinement` before accepting. Blocked-by-gate10 errors require fixing the refinement before retry.


## Quality Gate (Gate-10)

Before committing, all refinements must pass the gate-10 quality check.
Run it against the batch or all current refinements:

```bash
python3 scripts/kb_manager.py gate-10 --config <config>
```

The gate performs three categories of check:

**Batch-level (hard block):**
- Model-text repetition rate above threshold (default 30%).
  If 30%+ of refinements in the same batch share an identical "可复用模型",
  the AI is likely template-filling instead of reading source material.

**Per-file blockers (must-fix):**
- Core points are all template boilerplate (AI did not extract actual content).
- Model text matches a known fabrication pattern.
- Connected topics are the generic boilerplate set (>=4 of the 6 common fake topics).
- Case text matches a known fabrication pattern.
- Missing essential sections (一句话价值, 核心观点, 可连接主题).

**Per-file warnings (review recommended, not blocking):**
- Missing optional sections (可复用案例, 可复用模型, 候选提升).
- Empty related_sources (acceptable for early/singleton sources).
- Generic theme_cluster (AI知识管理, 未归类).

Pass the gate with `--strict` to exit non-zero on failure:

```bash
python3 scripts/kb_manager.py gate-10 --config <config> --strict --apply
```

The `--apply` flag writes a `gate-10.md` report to the system directory.

**Do not run `commit-ready` until gate-10 passes.** If the gate reports
blockers, fix or redo the flagged refinements before committing.

To re-gate a specific batch, use:

```bash
python3 scripts/kb_manager.py gate-10 --config <config> --batch <batch-name>
```


Commit all validated staged results:

```bash
python3 scripts/kb_pipeline.py --config <config> commit-ready --limit 100
```

If model work fails, record it instead of abandoning the lease:

```bash
python3 scripts/kb_pipeline.py --config <config> fail \
  --job-id <id> --lease-token <token> --error <message>
```

Inspect and retry:

```bash
python3 scripts/kb_pipeline.py --config <config> status
python3 scripts/kb_pipeline.py --config <config> retry --limit 10
```

Preview expired committed-job artifacts before deleting anything:

```bash
python3 scripts/kb_pipeline.py --config <config> cleanup --retention-days 30
```

After reviewing the candidate list, apply the same verified cleanup:

```bash
python3 scripts/kb_pipeline.py --config <config> cleanup --retention-days 30 --apply
```

Cleanup only considers `committed` jobs whose original source and final refinement both still exist. It never removes artifacts for unfinished or failed jobs, and dry-run is the default.

Inspect and migrate legacy synced runtime data:

```bash
python3 scripts/kb_pipeline.py --config <config> storage-status
python3 scripts/kb_pipeline.py --config <config> migrate-runtime
python3 scripts/kb_pipeline.py --config <config> migrate-runtime --apply
python3 scripts/kb_pipeline.py --config <config> retire-legacy-runtime
python3 scripts/kb_pipeline.py --config <config> retire-legacy-runtime --apply
```

Migration refuses to run while a job is `refining`, copies the database through SQLite's backup API, rewrites managed artifact paths, verifies database integrity and record counts, and only then switches the configuration. Retirement moves the legacy runtime into a device-local recovery directory instead of deleting it.

Expired `refining` leases automatically return to `extracted` when status or claim runs. A refinement failure retries from `extracted`; an extraction failure retries from `discovered`.

For Chinese knowledge bases, preserve the original source title and use the established Chinese headings: `一句话价值`, `文章解决的问题`, `核心观点`, `可复用模型`, `存疑点 / 使用边界`, `可连接主题`, and `候选提升`. Internal job IDs must stay in metadata and must not appear in user-facing filenames. If the canonical destination already exists, do not overwrite it; reconcile or adopt the existing refinement.

## Operational Rules

- Keep batches small enough to finish within the lease.
- Use a stable worker name per active task.
- Never write `processed-index.jsonl` manually while the pipeline is active.
- Treat `commit` and `commit-ready` as the only completion boundary.
- Re-run `prepare`; discovery and extraction are idempotent for unchanged files.
- During discovery, reconcile legacy index records by resolved source path first and unique content hash second. If a legacy record has an empty output path, adopt the canonical destination only when that refinement file already exists; never deduplicate by title alone.
- Do not delete `<system>/runtime` while work is in progress.
- Use `cleanup` instead of manually deleting artifact directories. Keep a nonzero retention period for live knowledge bases.
- Back up the knowledge base, including the SQLite database, before migrations.
- Run `storage-status` after migration and again after retiring legacy runtime.

## Promotion Work Is a Separate Control Layer

Do not use the source-processing ledger as the only state for topic pages, reusable assets, or outputs. After sources are committed, promotion and output generation should use the mapped system files:

- `active-run-state.json` for the latest resumable stage;
- `run-log.jsonl` for append-only stage history;
- `asset-output-candidates.md` for human-readable approval decisions.

If the user terminates or pauses after source processing but before promotion, mark the run as `waiting_for_approval` or `paused_by_user` and record the next safe action. The next task should inspect this state and continue instead of recomputing the same candidate set.

## Refinement Metadata

```json
{
  "title": "Source title",
  "topics": ["topic one", "topic two"],
  "fact_risk": "low",
  "fact_check_required": false
}
```

Valid risk values are `low`, `medium`, `high`, and `unknown`.
