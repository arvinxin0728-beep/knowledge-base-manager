# Setup and Configuration

Use this reference when a user asks to initialize a knowledge base, make the workflow portable, or adapt the skill to a new directory system.

## Universal Model

The skill uses universal roles, then maps them to concrete folders.

| Universal role | Meaning |
|---|---|
| source libraries | Raw or lightly curated materials such as ebooks, articles, webpages, newsletters, public-account exports, transcripts, or PDFs. |
| AI knowledge base | Processed knowledge area, not raw-source storage. |
| system | Indexes, rules, configs, topic candidates, batch reports. |
| source refinements | One processed note per source. |
| topic pages | Cross-source synthesis around a question. |
| MOC indexes | Obsidian navigation hubs that collect topic pages, reusable assets, and outputs by theme. |
| reusable assets | Methods, cases, expressions, frameworks, checklists. |
| outputs | Feynman explanations, article drafts, solution materials, reviews. |

## Portable Default Layout

For a new user without an existing structure:

```text
Knowledge-System/
├── Sources/
│   ├── Ebooks/
│   ├── Articles/
│   └── Public-Accounts/
└── AI-Knowledge-Base/
    ├── 00-system/
    │   ├── kb-config.json
    │   ├── processed-index.jsonl
    │   ├── topics.md
    │   ├── topic-clusters.md
    │   ├── promotion-review.md
    │   ├── promotion-decision.jsonl
    │   ├── asset-output-candidates.md
    │   ├── verification-queue.jsonl
    │   ├── verification-results.jsonl
    │   ├── verification-status.md
    │   ├── output-quality-review.md
    │   ├── output-review-results.jsonl
    │   ├── output-review-status.md
    │   ├── portability-audit.md
    │   ├── topic-page-audit.md
    │   ├── asset-relation-audit.md
    │   ├── relation-audit.md
    │   ├── quality-gate.md
    │   ├── rules.md
    │   ├── inbox-review.md
    │   └── stubs/
    ├── 10-source-refinements/
    │   ├── ebooks/
    │   ├── articles/
    │   └── public-accounts/
    ├── 20-topic-pages/
    │   ├── pages/
    │   └── moc/
    ├── 30-reusable-assets/
    │   ├── methods/
    │   ├── cases/
    │   ├── expressions/
    │   └── frameworks/
    └── 40-outputs/
        ├── feynman-explanations/
        ├── article-drafts/
        ├── solution-materials/
        └── reviews/
```

## Config Schema

Store config at `<ai_knowledge_base>/<system>/kb-config.json`.

```json
{
  "name": "my-knowledge-base",
  "version": 1,
  "language": "zh-CN",
  "source_libraries": {
    "ebooks": "/absolute/path/to/ebooks",
    "articles": "/absolute/path/to/articles",
    "public_accounts": "/absolute/path/to/public-account-library"
  },
  "ai_knowledge_base": "/absolute/path/to/ai-knowledge-base",
  "mapping": {
    "system": "00-system",
    "source_refinements": "10-source-refinements",
    "topic_pages": "20-topic-pages",
    "reusable_assets": "30-reusable-assets",
    "outputs": "40-outputs"
  },
  "source_refinement_subdirs": {
    "ebooks": "ebooks",
    "articles": "articles",
    "public_accounts": "public-accounts"
  },
  "topic_page_subdirs": {
    "pages": "pages",
    "moc": "moc"
  },
  "reusable_asset_subdirs": {
    "methods": "methods",
    "cases": "cases",
    "expressions": "expressions",
    "frameworks": "frameworks"
  },
  "output_subdirs": {
    "feynman": "feynman-explanations",
    "article_drafts": "article-drafts",
    "solution_materials": "solution-materials",
    "reviews": "reviews"
  },
  "promotion_rules": {
    "min_sources_for_topic": 3,
    "allow_user_requested_topic": true,
    "fact_check_before_public_output": true,
    "cluster_rules": "00-system/cluster-rules.json"
  },
  "integrations": {
    "obsidian": {
      "enabled": false,
      "taxonomy": "00-system/obsidian-taxonomy.json"
    }
  },
  "pipeline": {
    "chunk_size": 5000,
    "default_batch_size": 10,
    "max_attempts": 3,
    "lease_minutes": 120,
    "runtime_storage": "local",
    "artifact_retention_days": 7
  }
}
```

`runtime_storage: local` keeps SQLite, extracted text, chunks, and drafts outside the synced knowledge base. The location is derived per device and per knowledge base; do not put a personal absolute runtime path in a portable profile. Existing configurations without this field remain on legacy `<system>/runtime` storage until explicitly migrated.

For automated tests or restricted runtime environments, set `KBM_RUNTIME_ROOT` to a writable local directory before running the pipeline. This keeps device-local runtime state out of synced knowledge-base folders and avoids assuming access to a specific home-directory application state path.

## Initialization Steps

1. Ask for source-library paths and AI knowledge-base path, unless they are already known.
2. Create the configured directory tree.
3. Create empty system files if missing.
4. Write `rules.md` with operating boundaries.
5. Write `kb-config.json`.
6. Run `validate-config`, `doctor`, and an audit; report counts and config health.

Never invent source paths. If the user has no existing source libraries, create empty source folders and explain where to put materials.

After writing config, run `validate-config` and `doctor` before processing. All values under `mapping` must be relative child paths inside `ai_knowledge_base`. A portable installation starts with no predefined topic clusters or Obsidian taxonomy.

Before sharing the skill package with another user, run:

```bash
python3 scripts/kb_manager.py package-lint --strict
```

Before declaring generated 20/30/40 artifacts complete, run:

```bash
python3 scripts/kb_manager.py quality-gate --config <kb-config> --apply --strict
```

## Rules File Starter

```markdown
# Knowledge Base Rules

## Purpose

This knowledge base stores understood, compressed, structured, and reusable knowledge. It is not a raw-source archive.

## Boundaries

- Raw sources stay in source libraries.
- Source refinements explain one source.
- Topic pages synthesize multiple sources around a question.
- Reusable assets extract methods, cases, expressions, and frameworks.
- Outputs serve explicit readers, tasks, and scenarios.

## Quality Controls

- Preserve source paths and metadata.
- Distinguish facts, author claims, AI inference, and personal judgment.
- Mark high-risk facts for verification before public or business-critical use.
- Do not create topic pages for every single source.
```
