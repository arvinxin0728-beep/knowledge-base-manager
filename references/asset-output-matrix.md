# Asset and Output Generation Matrix

Use this reference when deciding whether processed sources, topic pages, batches, or active projects should produce reusable assets or outputs.

The goal is not to fill every folder. The goal is to create the smallest set of artifacts that make knowledge reusable and consumable.

For stage authorization, cost control, and resuming interrupted promotion work, read `promotion-control-and-resume.md`.

## Core Rule

Every artifact needs a trigger, a source boundary, and a quality standard.

### Evidence Gate

Every 20/30/40 artifact MUST include an `evidence_from` (or `supported_by`) YAML field. The minimum evidence count depends on artifact type:

| Artifact type | Minimum evidence | Rule |
|---|---:|---|
| Topic page | 3 source refinements | Must synthesize multiple sources around one question. |
| MOC / index page | 1 source, topic page, or navigation basis | Navigation pages route knowledge; they need traceability but not the full synthesis burden of a topic page. |
| Method, workflow, checklist, SOP, standard, scoring card, template, design card | 3 source refinements preferred; 1 strong source only when marked draft with clear limits | Must include steps, conditions, limits, and when not to use it. |
| Framework, model, map, decision tree, loop | 3 source refinements preferred | Must show relationships, not just a list. |
| Article draft, solution material, decision memo, Feynman explanation | 3 source refinements preferred; 2 allowed for low-risk Feynman explanations | Must name reader/scenario and fact boundary. |
| Case, case-pattern, anti-case | 1 primary source refinement | Must include background, action, result or claimed result, transferable lesson, and fact-risk boundary. |
| Expression, definition, distinction, warning, metaphor | 1 primary source refinement | Must include attribution, source context, and `use_when`/使用场景 guidance. |
| Review record | 1 system event, batch, audit, or run log entry | Must record what happened, evidence, diagnosis, rule change, and next experiment. |

This prevents heavy artifacts from being generated on weak evidence while allowing lightweight assets such as cases and expressions to grow from one strong source with explicit boundaries.

### Template Reference Requirement

Before writing any new 10/20/30/40 artifact, open at least one existing artifact of the same type that is known to be correct. Copy its frontmatter field order, body section names, tag style, and wikilink format exactly. Do not write from memory or impression.

Known violation patterns:
- Writing article drafts with `evidence_from`, `output_type`, and `source_theme` fields when existing drafts don't have them
- Adding extra tags beyond what the template specifies
- Using placeholder text like "（待补充）" or "（核心观点已写入）" instead of real content
- Guessing body section structure instead of matching the existing pattern

- Trigger: why this artifact should exist now.
- Source boundary: which sources or topic page support it, and what remains uncertain.
- Quality standard: how to judge whether it can be reused without rereading the raw sources.

If no trigger is present, do not create the artifact. Record it as deferred in the topic page or promotion review.

## Promotion Guards

These guards override the matrix:

- Repeated source count alone never proves that a reusable asset exists. It only proves that a topic deserves review.
- A generated placeholder question such as "What do current sources support about X?" does not count as a clear research question.
- A reusable asset must have a parent topic page, a specific asset type, and a non-duplication reason.
- Do not default unclassified reusable material to Method. Use `unclassified` until the method, case, expression, or framework-map trigger is proven.
- A topic page with more than 5 linked reusable assets or more than 5 linked outputs must trigger a structure review before new assets or outputs are created.
- A Method asset must include steps, conditions, limits, and when not to use it. Otherwise it remains a candidate.
- Do not force lightweight assets through heavy-asset gates. A case or expression can be promoted from one strong source when its source boundary and reuse context are explicit.
- Do not let all candidates remain `unclassified`. After each promotion review, split opportunities into concrete candidate pools: `topic_candidates`, `case_candidates`, `expression_candidates`, `framework_candidates`, `method_candidates`, `output_candidates`, and `moc_split_candidates`.

## Reusable Asset Matrix

Use a controlled `asset_type` value in frontmatter. The folder is only the broad storage category; `asset_type` is the callable subtype.

Recommended reusable asset subtypes:

| Broad folder | Preferred `asset_type` values |
|---|---|
| Method / 方法论 | `method`, `workflow`, `checklist`, `sop`, `operating-procedure`, `operating-standard`, `scoring-card`, `template`, `design-card` |
| Case / 案例 | `case`, `case-pattern`, `anti-case` |
| Expression / 金句表达 | `expression`, `definition`, `distinction`, `warning`, `metaphor` |
| Framework map / 框架图谱 | `framework`, `model`, `map`, `decision-tree`, `loop` |

Do not use broad folder names such as `methods`, `方法论`, `框架图谱`, or `金句表达` as `asset_type`. If the subtype is unclear, use `unclassified` and keep the item as a candidate.

| Asset type | Create when | Do not create when | Minimum standard |
|---|---|---|---|
| Method | A repeatable process, workflow, checklist, or decision rule appears in one strong source or across multiple sources. | The source only describes an opinion or one-off action. | Steps, conditions, limits, and when not to use it are clear. |
| Case | A source contains a concrete situation, action, result, and transferable lesson. | The example is only decorative or lacks outcome/context. | Background, action, result, lesson, and applicability boundary are clear. |
| Expression | A source contains a compact definition, distinction, metaphor, warning, or memorable formulation that can improve future writing or explanation. | The sentence is merely catchy, unsupported, too context-dependent, or too long to quote safely. | Short, attributable, context-preserved, and paired with "use when" guidance. |
| Framework map | A topic contains a structure: layers, sequence, causal chain, role system, feedback loop, decision tree, or concept relationship. | The content is only a list of points without structural relationship. | Nodes, relationships, direction, and interpretation are clear. |

