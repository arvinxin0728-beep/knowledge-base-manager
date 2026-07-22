---
name: knowledge-base-manager
description: Manage a mapped personal or portable knowledge-base system built from source libraries, AI-refined notes, topic pages, reusable assets, and outputs. Use when Codex needs to initialize or audit a knowledge base, map a user's folders to a general knowledge workflow, process unread ebooks/articles/public-account posts, manage WeChat/public-account Markdown libraries, read and refine books/articles/webpages, maintain processed indexes and topic candidates, decide whether to create topic pages, extract asset types such as methods/cases/expressions/frameworks, or generate Feynman explanations, article drafts, solution materials, reviews, and other reusable outputs. This is a single-install skill with embedded reading/refinement and public-account library modules.
---

# Knowledge Base Manager

## Purpose

Operate a knowledge-base system as an integrated workflow, not as isolated summaries. Convert mapped source libraries into structured, reusable knowledge through four layers:

1. Source refinement
2. Topic synthesis
3. Reusable assets
4. Concrete outputs

Keep universal methodology separate from the user's implementation mapping.

Use an asset and output generation matrix so source refinements do not accumulate as inert summaries. Distinguish method, case, expression, framework, Feynman explanation, article draft, solution material, decision memo, and review outputs by trigger and quality standard.

For multi-stage work, use explicit cost tiers, approval gates, and resumable checkpoints. The system should be able to pause at a human decision point and resume from the last recorded stage instead of starting over.

## First Decision

Classify the user request before acting:

| Request type | Primary action |
|---|---|
| "Set this up", "from scratch", "create my system" | Read `references/setup-and-config.md`, create mapping/config and base directories. |
| "Process unread/new sources" | Read `references/pipeline.md`; prepare and claim a bounded batch, generate refinements, submit, and commit them. |
| "Can I output now?", "make a complete loop" | Read `references/promotion-control-and-resume.md`; select a supported topic, confirm the approved scope if high-cost generation is needed, then create topic page plus at least one output artifact. |
| "Create a theme/page/article/Feynman explanation" | Use existing source refinements first; only read raw sources if needed. |
| "This structure is confusing" | Separate universal method from personal directory mapping and revise files. |
| "Use my WeChat/公众号 library" | Use the embedded official-account library module for deterministic library hygiene, then process articles. |
| "Read a book/article/source" | Use the embedded reading and refinement module for active reading and durable notes. |

If the user's mapped directories are unknown, ask for or infer:

- source library paths
- AI knowledge-base output path
- source types present
- whether to create directories if missing

For a new user with no mapping, create a portable default after confirmation. See `references/setup-and-config.md`.

## Embedded Capability Modules

This skill is designed to work as a single installed package. A normal installation contains every module needed for setup, source-library hygiene, reading, refinement, synthesis, indexing, and output.

The package should remain usable beyond Codex. Codex reads `SKILL.md` as the native entrypoint; other agent platforms may use this package as an instruction bundle plus deterministic local scripts. Keep platform-specific behavior isolated in adapters or installation notes, not in the universal workflow model.

- Use `references/reading-and-refinement.md` whenever reading, refining, synthesizing, or outputting from books, ebooks, public-account articles, webpages, newsletters, Markdown, PDF, EPUB, DOCX, HTML, TXT, or copied article text.
- Use `references/asset-output-matrix.md` whenever deciding whether a source, topic page, batch, or active project should produce reusable assets such as methods, cases, expressions, framework maps, or outputs such as Feynman explanations, article drafts, solution materials, decision memos, and review records.
- Use `references/promotion-control-and-resume.md` whenever a request may cross stages, consume high token cost, require human approval, or need to resume after a pause or termination.
- Use `scripts/ebook_probe.py` for deterministic text extraction from supported local files.
- Use `references/official-account-library.md` when a mapped source library is a WeChat/公众号 Markdown library that needs auditing, importing, flattening, deduping, or filename normalization.
- Use `scripts/official_account_library.rb` for deterministic 公众号 library operations.

## Default Directory Model

Use universal names in method explanations:

