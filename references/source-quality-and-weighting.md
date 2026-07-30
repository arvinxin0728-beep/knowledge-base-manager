# Source Quality and Weighted Promotion

Use this reference when deciding whether source refinements should support topic pages, reusable assets, or outputs.

## Principle

Source refinements are not votes. They are evidence. Storage may be broad, but promotion must be weighted.

Do not let a large number of weak, stale, derivative, or marketing-heavy sources outweigh a smaller number of authoritative sources.

## Recommended source fields

For source refinements, use or infer:

```yaml
source_channel: public_account / book / report / paper / official_doc / interview / case / tool_doc / web_article / unknown
source_entity_type: official / institution / expert / practitioner / media / personal / unknown
source_evidence_mode: primary_data / cited_report / firsthand_case / tutorial / theory / opinion / summary / marketing / unknown
source_time_sensitivity: low / medium / high
source_quality_tier: A / B / C / D
source_authority: 1-5
source_freshness: 1-5
source_evidence_strength: 1-5
source_bias_risk: low / medium / high
promotion_weight: 0.2-1.5
```

These fields are an evidence map, not a moral judgment about the author.

## Default tier logic

- `A`: official documentation, primary report, academic paper, recognized professional book, standards, original data with traceable method.
- `B`: credible institutional report, expert/practitioner writing with clear evidence, high-quality case with concrete context.
- `C`: ordinary public-account article, commentary, summary, tutorial, or secondhand synthesis with some useful ideas.
- `D`: marketing-heavy, title-bait, unverifiable, stale tool/product claim, pure opinion, or content with high fact risk and no evidence.

## Knowledge-type matching

Match source types to artifact types:

- Principles and methods: prefer books, papers, official docs, institutional reports, or repeated practitioner evidence.
- Tool/product advice: require freshness and current official/tool evidence.
- Market/company facts: require primary source or current credible source; public-account summaries are only leads.
- Cases and scenes: public-account and practitioner sources can be useful, but must not be over-generalized.
- Expressions: one source can be enough if attribution and use context are clear.

## Promotion rule

Promotion should consider:

```text
weighted_evidence = source_count × source_quality × freshness × evidence_strength × diversity
```

Practical guards:

- A topic page should not be promoted from only low-tier public-account material unless explicitly marked as exploratory.
- A 30-layer method/framework should have at least one strong source or several mutually confirming medium sources.
- A case/expression can come from one source, but must be labeled as a case/expression, not a general rule.
- A 40-layer article can use public-account material for scenes and expression, but its core claim should be supported by topic pages or higher-quality sources.
- Stale high-risk facts must not silently support active conclusions.

## Operating rule

Start with automatic source-quality audit, then manually calibrate the misclassified sources. Do not treat the first automatic tier as final truth.

Use:

```bash
python3 scripts/kb_manager.py audit-source-quality --config <config> --apply
```

The report should guide promotion and health review, not automatically delete or demote sources.
