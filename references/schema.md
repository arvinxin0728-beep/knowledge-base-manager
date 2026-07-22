# Processed Index Schema

Use this reference when reading, normalizing, or writing `processed-index.jsonl`.

## Canonical Fields

Each line is one JSON object.

| Field | Required | Meaning |
|---|---|---|
| `schema_version` | yes | Current value: `1`. |
| `source_id` | yes | Stable 16-char hash from source hash/path/title. |
| `source_path` | yes | Absolute or mapped path to the original source. |
| `source_sha256` | recommended | SHA-256 of the source when available. |
| `source_type` | yes | Canonical type such as `ebook`, `public_account_article`, `article`, `web_article`. |
| `title` | yes | Human title used in reports. |
| `processed_at` | yes | ISO date or datetime. |
| `output_file` | yes | Source-refinement note path. |
| `topics` | yes | Array of candidate topics/tags. |
| `status` | yes | Usually `processed`. |
| `fact_risk` | recommended | `low`, `medium`, `high`, or `unknown`. |
| `fact_check_required` | recommended | Boolean. |

## Normalization

Run:

```bash
python3 scripts/kb_manager.py normalize-index --config <kb-config> --apply
```

The command maps older aliases such as `source_file` to `source_path`, normalizes source types, converts topic strings into arrays, creates `source_id`, and writes a dated backup before replacing the index.