## Lightweight Promotion Lane

Use this lane before high-cost generation whenever a batch contains reusable small units.

| Candidate pool | Promote when | Minimum fields before generation |
|---|---|---|
| `case_candidates` | One source has a concrete situation, action, result/claimed result, and transferable lesson. | `candidate_id`, `artifact_type`, `parent_topic`, `source_refs`, `fact_risk`, `reuse_context`, `recommended_action`. |
| `expression_candidates` | One source contains a compact definition, distinction, warning, metaphor, or reusable wording. | `candidate_id`, `artifact_type`, `parent_topic`, `source_refs`, `use_when`, `source_context`, `recommended_action`. |
| `moc_split_candidates` | A topic mixes distinct questions, reuse modes, or output scenarios. | `candidate_id`, `parent_moc`, `proposed_child`, `reason_to_split`, `source_refs`, `risk`. |

Lightweight assets are not filler. They must be small, attributable, and callable. If they cannot be reused without rereading the raw source, keep them as candidates.

## Output Matrix

| Output type | Create when | Do not create when | Minimum standard |
|---|---|---|---|
| Feynman explanation | A concept or method is important but still hard to explain simply. | The topic is mostly factual reporting or requires unresolved verification. | Plain-language explanation, one accurate example, boundary, and understanding test. |
| Article draft | A topic page has a clear claim, reader problem, argument structure, and manageable fact risk. | The theme is only a material collection or contains high-risk unverified claims. | Reader, core claim, argument chain, evidence, counterpoint/limit, and fact-check notes. |
| Solution material | A topic can guide action, implementation, project design, operating rules, or evaluation. | The content depends on a private implementation but is not labeled as such. | Standard method first; local mapping only as explicit example or appendix. |
| Decision memo | A user or team needs to choose between options, commit resources, or set direction. | There is no decision owner, choice, or consequence. | Decision question, options, criteria, tradeoffs, recommendation, risks, next step. |
| Review record | A processing batch, promotion round, output evaluation, or failed workflow reveals system-level lessons. | Nothing changed in the system or no evidence exists. | What happened, evidence, diagnosis, rule change, and next experiment are recorded. |

## Trigger Checklist

Before creating files under reusable assets or outputs, answer:

1. What artifact type is triggered?
2. Which source refinement or topic page supports it?
3. What would make this artifact reusable outside the original context?
4. What must be verified before public or business-critical use?
5. What should be deferred rather than generated now?
6. Which existing asset could this duplicate or replace?
7. Which parent topic page owns this artifact?

If the answer to question 1 is unclear, update the topic page instead of creating a new asset or output.

## Cost and Approval Rule

Use the lowest-cost action that preserves quality:

- Low-cost: scan indexes, source-refinement headings, existing topic pages, tags, links, and MOCs.
- Medium-cost: compare candidate sources, score clusters, and produce `asset-output-candidates.md`.
- High-cost: generate or substantially rewrite topic pages, reusable assets, and outputs.

High-cost generation requires an approved candidate or an explicit user request for the exact artifact, cluster, or output type. If the user stops before approval, record the candidate state instead of generating speculative files.

## Asset Lifecycle

Every reusable asset should have one lifecycle status:

- `candidate`: possible asset, not yet validated.
- `draft`: created but not fully tested against quality standards.
- `active`: reusable as a stable asset.
- `merge_candidate`: likely duplicates or overlaps another asset.
- `superseded`: replaced by a stronger asset.
- `deprecated`: retained for history but not recommended for reuse.

## Batch-Level Review Trigger

Create a review record when any of these occur:

- a batch processes many sources but produces no new topic judgment;
- promotion decisions repeatedly stop at source refinement;
- output evaluation marks files as needs_revision;
- Obsidian links or tags become too broad to explain source logic;
- the same topic is repeatedly split across near-duplicate pages;
- a new rule is added because prior outputs were not reusable.

Review records are outputs because they improve the knowledge system itself. They should not be generated from individual articles unless the article is about the knowledge system process.

## Portfolio Balance Check

After a promotion round, inspect the artifact mix:

- Too many methods and few cases: source refinements may be over-abstracting.
- Too many solution materials and few article drafts: output intent may be internal but not public-facing.
- Few expressions: reading template may not be capturing reusable phrasing.
- Few framework maps: topic pages may be listing points instead of modeling relationships.
- No review records: the system may be running without learning from its own behavior.

Use this check to decide the next artifact to create, not to force artificial balance.

### Portfolio Health Flags

Record these flags in candidate or review reports:

- `case_count = 0`: red flag unless the source batch has no concrete cases.
- `expression_count < 5` after many sources: yellow flag; scan for definitions, distinctions, warnings, and metaphors.
- `unclassified_candidates > 0`: red flag; classify before high-cost generation.
- Topic/MOC count unchanged across large batches: yellow flag; inspect `moc_split_candidates`.
- Methods/frameworks growing while cases/expressions stay flat: yellow flag; the system may be over-abstracting.