```text
knowledge-base/
├── 00-system/
├── 10-source-refinements/
├── 20-topic-pages/
│   ├── pages/
│   └── moc/
├── 30-reusable-assets/
└── 40-outputs/
```

Map these to the user's implementation. For an 8XX-style numeric folder system, use `examples/profiles/8xx/profile.md` only when the user explicitly selects or already has that profile.

When writing public-facing outputs, use universal names. When writing implementation plans or operating the user's local system, use mapped paths.

## Output Portability Boundary

Treat output artifacts as reusable knowledge products by default, not as private operation logs.

- Public-facing outputs, solution materials, Feynman explanations, article drafts, decision memos, and reusable templates must be understandable without knowing a specific user's folder names, local paths, or prior conversation.
- Use universal layer names in portable outputs: source library, source refinement, topic page, reusable asset, output, system files, MOC/index.
- Do not present a user's folder structure, such as an 8XX mapping, as the methodology itself.
- Do not write local layer codes such as `10-source-refinements`, `20-topic-pages`, `30-reusable-assets`, `40-outputs`, or their mapped names as the method body of a portable topic page, asset, or output. Use semantic layer names instead.
- Do not hard-code one user's batch size, source type, tool stack, local folder names, or private operating rhythm into a portable artifact. Put such details in a clearly marked implementation example or local operating note.
- Personal folder names, absolute paths, batch records, and implementation details may appear only when the artifact is explicitly labeled as a personal implementation plan, local operating note, migration note, or appendix/example.
- If an output would be confusing without the user's private context, rewrite it as universal methodology first and move the personal mapping into a clearly marked example section.
- File titles for reusable outputs should be portable. Avoid titles that depend on a private folder code or user-specific case unless the file is intentionally a case record.

## Core Workflow

### 1. Inspect and map

1. Locate the config file if present:
   - preferred: `<ai_knowledge_base>/00-系统/kb-config.json`
   - fallback: infer from nearby `800/801/888` or user-provided paths.
2. Read existing system files:
   - `processed-index.jsonl`
   - `topics.md`
   - `rules.md`
   - `inbox-review.md`
3. Check directory existence and source-library health.
4. For 公众号 libraries, run the official-account manager audit before processing when available.
5. For multi-stage or previously interrupted work, inspect `<ai_knowledge_base>/00-系统/active-run-state.json` or its mapped equivalent before starting a new run.

Use `scripts/kb_manager.py audit --config <config>` or `scripts/kb_manager.py init --config <config> --apply` for deterministic setup and counts. For 公众号 library hygiene, read `references/official-account-library.md` and run `scripts/official_account_library.rb`.

### 2. Process unread sources

For more than a few sources or any work that may span tasks, use the recoverable pipeline in `references/pipeline.md`. Do not manually append the processed index while the pipeline is active.

1. Determine candidate source files from mapped libraries.
2. Skip sources already present in `processed-index.jsonl`, using path and content hash when possible.
3. Process in small batches unless the user specifies otherwise.
4. For each source:
   - read using `references/reading-and-refinement.md`
   - write one source-refinement note
   - preserve source metadata and path
   - mark source type
   - extract topics and candidate reusable assets using `references/asset-output-matrix.md`
   - record limitations and fact-check needs
5. Append one JSON object per source to `processed-index.jsonl`.
6. Update `topics.md` and `inbox-review.md`.

Default source-refinement shape:

```markdown
# Source title

---
source_type:
source_file:
processed_at:
stage: 来源精炼
status: processed
---

## One-line value
## Problem addressed
## Core claims
## Reusable models or cases
## Limits / fact-check needs
## Connected topics
## Promotion candidate
```

Use the user's language unless they ask otherwise.

### 3. Run promotion review

After every batch of source processing, run a promotion review. Do not leave the system at source refinement only when topic clusters qualify for promotion. The review must update or create:

- `topic-clusters.md`: semantic topic clusters, not just raw tags
- `promotion-review.md`: cluster scores, actions, and reasons for not promoting
- `asset-output-candidates.md`: candidate assets and outputs that need approval before high-cost generation

