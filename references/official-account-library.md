# Official Account Library Module

Use this reference when a mapped source library contains WeChat/公众号 Markdown exports that need audit, import, dedupe, flattening, or filename normalization.

This module is part of the single installed package and provides deterministic public-account library hygiene.

## Canonical Structure

Expected base directory:

```text
笔记同步助手/
└── 公众号原始文章/
```

Canonical article filename:

```text
YYYY-MM-DD original title.md
```

If a user's config points directly to `公众号原始文章`, use its parent as `--base` when running `scripts/official_account_library.rb`.

## Script

Run:

```bash
ruby scripts/official_account_library.rb audit --base <path-to-笔记同步助手>
ruby scripts/official_account_library.rb import-dates --base <path-to-笔记同步助手> --from 2026-06-01 --to 2026-07-20
ruby scripts/official_account_library.rb import-dates --base <path-to-笔记同步助手> --from 2026-06-01 --to 2026-07-20 --apply
ruby scripts/official_account_library.rb dedupe --base <path-to-笔记同步助手>
ruby scripts/official_account_library.rb dedupe --base <path-to-笔记同步助手> --apply --quarantine <path-to-quarantine>
ruby scripts/official_account_library.rb prune-empty --base <path-to-笔记同步助手> --from 2026-06-01 --to 2026-07-20
ruby scripts/official_account_library.rb prune-empty --base <path-to-笔记同步助手> --from 2026-06-01 --to 2026-07-20 --apply
```

## Safety Rules

1. Run the requested mutation without `--apply` first.
2. Report counts, destination conflicts, exact duplicates, and non-Markdown files.
3. Never overwrite an existing destination.
4. Use SHA-256 equality before quarantining a duplicate; do not permanently delete it.
5. Keep the filename without trailing ` 1` when exact duplicates exist.
6. Request filesystem approval when the real library path is outside the writable sandbox.
7. Run the matching audit again after every mutation.
8. Do not remove a directory unless it is completely empty.

## Commands

### audit

Counts:

- root articles
- nested Markdown files
- malformed names
- exact duplicate groups
- duplicate extras

### import-dates

Select only top-level directories named `YYYY-MM-DD` in an inclusive date range. Recursively move `.md` files into `公众号原始文章`, using the directory date and current basename as the original title. Strip one existing leading `YYYY-MM-DD ` to avoid double prefixes.

### dedupe

Group root Markdown files by SHA-256. Preserve the clean filename and move only byte-identical extras into the explicitly configured quarantine directory. `dedupe --apply` refuses to run without `--quarantine`.

### prune-empty

Remove only empty top-level date directories in the inclusive range.

## Non-Markdown Attachments

Do not rename non-Markdown attachments or move them implicitly. Surface them for a separate user decision.
