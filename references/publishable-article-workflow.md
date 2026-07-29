# Publishable Article Workflow

Use this reference when upgrading a `40-outputs` article from `article_draft` to `publishable_draft`.

## Entry gate

Only upgrade an article when:

- `output_type: "文章草稿"` is present.
- `article_maturity` is `article_draft`.
- The article has a source theme or topic page.
- The user explicitly asks for publication-level polishing, or the article is an approved output candidate.

If the article is still `article_seed`, expand it to `article_draft` first. Do not skip directly from seed to publishable.

## Required frontmatter

Add or update:

- `article_maturity: "publishable_draft"`
- `publish_status: "ready_for_editorial_review"` unless the user explicitly asks for public release.
- `publish_angle`: the core public-facing angle in one sentence.
- `hook_type`: one of `problem`, `story`, `contrarian`, `checklist`, `case`, `trend`.

Keep `fact_check_required: true` when claims depend on public-account articles, product capability descriptions, company events, report claims, market data, rankings, or numbers.

Keep Obsidian Properties compact. Do not put long publication planning lists in frontmatter. The following items must live in body sections instead of YAML:

- `## 标题候选`: 3-5 candidate titles.
- `## 发布编辑卡片`: compact editorial planning section with four clear subparts:
  - `### 文章体裁`: one of the approved article genres below; choose by argument need, not by convenience.
  - `### 选题切口`: the article's entry angle, hook logic, conflict, or contrast; do not repeat the thesis verbatim.
  - `### 目标读者`: who is reading and what task, confusion, or decision situation they are in.
  - `### 核心论断`: the article's thesis in one short paragraph; do not duplicate it again as a separate `## 核心观点`.
  - `### 关键证据/素材`: 2-4 concrete scenes, examples, cases, methods, or evidence used in the body; phrase them as reusable writing materials, not generic audience context.
- `## 可复用金句`: 5-8 reusable lines from the article.
- `## 发布前核查`: concrete claims that must be verified before external publishing.

## Approved article genres

Do not use one body template for every article. A publishable article must select a genre and make the body structure match that genre. Use these genre patterns as disciplined editorial forms, not decorative headings.

### 问题—原因—解法型

Use for diagnostic articles that explain why something keeps failing and what to do instead.

Required body moves:

1. Problem scene: show the observable failure.
2. Surface causes: name common explanations.
3. Deeper mechanism: explain the real cause.
4. Why old approaches fail: show why intuitive fixes do not work.
5. Better model or solution: present the replacement frame.
6. Action guidance: give a next step, checklist, or decision rule.
7. Boundary: state when the argument may not apply.

### 观点论证型

Use for articles centered on a clear claim that must be proven.

Required body moves:

1. Claim: state the arguable thesis.
2. Evidence: provide concrete sources, examples, or cases.
3. Reasoning: explain why the evidence supports the claim.
4. Counterargument: acknowledge a plausible opposing view.
5. Response: show why the thesis still holds, or narrow it.
6. Implication: explain what changes if the reader accepts the claim.
7. Boundary: mark uncertainty and fact-check needs.

### 方法教学型

Use for workflow, how-to, or operating-method articles.

Required body moves:

1. Use case: define when the method is needed.
2. Preconditions: state what must be ready before starting.
3. Steps: give ordered actions, not vague principles.
4. Example: show the method in a realistic situation.
5. Common mistakes: warn against predictable misuse.
6. Quality check: tell the reader how to judge whether it worked.
7. Boundary: state where the method should be adapted.

### 案例分析型

Use for company, product, project, customer, or personal practice cases.

Required body moves:

1. Case background: describe context and stakes.
2. Core conflict: name the tension or decision.
3. Key actions: explain what was done.
4. Result: describe outcome or observed consequence.
5. Mechanism: explain why the result happened.
6. Transferable principle: extract what others can reuse.
7. Boundary: state what may not transfer.

### 比较辨析型

Use for clarifying two concepts, models, roles, tools, or approaches that are often confused.

Required body moves:

1. Common confusion: show why readers mix them up.
2. Define A.
3. Define B.
4. Key differences: compare on dimensions that matter.
5. Misuse consequences: show what goes wrong if confused.
6. Selection rule: tell readers how to choose.
7. Boundary: state overlap or hybrid cases.

### 经营/管理分析型

