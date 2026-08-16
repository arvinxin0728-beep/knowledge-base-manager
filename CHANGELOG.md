# Changelog

All notable changes to this project should be recorded here.

The format follows Keep a Changelog conventions loosely, and this project uses semantic versioning while it is distributed publicly.

## [Unreleased]

## [0.8.0] - 2026-08-16

### Added

- Transactional model-run ledger with prompt/model identity, input/output hashes, durable snapshots, usage metrics, failure records, validation, and commit linkage.
- Device-local `lexical-v1` retrieval index across the four durable knowledge layers with ranked snippets and line-addressable citations.
- Multidimensional researcher designs covering identity, scope, sources, process, outputs, capabilities, and governance, with optional editable presets.
- Executable capability contracts for bundled code, model instructions, and instance-provided adapters.
- Instance-aware, redacted adapter readiness diagnostics for video and enterprise document connectors.
- Privacy gates that reject embedded connector values, private paths, raw secrets, and enterprise markers in release packages.
- Cross-dimensional acceptance matrix proving themes, media sources, research processes, audiences, and outputs can be composed independently.
- Dedicated application modules for evidence intake, source indexing, mechanical output quality, and editorial quality.

### Changed

- Pipeline CLI parsing is separated from the transaction engine; legacy direct refinement submission remains compatible while model-run submission is now available.
- Retrieval excludes YAML frontmatter, down-ranks relationship-navigation sections, requires mixed-language named-entity matches, and preserves original source line citations.
- `SKILL.md` now uses progressive disclosure and is reduced below the architecture target while routing detailed rules to references.
- Researcher manifests store only compact execution plans; shared capability definitions are not duplicated into each workspace.
- Legacy researcher types are deprecated compatibility aliases; new configurations persist `research_design` schema v2 instead of a nominal type.
- Enterprise integrations are declared as generic `instance_only` adapter capabilities and remain blocked until configured and available.
- The architecture ratchet for `SKILL.md` is lowered to prevent renewed entrypoint growth.

### Security

- Real MCP configuration, credentials, tenant/node identifiers, private paths, enterprise taxonomies, and enterprise knowledge are prohibited from the shared package.
- Researcher diagnostics expose readiness, reasons, and missing field names without returning connector values.

### Compatibility

- Existing `knowledge` and `video` profiles, legacy configs, CLI command names, and researcher-local runtime behavior remain supported.
- Missing video or enterprise adapters are reported explicitly; they are not treated as successful execution.

## [0.7.7] - 2026-08-09

### Added

- Shared source-inventory reconciliation for audit and transactional pipeline bootstrap.
- Unique refinement lookup across source-directory moves, dated refinement renames, and Unicode punctuation changes.
- Regression coverage for stale temporary outputs, ambiguous matches, and legacy renamed refinements.

### Changed

- `audit` now reports verified processed sources only when an index record and a durable refinement can be reconciled.
- New local ledgers import existing durable refinements as committed instead of rediscovering them as model work.

### Fixed

- Stale output paths no longer hide genuinely unrefined sources or cause already refined sources to be processed twice.
- Paths outside the mapped source-refinement layer, including `/private/tmp` staging files, are not accepted as durable outputs.

## [0.7.6] - 2026-08-09

### Added

- Source-channel classification basis and confidence, with metadata-first aliases and conservative unknown fallback.
- Verification-ledger reconciliation for physical rows, superseded results, orphaned results, stale results, and parse errors.
- Ten-case deterministic golden refinement regression covering required-claim preservation and forbidden-claim detection.

### Changed

- The default regression runner now includes the portable new-user end-to-end lifecycle.
- Video researcher initialization creates only video-profile input and refinement directories.

### Fixed

- Ambiguous words such as “研究” and “报告” no longer grant report-level authority without explicit provenance.
- Stale verification items are counted once and latest result dictionaries are no longer mutated during status rendering.

## [0.7.5] - 2026-08-09

### Added

- Source-quality and verification module covering evidence channels, authority, freshness, bias, A-D tiers, risk signals, verification ledgers, and stale-result detection.
- Shared platform date parser and regression tests for primary-versus-marketing weighting and stale verification.

