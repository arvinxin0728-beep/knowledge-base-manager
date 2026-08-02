# Publication Candidate Handoff

Use this reference when selecting scheduled public-account/WeChat publication candidates from 40 outputs or handing a knowledge output to a channel-specific editing/layout skill.

## Boundary

Knowledge Base Manager is the knowledge researcher and upstream editorial gate. It decides whether an output is worth publishing, whether the evidence is safe enough, and what the publication angle should be.

It does not own channel-specific layout, visual styling, platform HTML, or final WeChat editor formatting. Those belong to a publishing/layout skill such as `wechat-article-layout`.

## Candidate decision

Do not rank candidates only by writing polish. For each candidate, check:

- schedule fit: whether the topic fits the planned publication date and content sequence
- audience fit: whether the reader problem is clear for the target account
- knowledge value: whether the piece has a real insight, framework, case, or practical method
- evidence status: whether central claims have enough credible and current support
- risk level: whether unsupported facts, market claims, product claims, or current data can mislead readers
- freshness: whether the knowledge is stale or depends on time-sensitive sources
- format fit: long article, short concept, framework card, checklist, Feynman explanation, case note, or decision memo

## Blocking rules

Do not mark a candidate `ready_for_layout` when any of these apply:

- `lifecycle_status`, `health_status`, or article metadata indicates `needs_evidence`, `weak_evidence`, `needs_revision`, `parked`, or equivalent
- a P0 evidence gap is open
- a P1 evidence gap affects the central public claim and cannot be removed or clearly bounded
- output verification is unresolved for claims that will appear in the public article
- the article depends on current facts, rankings, prices, policies, company claims, or market data that have not been checked against current authoritative sources

If the risky claim can be removed without damaging the article, downgrade the scope and state the boundary. Otherwise choose `needs_evidence`, `needs_rewrite`, or `defer`.

## Handoff card

When passing a candidate downstream, create or report a handoff card:

```yaml
publication_candidate:
  source_output:
  recommended_publish_date:
  target_channel: 微信公众号
  target_account:
  article_h1:
  topic_type:
  audience:
  publish_angle:
  reader_problem:
  key_materials:
  evidence_status:
  open_evidence_gaps:
  risk_level:
  required_fact_check:
  recommendation: ready_for_editing | ready_for_layout | needs_evidence | needs_rewrite | defer
  handoff_to: wechat-article-layout
  handoff_notes:
```

Use `ready_for_editing` when the article needs channel expression work before layout. Use `ready_for_layout` only when the visible article body is sufficiently final and the remaining work is formatting, naming, metadata, images, or platform checks.

## Current-project implementation

For the user's current 8XX-style project, formal knowledge outputs live under `888-AI知识库/40-输出`, while external WeChat-ready artifacts live under `899-文章输出`.

Do not mutate formal 40 outputs merely to create channel packaging unless the user explicitly asks to update the knowledge artifact itself. Packaging files, HTML, images, and publish-status filenames belong to the downstream publishing/layout workflow.

## Regression checks

Before handing off, run the relevant KB quality gate or inspect the candidate's current metadata/report:

- unresolved wikilinks should not affect the candidate
- filename freshness issues should not affect the candidate
- unresolved output verification should be zero for public claims
- evidence-gap warnings must be either closed, downgraded, or explicitly bounded in the handoff card

Do not claim that an article has been uploaded, previewed, or published unless the downstream tool or user has actually completed that platform operation.