Use for organizational, business, management, transformation, or governance arguments.

Required body moves:

1. Misdiagnosis: identify the common management mistake.
2. Business objective: clarify what result actually matters.
3. Process/mechanism: show how work must change.
4. Organization/accountability: explain roles, incentives, and responsibility.
5. Metrics/governance: define how to measure and control progress.
6. Practical starting point: give a low-risk first move.
7. Boundary: state organization size, maturity, or scenario limits.

## Anti-fluff gate

Before marking an article as `publishable_draft`, check the body against these rules:

- Every major section must make a distinct argumentative move; do not repeat the same point with different wording.
- Every major claim must include at least one of: concrete scene, evidence, case, mechanism, counterexample, or operational consequence.
- The article must contain a real tension, counterargument, misconception, or boundary; pure agreement and inspirational phrasing are not enough.
- `关键证据/素材` must be used in the body. If a listed item never appears in the body, remove it or revise the body.
- The ending must change the reader's next action, decision rule, or diagnostic lens.
- Avoid generic phrases such as "很重要", "赋能", "提升效率", or "形成闭环" unless followed by a concrete mechanism.

## Rewrite sequence

1. Clarify the publishing angle.
2. Generate 3-5 title candidates. Keep the H1 as the selected title, not the filename date prefix.
3. Select `### 文章体裁` from the approved genre list and use that genre's required body moves.
4. Add `## 发布编辑卡片` with `### 文章体裁`, `### 选题切口`, `### 目标读者`, `### 核心论断`, and `### 关键证据/素材`; keep these boundaries non-overlapping. `选题切口` is the opening angle, `目标读者` is the reader's situation, `核心论断` is the thesis, and `关键证据/素材` is body material.
5. Rewrite the opening with a concrete scene, contradiction, or reader problem.
6. Build a visible argument spine according to the selected genre, not a generic listicle.
7. Add at least 4 argument sections.
8. Add at least 2 concrete scenes, cases, examples, or evidence items.
9. Add a counterpoint, misconception, or tension section.
10. Add 5-8 memorable lines. They may appear in body text and also in a `## 可复用金句` section.
11. Add an actionable ending: checklist, next step, decision rule, or diagnostic questions.
12. Add `## 发布前核查` with specific fact-check items.
13. Preserve `## 事实边界` and `## 关联知识`.

## Body shape

Recommended section order:

```markdown
# Selected publishable title

## 标题候选
## 发布编辑卡片
### 文章体裁
### 选题切口
### 目标读者
### 核心论断
### 关键证据/素材
## 正文草稿
### Opening hook
### Argument section 1
### Argument section 2
### Argument section 3
### Argument section 4
### Counterpoint / misconception
### Actionable ending
## 可复用金句
## 发布前核查
## 事实边界
## 来源主题
## 关联知识
```

The final body may use Chinese section titles, but avoid keeping old front sections such as `## 场景`, `## 读者问题`, or a separate `## 核心观点` when their content is already represented inside the editorial card. Keep `## 来源主题` near the end with traceability sections, not before the article body.

## Publishable quality gate

A `publishable_draft` should satisfy:

- Main article body has at least 2500 Chinese characters.
- A declared article genre under `### 文章体裁`, selected from the approved genre list.
- Body sections match the selected genre's required moves.
- 4 or more argument sections.
- Strong opening hook.
- Clear reader problem.
- At least 2 concrete scenes, examples, or cases.
- At least one counterpoint, misconception, or tension.
- 5-8 memorable lines.
- Actionable ending.
- Specific publication fact-check list.
- Fact boundary and evidence boundary.
- No local path, private folder code, or implementation-specific directory name in the main methodology body unless marked as an implementation example.

## Review result

After rewriting, run:

```bash
python3 scripts/kb_manager.py evaluate-outputs --config <kb-config> --apply
python3 scripts/kb_manager.py record-output-review --config <kb-config> --file "<relative-file>" --status usable --scores '{"argument_clarity":5,"evidence_strength":4,"portability":5,"scope_control":4,"actionability":5,"reuse_value":5}' --note "publishable_draft review..." --apply-status
python3 scripts/kb_manager.py quality-gate --config <kb-config> --apply --strict
```

If external publication is intended, verify or downgrade risky claims before release. `publishable_draft` means editorially publishable after fact verification, not automatically fact-verified.