Run `scripts/kb_manager.py promote --config <config> --apply` for deterministic topic clustering and promotion review. Add `--create-stubs` only when the user wants deterministic draft files created under the system stub area. Stubs must not enter formal topic pages, reusable assets, or outputs until they are synthesized and pass quality gates. Source count is a hard evidence gate: a cluster below `min_sources_for_topic` remains a candidate unless it is explicitly marked `user_requested` or `active_project`.

Cluster raw tags into meaningful questions before scoring. For example, `Obsidian`, `AI knowledge management`, `personal knowledge base`, `LLM Wiki`, and `Graphify` may belong to one broader cluster if they support the same knowledge-work problem.

Before deciding what to create, read `references/asset-output-matrix.md` and classify the cluster by artifact opportunity. Do not default every promoted cluster to a method asset or solution material. Generate only the artifact types whose triggers are present; record missing triggers when no artifact is created.

Do not treat repeated source count as proof of a reusable asset. A generated placeholder question does not count as question clarity. A 30-layer asset must have a parent topic page, a specific asset type, a non-duplication reason, and a lifecycle status. If these are missing, keep the item in `asset-output-candidates.md`.

If a topic page already owns more than 5 reusable assets or more than 5 outputs, run a structure review before generating more for that topic.

Read `references/promotion-control-and-resume.md` before moving from review into generation. Low-cost scans and medium-cost candidate reviews may proceed when requested. High-cost generation of 20/30/40 artifacts requires explicit approval unless the user directly requested the exact artifact or cluster.

Use a 5-point promotion score:

1. Source count: 3 or more relevant sources
2. Question clarity: the cluster can be expressed as a concrete problem/question
3. Reusability: it contains reusable methods, cases, expressions, or frameworks
4. Output intent: it can support an explanation, article, solution material, decision memo, or active project
5. Fact-risk control: claims are low-risk, or risk is explicitly marked for verification

Promotion actions:

- 0-1: keep as topic candidate only
- 2-3: create or update a topic page
- 4: create or update a topic page and at least one reusable asset
- 5: create or update a topic page, at least one reusable asset, and at least one output artifact

If a cluster is not promoted, record the reason: insufficient sources, unclear question, weak reuse value, no output scenario, or high fact risk.

Topic pages must answer:

- What question is this page about?
- What do current sources support?
- What is my current judgment?
- What is uncertain or needs verification?
- What can be output now?
- Which assets should be extracted next?
- Which asset/output types are triggered by the matrix, and which are intentionally deferred?

Read `references/output-rules.md` for topic/output boundaries.

### 4. Produce outputs

Use topic pages as the source of truth before generating outputs. Valid output types include:

- Feynman explanations
- article drafts
- solution or consulting materials
- reusable checklists
- decision memos
- review notes

Before writing a `30-reusable-assets` or `40-outputs` file, classify the intended artifact with `references/asset-output-matrix.md`. If the trigger is absent, do not create the file merely to fill a folder. If the trigger exists but evidence is weak, create a draft with explicit source boundary and fact-check needs.

For high-cost generation, write or update the active run checkpoint before and after generation. If the user pauses or declines the next stage, record `paused_by_user` or `waiting_for_approval` so the next run can continue from the same candidate set.

For Feynman outputs, explain in plain language, use simple analogies only when accurate, avoid folder-specific implementation details unless the output is explicitly for the user.

For public-facing outputs, separate:

- universal principles
- user's implementation example
- unverified claims

For solution materials and other `40-outputs` artifacts, default to portable methodology. A user's current folder structure is evidence of one implementation, not the method itself. If the output is meant to be reused by other users, keep personal mappings out of the main body and use a short "Implementation example" or "Local mapping" section only when needed.

### 5. Maintain Obsidian links

When the mapped knowledge base is used in Obsidian, every new or updated source refinement, topic page, reusable asset, and output must include Obsidian-ready frontmatter, stable tags, wikilinks, and a `## 关联知识` section. Run:

```bash
python3 scripts/obsidian_linker.py --config <config> --apply
```