### Changed

- Existing source-quality and verification CLI commands retain their contracts while delegating to the governance module.
- `kb_manager.py` decreased from 3347 to 2974 lines; its line ratchet decreased to 2975.

### Fixed

- Quantified, ranking, report-year, and forecast regexes preserve their original digit/whitespace semantics after module extraction.

## [0.7.4] - 2026-08-09

### Added

- Promotion runtime module for idempotent decision ledgers, resumable checkpoints, and system-scoped deterministic stubs.
- Shared platform clock and JSONL persistence primitives.
- Regression tests for ledger idempotency, parse-error reporting, checkpoint state, and formal-layer write isolation.

### Changed

- Promotion write behavior remains behind the existing `--apply` and `--create-stubs` boundaries while delegating to the runtime module.
- `kb_manager.py` decreased from 3601 to 3347 lines; its line ratchet decreased to 3350.

## [0.7.3] - 2026-08-09

### Added

- Dedicated promotion module for cluster rules, source matching, five-dimension scoring, non-promotion reasons, artifact candidates, and review rendering.
- Portable naming domain primitive and promotion-module feature tests.

### Changed

- Existing `promote` and `run` commands retain their output contracts while delegating topic decisions to the extracted module.
- `kb_manager.py` decreased from 3833 to 3601 lines; its line ratchet decreased to 3605.

### Fixed

- Portable cluster-rule lookup now resolves from the skill root after moving code from `scripts/` into `kbm/application/`.

## [0.7.2] - 2026-08-09

### Added

- Dedicated refinement-quality application module covering per-file blockers, warnings, batch repetition detection, and Gate-10 report rendering.
- Direct feature tests for valid refinements, placeholder rejection, and repeated-model batch blocking.

### Changed

- Existing `gate-10`, `check-refinement`, `run`, pipeline submit, and pipeline adopt workflows retain their CLI contracts while consuming the extracted module.
- `kb_manager.py` decreased from 4141 to 3833 lines; its line ratchet decreased to 3835.

## [0.7.1] - 2026-08-09

### Added

- Shared `kbm.domain.markdown` primitives for frontmatter, section, title, wikilink, and recursive Markdown-file parsing.
- Contract tests for Markdown parsing and deterministic recursive collection.

### Changed

- Gate-10 and governance callers now consume the shared Markdown domain primitives through compatibility imports.
- `kb_manager.py` decreased from 4207 to 4141 lines; its line ratchet decreased to 4145.

## [0.7.0] - 2026-08-09

### Added

- Application-scoped release package validator for required files, README freshness, portable fixtures, and source hash refresh.
- Independent regression coverage for release validation and stale-hash detection.

### Changed

- Legacy `package-lint` remains CLI-compatible but delegates to `kbm/application/package_release.py`.
- `kb_manager.py` decreased from 4271 to 4207 lines and its architecture ratchet decreased to 4210 lines.

## [0.6.0] - 2026-08-09

### Added

- Executable `architecture-contract.json` defining modular-monolith boundaries, current complexity ratchets, target sizes, legacy CLI contracts, and allowed script dependencies.
- `scripts/architecture_check.py --strict` and `tests/test_architecture.py` to prevent further monolith growth or accidental CLI contract loss before decomposition.
- Target module ownership for Intake, Refinement, Synthesis, Assets, Publication, Governance, and Platform.
- `kbm/domain/researcher.py` with an explicit researcher identity and isolation contract.
- Shared `kbm/platform` modules for configuration, researcher-scoped paths, runtime isolation, backups, and operation logs.
- Multi-researcher regression tests proving independent SQLite ledgers, source discovery state, and system-file paths.
- `kb_researcher.py` commands for registry initialization, researcher registration, selection, inspection, diagnosis, and profile-driven workspace initialization.
- Dependency-free regression runner with researcher registry, duplicate identity, shared-workspace rejection, and video-profile tests.
- Video researcher profile with device-local runtime, video-only source mapping, derived-media directories, and an explicit disabled adapter state until ingestion is implemented.

