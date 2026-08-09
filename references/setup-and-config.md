# Setup and Configuration

Use this reference when a user asks to initialize a knowledge base or researcher, make the workflow portable, or adapt the skill to a new directory system.

## Universal Model

The skill uses universal roles, then maps them to concrete folders.

| Universal role | Meaning |
|---|---|
| researcher | Independent research unit with its own sources, process state, knowledge base, outputs, and quality gates. |
| source libraries | Raw or lightly curated materials such as ebooks, articles, webpages, newsletters, public-account exports, transcripts, or PDFs. |
| AI knowledge base | A single researcher's processed knowledge area, not raw-source storage. |
| system | Indexes, rules, configs, topic candidates, batch reports. |
| source refinements | One processed note per source. |
| topic pages | Cross-source synthesis around a question. |
| MOC indexes | Obsidian navigation hubs that collect topic pages, reusable assets, and outputs by theme. |
| reusable assets | Methods, cases, expressions, frameworks, checklists. |
| outputs | Feynman explanations, article drafts, solution materials, reviews. |

## Portable Default Layout

For a new user without an existing structure and only one researcher:

```text
Knowledge-System/
├── Sources/
│   ├── Ebooks/
│   ├── Articles/
│   └── Public-Accounts/
└── AI-Knowledge-Base/
    ├── 00-system/
    │   ├── kb-config.json                  # 配置文件（根目录，通过 --config 引用）
    │   ├── obsidian-taxonomy.json          # Obsidian 分类映射（根目录）
    │   ├── active/                         # 当前工作状态
    │   │   ├── processed-index.jsonl
    │   │   ├── active-run-state.json
    │   │   ├── run-log.jsonl               # 操作日志，每次 --apply 追加一条
    │   │   ├── promotion-decision.jsonl
    │   │   ├── verification-queue.jsonl
    │   │   ├── verification-results.jsonl
    │   │   ├── output-review-results.jsonl
    │   │   ├── evidence-fill-ledger.jsonl
    │   │   ├── rules.md
    │   │   └── topics.md
    │   ├── reports/                        # 可重新生成的快照
    │   │   ├── topic-clusters.md
    │   │   ├── promotion-review.md
    │   │   ├── asset-output-candidates.md
    │   │   ├── quality-gate.md
    │   │   ├── gate-10.md
    │   │   ├── verification-status.md
    │   │   ├── output-quality-review.md
    │   │   ├── output-review-status.md
    │   │   ├── portability-audit.md
    │   │   ├── topic-page-audit.md
    │   │   ├── relation-audit.md
    │   │   ├── asset-relation-audit.md
    │   │   ├── evidence-gap-registry.md
    │   │   ├── evidence-intake-audit.md
    │   │   ├── source-capabilities.md
    │   │   └── inbox-review.md
    │   ├── evidence-intake/                # 系统主动补证候选区，未通过抽取质检前不得进入10
    │   │   ├── candidates/
    │   │   ├── extracted/
    │   │   ├── needs-ocr/
    │   │   ├── needs-manual-review/
    │   │   └── rejected/
    │   ├── backups/                        # 自动备份（保留最近5份，超出轮转）
    │   │   └── ... (processed-index.jsonl.20260723, etc.)
    │   └── stubs/
    ├── 10-source-refinements/
    │   ├── ebooks/
    │   ├── articles/
    │   ├── public-accounts/
    │   └── system-evidence-fill/           # 系统主动补证来源，和人工保存来源分开
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

For multiple researchers on one computer, use a registry plus isolated researcher workspaces:

```text
Research-System/
├── shared-methods/
│   ├── rubrics/
│   ├── templates/
│   └── playbooks/
├── researchers/
│   ├── researcher-a/
│   │   ├── Sources/
│   │   └── AI-Knowledge-Base/
│   └── researcher-b/
│       ├── Sources/
│       └── AI-Knowledge-Base/
└── registry/
    └── researchers.json
```

Each researcher has its own `AI-Knowledge-Base/00-system/kb-config.json`. Do not share `00-system/active` files across researchers.

## Config Schema

Store config at `<ai_knowledge_base>/<system>/kb-config.json`.

```json
{
  "name": "my-researcher",
  "version": 1,
  "language": "zh-CN",
  "researcher": {
    "id": "my-researcher",
    "name": "My Researcher",
    "domain": "research domain or project scope",
    "role": "researcher",
    "isolation": "independent_workspace",
    "shared_methods": []
  },
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
    "runtime_namespace": "my-researcher",
    "artifact_retention_days": 7
  }
}
```

`runtime_storage: local` keeps SQLite, extracted text, chunks, and drafts outside the synced knowledge base. `runtime_namespace` should match the researcher ID for new configs. Existing configs without it preserve their historical name-based local runtime path; do not add or change it without an explicit runtime migration. The location is derived per device and per knowledge base; do not put a personal absolute runtime path in a portable profile. Existing configurations without `runtime_storage` remain on legacy `<system>/runtime` storage until explicitly migrated.

For automated tests or restricted runtime environments, set `KBM_RUNTIME_ROOT` to a writable local directory before running the pipeline. This keeps device-local runtime state out of synced knowledge-base folders and avoids assuming access to a specific home-directory application state path.

## Initialization Steps

1. Ask for source-library paths and AI knowledge-base path, unless they are already known.
2. Create the configured directory tree.
3. Create empty system files if missing.
4. Write `rules.md` with operating boundaries.
5. Write `kb-config.json`.
6. Run `validate-config`, `doctor`, and an audit; report counts and config health.

Never invent source paths. If the user has no existing source libraries, create empty source folders and explain where to put materials.

For a multi-researcher setup, first select or create the researcher registry, then initialize one researcher at a time. Register the researcher's config path after validation. Do not create a global processed index or shared active run state.

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
