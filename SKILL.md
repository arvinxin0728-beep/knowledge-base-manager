---
name: knowledge-base-manager
description: Initialize and operate one or many isolated research agents with configurable scope, sources, process, outputs, capabilities, governance, recoverable processing, and quality gates. Use when Codex needs to create, audit, migrate, or evolve a portable research knowledge system; design a researcher; process books, articles, public-account posts, webpages, transcripts, or videos; refine sources; synthesize topics; create reusable assets or outputs; or diagnose configuration, lifecycle, evidence, privacy, and release readiness.
---

# Knowledge Base Manager

## Operating model

Treat a researcher as an isolated, configured research unit with its own sources, runtime state, knowledge base, quality records, and outputs. Share the skill package and portable research methods; never silently share raw sources, enterprise knowledge, conclusions, credentials, caches, or active state between researchers.

Use four semantic knowledge layers:

1. source refinements;
2. topic synthesis;
3. reusable assets;
4. concrete outputs.

Keep universal methodology separate from user-specific mappings. Treat a personal directory layout as one implementation profile, not as the method.

Resolve each researcher from:

```text
shared core
+ research scope, sources, process, and outputs
+ optional starter preset
+ capability contracts
+ governance policy
+ instance-local mapping and adapters
```

Preview high-cost or multi-stage work, record checkpoints, and resume instead of restarting.

## Route the request

| Request | Read first | Primary action |
|---|---|---|
| Initialize, select, or coordinate researchers | `references/researcher-system.md`, `references/setup-and-config.md` | Compose a research design, preview its plan, then create or map one isolated workspace. |
| Add a preset, capability, dependency, or adapter | `references/capability-contracts.md` | Keep dimensions independent; define an executable contract and validate readiness. |
| Add MCP, DingTalk, Feishu, or enterprise integration | `references/privacy-and-enterprise-connectors.md` | Keep contracts portable and all values/data instance-local. |
| Process unread or new sources | `references/pipeline.md`, `references/reading-and-refinement.md` | Discover, prepare, extract, claim, refine, submit, and commit a bounded batch. |
| Read or refine one book/article/source | `references/reading-and-refinement.md` | Perform active reading and create one traceable durable refinement. |
| Handle PDF/OCR/unsupported or uncertain extraction | `references/source-intake-and-extraction.md` | Validate readability before refinement. |
| Audit source credibility or freshness | `references/source-quality-and-weighting.md` | Weight evidence and record limitations. |
| Promote topics or create assets/outputs | `references/asset-output-matrix.md`, `references/promotion-control-and-resume.md` | Review triggers/evidence, obtain approval when required, then generate. |
| Fill an evidence gap | `references/evidence-gap-and-bounded-fill.md` | Run bounded evidence intake; avoid open-ended research. |
| Create or improve an article | `references/editorial-quality-and-output-maturity.md`, `references/publishable-article-workflow.md` | Upgrade argument, evidence, reader value, and maturity. |
| Hand off a publication candidate | `references/publication-candidate-handoff.md` | Verify readiness and produce a channel-neutral handoff. |
| Audit stale knowledge, rollback, or health | `references/lifecycle-and-health.md`, `references/verified-closed-loops.md` | Audit first; do not demote or delete from warnings alone. |
| Maintain Obsidian links | `references/obsidian-linking.md` | Normalize metadata, links, relations, and MOCs. |
| Manage a public-account Markdown library | `references/official-account-library.md` | Audit before importing, flattening, deduping, or pruning. |

If required mappings are unknown, infer safely from an existing config or ask for source paths, output path, source types, and permission to create missing directories.

## Portable workspace

```text
researcher-workspace/
├── sources/
└── knowledge-base/
    ├── 00-system/
    ├── 10-source-refinements/
    ├── 20-topic-pages/
    │   ├── pages/
    │   └── moc/
    ├── 30-reusable-assets/
    └── 40-outputs/
```

For multiple researchers, use one shared skill installation and separate workspaces/configs. Use `examples/profiles/8xx/profile.md` only when the user explicitly selects or already uses that mapping.

Organize system files under:

- `active/` for current ledgers and run state;
- `reports/` for regenerable audits;
- `backups/` for bounded recoverable history.

Keep new runtime databases and extraction caches device-local. Migrate legacy runtime only through explicit dry-run, verification, and recoverable retirement.

## Researcher and capability rules

Model researcher identity, scope, sources, process, outputs, capabilities, and governance as independent dimensions. Presets provide editable defaults, never identity or mutually exclusive classes. Keep organization-specific taxonomies and knowledge outside the shared package.

Every capability must declare its dependency, execution mode, portable entrypoint, inputs, outputs, quality gates, configuration fields, availability, and configuration scope. Use:

- `builtin` for bundled deterministic code;
- `instruction` for a bundled model procedure;
- `adapter` for an instance-provided integration.

Mark missing adapters and blocked dependencies explicitly. Never report them as ready or silently skip them.

For enterprise adapters, return only status, reason, and missing field names. Never echo MCP values, credentials, tenant/node identifiers, private paths, or enterprise content. Read only the selected researcher's instance namespace.

## Core workflow

### 1. Inspect and select

1. Locate and validate the intended researcher's config.
2. Confirm its identity, workspace, runtime namespace, sources, and destination.
3. Inspect active run state before starting another multi-stage run.
4. Run source-library hygiene when the source type requires it.

