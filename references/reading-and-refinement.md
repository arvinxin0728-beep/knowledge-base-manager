# Reading and Refinement Module

Use this reference when processing books, ebooks, public-account posts, web articles, newsletters, blog posts, Markdown, TXT, HTML, DOCX, EPUB, PDF, or copied article text.

This module is part of the single installed package and provides the reading, refinement, synthesis, and durable-note workflow.

## Source Handling

Only process material the user supplied, made accessible, or has permission to process. Do not bypass paywalls, login walls, anti-bot controls, private accounts, or access restrictions.

For WeChat/公众号 and similar platforms, prefer user-supplied exports, copied text, saved HTML/PDF, screenshots with OCR, or accessible article URLs.

Do not provide long verbatim excerpts from copyrighted books or articles. Summarize and quote only brief passages when analytically necessary.

## Extraction

For supported local files, use:

```bash
python3 scripts/ebook_probe.py <source-file> --out-dir <work-dir>
```

The script creates:

- `manifest.json`: title, format, text stats, candidate chapters, output paths
- `chunks.jsonl`: ordered chunks
- `full_text.txt`: normalized extracted text

Supported directly: `.txt`, `.md`, `.markdown`, `.html`, `.htm`, `.docx`, `.epub`. PDF is supported when local PDF libraries are available. For scanned PDFs or image-only captures, OCR is required before synthesis.

## Active Reading Questions

Carry these questions through every durable note:

1. What is the material about as a whole?
2. What does the author say in detail, and how?
3. Is it true, sound, or persuasive, in whole or in part?
4. What follows for the reader?

## Reading Levels

### Inspectional Reading

Use before deep synthesis:

- inspect title, subtitle, preface, table of contents, headings, introduction, conclusion, and representative chunks
- classify the material type
- identify the central problem
- decide whether the source needs quick extraction, full analysis, or cross-source synthesis

### Analytical Reading

For one important source:

1. Classify the source.
2. State the whole source in a few sentences.
3. Outline major parts and relationships.
4. Identify the author's questions or problems.
5. Define important terms.
6. Extract key propositions.
7. Reconstruct the argument chain.
8. Identify proposed solutions or actions.
9. Critique only after understanding.
10. Specify whether disagreement concerns missing knowledge, factual error, invalid reasoning, or incomplete analysis.

### Syntopical Reading

For multiple sources around a topic:

1. Inspect all candidate sources and locate relevant passages.
2. Build neutral terminology instead of adopting one source's vocabulary.
3. Formulate shared questions.
4. Map agreement, disagreement, omissions, and redefinitions.
5. Build a topic page around the question, not around one source.

## Genre Adjustments

- Practical: extract goals, rules, actions, conditions, and application limits.
- Theoretical: extract concepts, propositions, arguments, evidence, and truth claims.
- History: preserve chronology, actors, causes, source selection, and interpretation.
- Science/math: preserve definitions, assumptions, experiments, evidence, formulas, and proof limits.
- Philosophy: preserve questions, distinctions, first principles, objections, and reasoning.
- Social science: separate empirical claims, concepts, values, methods, and policy implications.
- Public-account articles/web essays: identify hook, claim, evidence, examples, persuasion strategy, omitted context, practical takeaway, and fact-check needs.

## Source Refinement Template

```markdown
# Source title

---
source_type:
source_file:
account:
author:
published_at:
saved_at:
url:
processed_at:
stage: 来源精炼
status: processed
---

## 一句话价值
## 文章/书籍解决的问题
## 核心观点
## 可复用模型
## 可复用案例
## 金句/表达候选
## 框架图谱候选
## 输出候选
## 复盘触发
## 存疑点 / 使用边界
## 可连接主题
## 候选提升
```

Use metadata fields when available; omit unknown fields rather than inventing them.

## Durable Output Schema

When asked for durable book/source knowledge, include as relevant:

1. Bibliographic snapshot
2. Core thesis
3. Audience
4. Chapter or section map
5. Four active-reading questions
6. Key ideas
7. Concepts and definitions
8. Argument chain
9. Evidence, examples, and cases
10. Methods, frameworks, or models
11. Practical applications
12. Critique and open questions
13. Knowledge cards
14. Tags and related topics

## Knowledge Cards

Use JSONL when useful:

```json
{"id":"card-001","type":"concept","front":"What is ...?","back":"...","source":"chapter-02","tags":["topic"]}
```

Recommended `type`: `concept`, `claim`, `contrast`, `process`, `example`, `quote-context`, `application`, `critique`.

## Asset and Output Capture

When a source contains reusable material, capture it at refinement time so it can be promoted later:

- Expression candidates: compact definitions, sharp distinctions, useful metaphors, memorable warnings, or reusable phrasing. Keep the source boundary and avoid long quotes.
- Framework-map candidates: processes, layers, causal chains, role relationships, feedback loops, or decision trees.
- Case candidates: background, action, result, limitation, and transferable lesson.
- Output candidates: a clear reader, question, claim, or use scenario that could become an explanation, article, solution material, or decision memo.
- Review triggers: evidence that the knowledge-base process itself should be reviewed, such as repeated low-quality outputs, duplicated themes, weak links, or source batches that did not change judgments.

Use `asset-output-matrix.md` when deciding whether these candidates should become files under reusable assets or outputs.
