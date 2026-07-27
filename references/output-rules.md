# Output Rules

Use this reference when deciding what to create after sources have been processed.

For artifact-type triggers and quality gates, read `asset-output-matrix.md` before creating `30-reusable-assets` or `40-outputs`.

For token-cost tiers, human approval gates, and resumable checkpoints, read `promotion-control-and-resume.md` before moving from candidate review into high-cost generation.

## Layer Boundaries

| Layer | Unit | Purpose | Create when |
|---|---|---|---|
| Source refinement | One source | Understand and compress a source. | Every processed source. |
| Topic page | One question/theme | Synthesize multiple sources. | 3+ sources, explicit user request, or active project. |
| Reusable asset | One reusable module | Make methods/cases/expressions/frameworks callable later. | A model, case, phrase, checklist, or framework recurs or is useful. |
| Output | One audience/task | Communicate or act. | There is a target reader, scenario, or user asks for output. |

Do not create assets or outputs only because a folder exists. Create them when the trigger in `asset-output-matrix.md` is present.

Use two promotion lanes:

- Heavy lane: topic pages, methods, frameworks, solution materials, article drafts, and decision memos. These need stronger evidence, usually 3+ source refinements, and explicit approval for high-cost generation.
- Lightweight lane: cases, case patterns, anti-cases, expressions, definitions, distinctions, warnings, and metaphors. These may be generated from one strong source when attribution, source context, reuse context, and fact-risk boundary are explicit.
- Navigation lane: MOC/index pages need traceability and meaningful routing, but they do not need the same 3-source synthesis threshold as topic pages.

High-cost generation of topic pages, reusable assets, or outputs requires either an explicit user request for the exact artifact or approval of a candidate list. When approval is missing, create or update `asset-output-candidates.md` and stop at `waiting_for_approval`.

Do not create a 30-layer asset unless a parent topic page exists or will be created in the same approved generation step. Do not create a 40-layer output unless it names its target reader or scenario and links to its source topic page.

Before stopping at candidate review, avoid leaving items as `unclassified`. Split them into concrete pools: topic, case, expression, framework, method, output, and MOC split candidates.

## Portability Gate

Topic pages, reusable assets, and outputs are portable by default unless the file is explicitly labeled as a local operating note, personal implementation plan, migration note, case record, or review record.

In portable artifact bodies:

- use semantic layer names: source refinement, topic synthesis, reusable asset, output, system index;
- do not use mapped directory codes such as `10-source-refinements`, `20-topic-pages`, `30-reusable-assets`, `40-outputs`, `10-来源精炼`, `20-主题页`, `30-可复用资产`, or `40-输出` as method language;
- do not hard-code one user's batch size such as "30-50 public-account articles" or "every 30 sources" unless the artifact is a local operating note;
- do not present a specific source type such as public-account articles as the default method; say "source materials" and list examples only when needed;
- do not use absolute paths, private folder names, or user-specific workspace names in the main body;
- if local mapping helps, put it under a section titled "Implementation example" or "Local mapping" and make clear that it is not the method itself.

Relationship metadata and evidence sections may still link to source-refinement notes and raw source titles. The portability gate applies mainly to the explanatory and procedural body of the artifact.

For 30-layer assets, separate directory category from callable subtype:

- Directory category answers where the file lives: method, case, expression, framework map.
- `asset_type` answers how the artifact should be reused: `workflow`, `checklist`, `scoring-card`, `framework`, `expression`, and so on.
- Do not use `方法论` or `methods` as a default `asset_type`; that hides whether the asset is a process, checklist, standard, template, or framework.
- If a file in the Method directory is actually a model/map/layer structure, move it to the Framework Map directory or mark it for structure review.
- For cases and expressions, a single source is allowed, but the body must clearly mark source context and fact boundary. Do not inflate a one-source case into a general rule.

## Promotion Review Rules

Run promotion review after every processing batch. The review converts raw topic candidates into semantic topic clusters and decides whether each cluster stays in the inbox or moves into topic pages, reusable assets, and outputs.

### Required Review Files

| File | Purpose |
|---|---|
| `topic-clusters.md` | Semantic clusters that merge related tags and sources. |
| `promotion-review.md` | Scored promotion decisions, actions, and reasons for non-promotion. |
| `asset-output-candidates.md` | Approval surface for high-cost 20/30/40 generation. |