### 2. Process sources transactionally

1. Discover candidates and skip committed sources by path/hash.
2. Prepare and extract into device-local runtime storage.
3. Claim a bounded batch.
4. Read with `references/reading-and-refinement.md`.
5. Submit only refinements that pass the single-file and batch quality gates.
6. Commit index/state changes transactionally.
7. Retry or resume failed/interrupted items from recorded state.

Do not manually append the processed index while the transactional pipeline is active.

### 3. Review promotion

After a committed batch, update semantic topic clusters, promotion review, and asset/output candidates. Source count is evidence, not proof of synthesis quality. Require a clear question, reusable value, output intent, and controlled fact risk.

Do not create formal topic pages, assets, or outputs from deterministic stubs. Read `references/asset-output-matrix.md`; generate only artifact types whose triggers exist. Obtain explicit approval for high-cost generation unless the user requested that exact artifact.

### 4. Generate durable knowledge

Use source refinements as evidence and topic pages as synthesis truth. Distinguish facts, source claims, inference, and unresolved verification. Preserve attribution and evidence links.

Default reusable/public outputs to portable language. Put personal mappings in a labeled implementation example only when needed.

### 5. Verify and maintain

Run relation, portability, filename/freshness, lifecycle, health, editorial, and verification checks appropriate to the changed artifacts. Update knowledge freshness only for semantic changes; record pure link maintenance separately.

## Non-negotiable quality gates

- Never use copied raw text or placeholders as a refinement.
- Never fabricate a source, citation, date, claim, product capability, or processing result.
- Verify extraction readability before model refinement.
- Preserve the canonical source-refinement schema and source attribution.
- Require evidence fields and artifact-specific thresholds for topic pages, assets, and outputs.
- Mark high-risk claims for verification; unresolved high-risk output claims block completion.
- Run editorial/output review before presenting an artifact as publishable.
- Use dry-run and explicit approval before destructive source-library, runtime, lifecycle, or migration actions.
- Keep 20/30/40 artifacts portable unless explicitly labeled as a local implementation record.
- Keep enterprise configurations, credentials, knowledge, and fixtures out of the shared package.
- Record checkpoints when stopping before a multi-stage task is complete.

Before writing a 10/20/30/40 artifact, inspect a known-good artifact of the same type and match its schema, section names, tags, and link style. After changing one defect category, scan the whole in-scope knowledge base for the same category.

## Deterministic interfaces

Use `scripts/kb_manager.py` for setup, audits, promotion, quality, verification, lifecycle, portability, and release checks. Important commands include:

```text
init  validate-config  doctor  audit  normalize-index  run
promote  audit-assets  audit-relations  audit-portability
audit-topic-pages  audit-filename-dates  normalize-filename-dates
gate-10  check-refinement  sync-relations  quality-gate
audit-source-quality  audit-evidence-gaps  init-evidence-intake
audit-evidence-intake  verification-queue  verify-claim
verification-status  evaluate-outputs  output-review
record-output-review  audit-lifecycle  audit-knowledge-health
init-lifecycle-health  package-lint
```

Use `scripts/kb_pipeline.py` for recoverable source processing:

```text
init  discover  prepare  extract  claim  submit  commit
commit-ready  fail  retry  adopt-existing  status
storage-status  migrate-runtime  retire-legacy-runtime  cleanup
```

Use `scripts/kb_researcher.py` for researcher registry, selection, composable initialization, capability plans, and redacted readiness diagnostics:

```text
registry-init  register  list  select  show  doctor
presets  types(deprecated)  capabilities  plan-init  init
```

Use `scripts/obsidian_linker.py`, `scripts/ebook_probe.py`, and `scripts/official_account_library.rb` for their declared deterministic modules.

## Completion protocol

Before declaring work complete:

1. Confirm the intended researcher/workspace received all writes.
2. Confirm no other researcher's state, cache, config, or knowledge was read or mutated without explicit import.
3. Run the relevant artifact quality gates and report blockers honestly.
4. For Skill changes, run full tests, `architecture_check.py --strict`, Skill validation, and `package-lint --strict`.
5. Update README when positioning, setup, commands, workflow, quality, privacy, or release behavior changes.
6. Keep release governance files present and synchronized.
7. Record unfinished stages and the next safe action.

## Reference index

- Setup and system: `references/setup-and-config.md`, `references/researcher-system.md`, `references/schema.md`, `references/pipeline.md`
- Capability and privacy: `references/capability-contracts.md`, `references/privacy-and-enterprise-connectors.md`
- Reading and evidence: `references/reading-and-refinement.md`, `references/source-intake-and-extraction.md`, `references/source-quality-and-weighting.md`, `references/evidence-gap-and-bounded-fill.md`, `references/verification.md`
- Synthesis and outputs: `references/asset-output-matrix.md`, `references/output-rules.md`, `references/feynman-template.md`, `references/editorial-quality-and-output-maturity.md`, `references/publishable-article-workflow.md`, `references/publication-candidate-handoff.md`, `references/output-evaluation.md`
- Maintenance: `references/obsidian-linking.md`, `references/lifecycle-and-health.md`, `references/verified-closed-loops.md`, `references/promotion-control-and-resume.md`
- Source modules: `references/official-account-library.md`
