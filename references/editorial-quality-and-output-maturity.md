# Editorial Quality and Output Maturity

Use this reference when judging whether an output has real insight, argument strength, reader value, and publication readiness rather than only correct structure.

## Principle

A valid output is not merely formatted. It must change the reader's judgment, help them act, or preserve a reusable decision.

Structural checks answer: "Is the file shaped correctly?"

Editorial checks answer: "Is this worth reading or reusing?"

## Editorial rubric

Score each output from 1 to 5 on these dimensions:

| Dimension | Question |
|---|---|
| `insight_density` | Does it contain non-obvious judgment rather than generic correctness? |
| `problem_sharpness` | Is the reader's real problem, tension, or decision situation clear? |
| `argument_strength` | Are claims supported by reasoning, evidence, examples, counterpoints, and boundaries? |
| `originality` | Does it have a differentiated angle, contrast, or framing beyond a generic AI answer? |
| `actionability` | Can the reader use it to decide, explain, implement, or change behavior? |
| `expression_quality` | Does it have readable pacing, concrete scenes, memorable lines, and a strong ending? |

## Status mapping

- `publishable`: article average score >= 4.2 and no dimension below 4.
- `strong`: non-article output average score >= 4.2 and no dimension below 4.
- `revise`: average score >= 3.0 but at least one dimension needs work.
- `downgrade_to_draft`: average score < 3.0 or argument gate fails for a draft marked publishable.
- `park`: weak score and no clear reader/problem/use case.

## Repair mapping

| Weak dimension | Repair path |
|---|---|
| `insight_density` | Return to the topic page and rewrite current judgment; add contrast, boundary, and judgment change. |
| `problem_sharpness` | Rewrite the editorial card: reader, problem, tension, and entry scene. |
| `argument_strength` | Build or repair the argument draft; add evidence, counterpoint, and limits. |
| `originality` | Add a differentiated angle: contradiction, overlooked cause, tradeoff, or better frame. |
| `actionability` | Add steps, checklist, decision criteria, examples, or next actions. |
| `expression_quality` | Rewrite hook, paragraph rhythm, key sentences, transitions, and ending. |

## Article maturity ladder

Do not jump from idea to publication.

```text
idea_seed
→ argument_draft
→ article_draft
→ publishable_draft
→ editorial_ready
```

Minimum standards:

- `idea_seed`: reader, problem, core claim, and why-now.
- `argument_draft`: core thesis, 3-5 supporting arguments, evidence for each, counterpoint, boundary, and intended reader judgment change.
- `article_draft`: complete body with opening scene, reader problem, argument sections, examples, implication, and fact boundary.
- `publishable_draft`: edited for title, hook, rhythm, tension, examples, memorable lines, actionable ending, and publication fact checks.
- `editorial_ready`: publication-grade draft after evidence gaps and high-risk claims are resolved or explicitly bounded.

## Argument draft gate

Before upgrading an article to `publishable_draft`, check:

1. Is the core thesis explicit?
2. Are there at least three supporting argument moves?
3. Does each main argument have evidence, example, or reasoning?
4. Is there a counterpoint, misconception, tradeoff, or limitation?
5. Is the reader's expected judgment change clear?
6. Are fact boundaries and verification needs explicit?

If this gate fails, the article should not be polished longer. Fix the argument first.

## Genre-specific body shapes

Do not use one structure for all articles.

| Genre | Body shape |
|---|---|
| Problem diagnosis | scene → symptom → root cause → misconception → solution → boundary |
| Method article | situation → principle → steps → example → checklist → limits |
| Opinion/commentary | contrarian claim → reasoning → evidence → counterpoint → boundary |
| Case analysis | background → action → result/claimed result → transfer → limitation |
| Trend explanation | change → drivers → consequences → response → uncertainty |
| Tool/system article | pain point → architecture → workflow → use case → boundary |

## Calibration examples

For stable judgment, maintain calibration examples:

```text
00-system/editorial-calibration/
├── good-examples/
├── weak-examples/
├── rewritten-examples/
└── rubric-notes.md
```

Each example should explain why it is strong or weak and which revision changed the quality.

## Command

```bash
python3 scripts/kb_manager.py audit-editorial-quality --config <config> --apply
```

This command creates an editorial review report. It should not rewrite outputs by itself.