### Promotion Score

Score each topic cluster from 0 to 5.

| Dimension | Question | Point |
|---|---|---:|
| Source count | Are there 3 or more relevant sources after semantic merging? | 1 |
| Question clarity | Can the cluster be framed as a concrete problem/question? | 1 |
| Reusability | Does it contain reusable methods, cases, phrases, checklists, or frameworks? | 1 |
| Output intent | Can it support an explanation, article, solution material, decision memo, or active project? | 1 |
| Fact-risk control | Are claims low-risk, or are verification needs explicitly marked? | 1 |

Repeated source count cannot score the reusability point by itself. A placeholder question generated from a tag cannot score the question-clarity point by itself.

The 3-source scoring rule applies to topic and heavy-asset promotion. Lightweight case/expression promotion can happen from one strong source, but it should not by itself create a new topic page or heavy output.

### Promotion Actions

| Score | Action |
|---:|---|
| 0-1 | Keep as topic candidate only; record why. |
| 2-3 | Create or update one topic page. |
| 4 | Create or update one topic page and at least one reusable asset. |
| 5 | Create or update one topic page, at least one reusable asset, and at least one output artifact. |

Do not use raw tag frequency alone. Merge semantically related tags first, then score the cluster against an actual question.

When a topic already has more than 5 assets or more than 5 outputs, the action should be `structure_review` unless the user explicitly approves a specific additional artifact.

### Structure Review Rules

When splitting an overloaded topic, do not create placeholder subtopic pages whose body only explains that a split happened. The split process belongs in a system review record; the topic pages themselves must be readable as knowledge pages.

A valid structure review must produce:

- a diagnosis record in the system layer explaining why the prior topic boundary failed;
- a parent topic page that states the general question and routes to child questions;
- child topic pages that follow the normal topic-page shape: topic question, current judgment, supporting sources, core model, reliable claims, uncertainties, output-ready material, assets to maintain, and next actions;
- updated relationship metadata and MOC pages;
- a post-change audit showing no overloaded clusters and no portability issues.

Do not split merely to satisfy a count threshold. Split only when the child topics represent different questions, reuse modes, or output scenarios.

## Topic Page Template

```markdown
# Topic title

---
stage: 主题页
version: v0.1
created_at:
status: draft
theme_type:
confidence:
source_count:
---

## Topic question
## Current judgment
## Supporting sources
## Core model
## What is reliable
## What is uncertain
## Output-ready material
## Assets to extract
## Output and asset matrix decision
## Next actions
```

## Feynman Output Rules

Feynman output should:

- explain one idea in plain language
- avoid jargon unless defined
- use examples that do not distort the idea
- separate universal principle from personal implementation
- end with a simple test of understanding or practical implication

Do not overload a Feynman explanation with folder names, tool names, or implementation-specific paths unless the intended audience is the system owner.

## Article Draft Rules

Article drafts should include:

- a clear core claim
- a reader problem
- a structured argument
- examples or cases
- limitations and fact-check notes

Mark `fact_check_required: true` when using public-account articles, product announcements, market data, company claims, or third-party tool descriptions as evidence.

## Solution Material Rules

Solution materials are portable by default. They should describe standard methods, roles, decisions, checklists, and operating rules that can be understood without a specific user's folder names or prior conversation.

Use implementation-specific folders and workflow details only when the file is explicitly intended as a personal implementation plan, local operating note, migration note, or case appendix. In that case, state this boundary at the beginning.

For reusable solution materials:

- use universal layer names such as source library, source refinement, topic page, reusable asset, output, system files, and MOC/index;
- do not use private folder codes or absolute paths as the method itself;
- keep local mappings in a clearly marked "Implementation example" or "Local mapping" section when needed;
- choose portable file titles that can be linked later without requiring private context;
- before finalizing, check whether a reader outside the original knowledge base can understand the artifact.

## Fact-Risk Levels

| Risk | Examples | Handling |
|---|---|---|
| Low | Personal workflow design, internal folder mapping, reading protocol | Can output with normal caveats. |
| Medium | Tool capability summaries, framework comparisons, source-derived claims | Mark as source-derived and verify when important. |
| High | Market data, legal/medical/financial claims, company events, personnel incidents, publishable accusations | Verify with primary or reliable current sources before formal output. |