### Changed

- `ARCHITECTURE.md` now distinguishes the current monolith from the target module architecture and defines a strangler-style migration sequence.
- Release checks now include the architecture gate.
- `kb_manager.py` and `kb_pipeline.py` now consume the shared platform core while preserving their existing CLI commands.
- Legacy configs are mapped to an implicit researcher without rewriting the config file; new `init` runs write an explicit researcher object.
- Researcher selection is stored only in the registry; knowledge, active state, SQLite ledgers, and caches remain researcher-local.

## [0.1.3] - 2026-07-27

### Added

- Freshness filename rule for formal Markdown artifacts: source refinements use `updated_at created_at saved_at title.md`; topic pages, reusable assets, and outputs use `updated_at created_at title.md`.
- `audit-filename-dates` command to verify freshness filenames and `updated_at >= created_at`.
- `normalize-filename-dates` command to rename formal knowledge artifacts, update H1 titles, and migrate Obsidian wikilinks.
- `--touch-updated-at` option for intentional full-library refreshes.
- `quality-gate` blocker for freshness filename/date-order violations.

### Changed

- `SKILL.md` now requires `updated_at` and filename first date to be updated together whenever a formal knowledge artifact is modified.
- `saved_at` semantics for source refinements clarified: it means original/source-library saved date, can be recovered from the canonical `source_file` filename prefix, and must not silently fall back to `created_at`, `updated_at`, `processed_at`, or publication date.

### Fixed

- Source-refinement freshness normalization now removes stale extra date prefixes when correcting polluted `saved_at` values, preventing filenames with four visible dates.
- Wikilink refresh during freshness normalization no longer mutates system backup Markdown files.

## [0.1.0-beta] - 2026-07-22

## [0.1.1] - 2026-07-23

### Added

- Gate-10 source refinement quality gate with structural, content integrity, and batch-level model-text repetition checks.
- `python3 scripts/kb_manager.py gate-10 --config <cfg> [--strict] [--apply]` CLI command.
- Quality rules section in `kb-config.json`: `quality.template_patterns`, `quality.boilerplate_topics`, `quality.batch_model_repeat_threshold` — replaces hardcoded domain-specific patterns.
- Auto-discovered cluster scoring: `has_question`, `has_reuse`, and `has_output` dimensions now inferred from source topics, not only from pre-configured cluster rules.
- `backup_file()` helper with configurable retention (default 5 copies) and `append_operation_log()` for `run-log.jsonl`.
- Two new pipeline reconciliation tests: path alias recovery and blank output repair.

### Changed

- `00-system/` directory restructured into `active/` (current state), `reports/` (regenerable snapshots), and `backups/` (auto-rotating).
- `system_file()` now routes to subdirectories with automatic fallback to old flat layout for existing knowledge bases.
- `ensure_system_files()` creates `active/`, `reports/`, `backups/` subdirectories and writes defaults to the correct subdirectory.
- `build_cluster()` scoring fixed: `risk_controlled` no longer always `True` for high-risk clusters (`verification_required` defaults to `False`).
- `build_cluster()` has_reuse fallback threshold lowered from 5 to `min_sources * 2`; has_output gains an equivalent fallback.
- `package-lint` README freshness check changed from `st_mtime` comparison to content SHA-256 comparison with `.source_hash` manifest; `--apply` writes hash on pass.
- `cmd_run --apply` now runs `gate-10` alongside existing quality-gate and promotion stages.
- Pipeline `reconcile_processed_index()` supports path alias resolution, SHA-256 content-hash fallback, and automatic repair of legacy blank output paths.
- Refined `check_refinement()` fixing 4 incorrect `"\\n"` escape sequences and removing a duplicate `split_frontmatter()` definition.

### Fixed

