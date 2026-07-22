# Changelog

All notable changes to this project should be recorded here.

The format follows Keep a Changelog conventions loosely, and this project uses semantic versioning while it is distributed publicly.

## [0.1.0-beta] - 2026-07-22

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

### Known Limitations

- This is a beta release. It is suitable for controlled trial use, not a mature turnkey product.
- Semantic clustering is still rule-assisted and should be reviewed by humans for important knowledge bases.
- High-risk claims require external verification before public, legal, medical, financial, or business-critical use.
- PDF extraction requires optional local PDF libraries for text PDFs; scanned PDFs require OCR before processing.
- Platform adapters outside Codex currently rely on script-first or instruction-copy integration rather than native plugin packaging for every agent platform.