Use few stable tags and meaningful wikilinks. Do not turn every noun into a tag or link. Read `references/obsidian-linking.md` for the rules.

## Deterministic Commands

- `init`: create the configured tree and starter system files.
- `validate-config`: validate schema version, required fields, absolute source paths, and knowledge-base path boundaries.
- `doctor`: validate configuration and inspect source-library and destination health.
- `audit`: count source files, processed records, and unprocessed files.
- `normalize-index`: convert older index fields to the canonical schema in `references/schema.md`.
- `promote`: generate `topic-clusters.md` and `promotion-review.md` from index records plus portable or explicitly configured cluster rules.
- `audit-assets`: inspect 30-layer assets for parent-topic linkage, type balance, lifecycle status, and overloaded topic clusters.
- `audit-relations`: inspect 20/30/40 relationship integrity and unresolved wikilinks.
- `audit-portability`: inspect 20/30/40 artifact bodies for user-specific implementation leakage that should not appear in portable methods or outputs.
- `audit-topic-pages`: inspect topic pages for required knowledge-page sections and placeholder/process-only structure-review text.
- `quality-gate`: combine relation, portability, topic-page, asset, output-quality, and verification checks into one pass/fail result; use `--strict` to fail on blockers.
- `package-lint`: inspect the skill package itself for release-blocking portability and packaging issues.
- `verification-queue`: scan processed notes, topic pages, and outputs for high-risk claims and write a verification queue.
- `verify-claim`: append a verification result for a queued claim or file into the verification result ledger.
- `verification-status`: merge the current queue with the result ledger and report pending, verified, rejected, and unresolved output items.
- `evaluate-outputs`: mechanically score output files and write `output-quality-review.md`.
- `output-review`: create a rubric review surface for output artifacts.
- `record-output-review`: append a human or model review result for an output artifact; `needs_revision` and `rejected` become quality-gate blockers.
- `run`: execute all safe deterministic maintenance stages and report the next cognitive action; use `--apply` to write reports.
- `kb_pipeline.py`: maintain the SQLite task ledger and run recoverable processing, storage inspection, legacy-to-local runtime migration, recoverable legacy retirement, and safe artifact cleanup. Keep runtime data device-local for new installations; preserve legacy behavior until an explicit verified migration. Cleanup and migration default to dry-run.
- `obsidian_linker.py`: add Obsidian frontmatter, stable tags, wikilinks, relation sections, and MOC pages for source refinements, topic pages, reusable assets, and outputs.

Read `references/schema.md`, `references/verification.md`, `references/output-evaluation.md`, and `references/obsidian-linking.md` when using these commands.

## Quality Controls

Before finalizing work:

1. Verify files were written to the intended mapped knowledge base, not only to a temporary output folder.
2. Count index lines and generated notes.
3. Distinguish facts, author claims, AI inference, and user-specific implementation.
4. Mark high-risk facts for verification.
5. Avoid long quotes from copyrighted books or articles.
6. Do not mutate source libraries destructively without dry-run, report, and user approval.
7. Do not treat directory names as methodology; directory names are implementation mapping.
8. Check reusable outputs for portability: the main body must be readable by someone who has never seen the user's local knowledge base.
9. For stage changes, confirm whether approval is required by `references/promotion-control-and-resume.md`.
10. When work stops before completion, record the latest stage, completed steps, pending steps, and next safe action in the mapped system directory.
11. Run `audit-portability` after creating or revising 20/30/40 artifacts. Treat any issue in portable artifact bodies as a defect, not a style preference.
12. Run `audit-topic-pages` after creating, splitting, renaming, or restructuring topic pages. A topic page that only explains a split, migration, or file organization change is not a valid topic page.
13. Run `quality-gate --strict` before declaring a 20/30/40 generation or restructuring task complete. Blockers must be fixed or explicitly left as unfinished work.
14. Run `package-lint --strict` before presenting the skill as installable by other users.
15. For high-risk output claims, run `verification-queue`, record results with `verify-claim`, then refresh `verification-status`; unresolved output verification is a completion blocker.
16. For reusable/public outputs, run `output-review` and record a rubric result with `record-output-review`; do not publish or present outputs marked `needs_revision` or `rejected`.
17. Keep `README.md` synchronized with skill behavior. Any change to positioning, setup, directory model, commands, workflow stages, quality gates, or portability boundaries must update the Chinese README before release. `package-lint --strict` must fail when the README is missing, incomplete, or older than core skill sources.
18. Public beta releases must include `LICENSE`, `CHANGELOG.md`, `SECURITY.md`, and `INSTALL.zh-CN.md`. Do not present the package as GitHub-ready if any release governance file is missing.