- `risk_controlled` scoring bug: `verification_required` default `True` → `False`, no longer grants automatic points to high-risk clusters.
- Auto-discovered clusters no longer score 2/5 with 1 point wasted on a bug; now reach 5/5 with content-aware inference.
- `split_frontmatter()` duplicate definition: new yaml-based version was shadowed by older manual parser.
- `check_refinement()` newline splitting: `core.split("\\n")` and `body.replace("\\n")` used literal backslash-n instead of actual newlines.
- `ensure_system_files()` wrote to old flat paths instead of new subdirectories, causing `promote --apply` to fail with `FileNotFoundError`.
- `test_kb_manager.py`: `promotion-decision.jsonl` path updated to `00-system/active/` and `package-lint` test now passes with content-hash checking.

### Added

- Initial public beta package for `knowledge-base-manager`.
- Chinese user-facing README for target users who do not read English skill instructions.
- Portable five-layer knowledge-base model: system, source refinements, topic pages, reusable assets, outputs.
- Codex skill entrypoint through `SKILL.md`.
- Script-first operation for non-Codex platforms through `scripts/kb_manager.py`, `scripts/kb_pipeline.py`, `scripts/ebook_probe.py`, `scripts/obsidian_linker.py`, and `scripts/official_account_library.rb`.
- New-user end-to-end test covering initialization, source processing, promotion review, stub safety, quality gate, and package lint.
- Package lint checks for release-blocking issues, including README freshness, user-profile isolation, temporary files, and required public distribution files.
- Optional 8XX-style profile under `examples/profiles/8xx/`, separated from the portable default.

### Changed

- Promotion stubs are written only under the system stub area, not directly into formal topic pages, reusable assets, or outputs.
- README synchronization is now a release requirement checked by `package-lint --strict`.
- Source discovery now reconciles path aliases and legacy index records with blank output paths when the canonical refinement exists, while refusing title-only deduplication.

### Known Limitations

- This is a beta release. It is suitable for controlled trial use, not a mature turnkey product.
- Semantic clustering is still rule-assisted and should be reviewed by humans for important knowledge bases.
- High-risk claims require external verification before public, legal, medical, financial, or business-critical use.
- PDF extraction requires optional local PDF libraries for text PDFs; scanned PDFs require OCR before processing.
- Platform adapters outside Codex currently rely on script-first or instruction-copy integration rather than native plugin packaging for every agent platform.


## [0.1.2] - 2026-07-24

### Added

- Lightweight promotion lane for cases, expressions, definitions, distinctions, warnings, metaphors, and MOC split candidates.
- Portfolio health flags for stagnant cases, expressions, MOCs/topic pages, and unresolved `unclassified` candidates.
- `check-refinement` subcommand: single-file gate-10 check returning JSON, used by pipeline at submit/adopt-existing entry points.
- `sync-relations` subcommand: auto-populate `related_sources` across all refinements based on `theme_cluster` matching.
- Pipeline gate-10 enforcement: `submit` and `adopt-existing` reject refinements that fail gate-10 checks.
- YAML frontmatter validation in `quality-gate`: full YAML parse for 20/30/40 files, quote-conflict detection for 10-layer files.
- Template compliance check in `quality-gate`: 10-layer files must have exactly 20 fields in exact order.
- `created_at` + `updated_at` field requirement enforced across all layers.
- `evidence_from` field requirement for 20/30/40 artifacts.
- `feynman-template.md`: standardized Feynman explanation template with required sections.
- Delivery self-check rules documented in SKILL.md (rules 16-17).

### Changed

- Evidence gate is now artifact-specific: heavy assets still require stronger multi-source evidence, while lightweight cases/expressions can use one strong attributed source with explicit reuse and fact-risk boundary.
- All 354 source refinements standardized to 20-field template format (field order, tag normalization, YAML cleanup).
- 147 inline array tags (`"[a", "b"]"`) fixed to proper YAML list items.
- 140 verification queue items auto-resolved as stale (sources rewritten).
- All article drafts rewritten with real content (no placeholders).
- `quality-gate()` checks `evidence_from` field presence (≥1 entry required).
- `build_cluster()` quality weighting: clusters with <5% rich refinements have auto-discovery points stripped.
- SKILL.md rules 13-17 cover evidence gate, template reference, quality audit, self-check.
