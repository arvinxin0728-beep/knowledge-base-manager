# Model Transactions and Citation-First Retrieval

Use this reference when model reading must be recoverable or when durable knowledge must be searched with citations.

## Model-run contract

The source job and the model run are separate ledgers. A source job owns discovery, extraction, lease, refinement, and commit state. A model run records one concrete attempt made under that lease:

```text
running → completed → validated → committed
   └──────────────→ failed
```

Record the provider, model, prompt version/hash, extracted-input hash, output snapshot/hash, metadata snapshot, token counts, duration, timestamps, and a bounded failure code. Snapshots live in device-local runtime storage, not in the synchronized knowledge base.

Start after claiming a job:

```bash
python3 scripts/kb_model.py --config <config> start \
  --job-id <job> --lease-token <token> \
  --provider <provider> --model <model> --prompt-version <version>
```

After the model produces one refinement and its metadata:

```bash
python3 scripts/kb_model.py --config <config> complete \
  --run-id <run> --output <refinement.md> --metadata <metadata.json> \
  --input-tokens <n> --output-tokens <n> --duration-ms <n>

python3 scripts/kb_pipeline.py --config <config> submit \
  --job-id <job> --lease-token <token> --model-run-id <run>
```

`complete` copies both files into a durable runtime snapshot. `submit` validates that snapshot and Gate-10 before marking it `validated`; the normal pipeline commit marks it `committed`. Use `kb_model.py fail` for an interrupted attempt and the existing pipeline `fail`/`retry` flow for the source job. Legacy direct submit remains supported.

## Retrieval contract

`lexical-v1` indexes only durable Markdown artifacts from the four semantic layers. The database is device-local and regenerable. Preview before writing:

```bash
python3 scripts/kb_search.py --config <config> rebuild
python3 scripts/kb_search.py --config <config> rebuild --apply
python3 scripts/kb_search.py --config <config> query --query <question> --limit 10
```

Each result returns `engine`, rank/score, stable artifact and chunk IDs, semantic layer, title/heading, snippet, absolute and knowledge-base-relative paths, and start/end lines. Downstream answers must cite these fields and must not claim that a search result proves a fact.

The first engine uses deterministic exact-phrase and term-frequency/IDF scoring. Its result contract is intentionally engine-neutral so a future hybrid/vector/graph engine can be added without changing callers. Rebuild after durable artifacts change; incremental indexing and generated answers are not part of this version.