## Configuration

Use `references/setup-and-config.md` for the config schema and default portable layout.

## Bundled Resources

- `references/promotion-control-and-resume.md`: cost tiers, human approval gates, checkpoint schema, and resume protocol.

Minimum config:

```json
{
  "name": "my-knowledge-base",
  "source_libraries": {
    "ebooks": "/absolute/path/to/ebooks",
    "public_accounts": "/absolute/path/to/public-account-library"
  },
  "ai_knowledge_base": "/absolute/path/to/ai-knowledge-base",
  "mapping": {
    "system": "00-系统",
    "source_refinements": "10-来源精炼",
    "topic_pages": "20-主题页",
    "reusable_assets": "30-可复用资产",
    "outputs": "40-输出"
  },
  "topic_page_subdirs": {
    "pages": "主题页",
    "moc": "MOC"
  }
}
```

For an 8XX setup, prefer the example in `examples/profiles/8xx/profile.md`. Personal cluster rules and Obsidian taxonomies must remain explicit profile configuration; portable initialization must not install personal starter topics.

## Bundled Resources

- `scripts/kb_manager.py`: initialize directories, audit config, normalize indexes, promote topic clusters, create deterministic system-area stubs, build verification queues, record verification/output-review ledgers, and evaluate output files.
- `scripts/obsidian_linker.py`: normalize Obsidian metadata, tags, wikilinks, relation sections, and MOC pages for 10/20/30/40 files.
- `scripts/ebook_probe.py`: extract text, metadata, chunks, and manifests from supported local books/articles.
- `scripts/kb_pipeline.py`: run the recoverable, lease-based source-processing pipeline for large libraries.
- `scripts/official_account_library.rb`: audit, import, dedupe, and prune WeChat/公众号 Markdown libraries.
- `references/setup-and-config.md`: portable setup and mapping rules.
- `README.md`: Chinese user-facing introduction, installation guide, usage guide, quality boundary, and README maintenance policy.
- `INSTALL.zh-CN.md`: Chinese install and verification guide for Codex, other agent platforms, and script-only use.
- `LICENSE`, `CHANGELOG.md`, `SECURITY.md`: public distribution license, version history, and security/privacy boundary.
- `references/output-rules.md`: source refinement, topic-page, asset, and output boundaries.
- `references/asset-output-matrix.md`: trigger matrix and quality standards for methods, cases, expressions, framework maps, Feynman explanations, article drafts, solution materials, decision memos, and review records.
- `references/schema.md`: canonical processed-index schema and normalization rules.
- `references/portable-cluster-rules.json`: empty portable starter rules that discover repeated exact topics without imposing a personal taxonomy.
- `examples/profiles/8xx/profile.md`: optional 8XX-style implementation example; load only when selected.
- `examples/profiles/8xx/cluster-rules.json`: optional 8XX example cluster rules; copy into the user's system directory only when selected.
- `examples/profiles/8xx/obsidian-taxonomy.json`: optional 8XX Obsidian taxonomy; never enable it for portable users automatically.
- `references/verification.md`: high-risk fact verification workflow.
- `references/output-evaluation.md`: output-quality evaluation checks.
- `references/obsidian-linking.md`: Obsidian frontmatter, tag, wikilink, and MOC rules.
- `references/reading-and-refinement.md`: embedded reading and source-refinement protocol.
- `references/pipeline.md`: state model, batch protocol, leases, retries, and commit boundary.
- `references/official-account-library.md`: embedded 公众号 library management protocol.
