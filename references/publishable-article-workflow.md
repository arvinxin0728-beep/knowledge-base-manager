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
- `title_candidates`: 3-5 candidate titles.
- `key_scenes`: 2-4 concrete scenes or examples used in the body.
- `memorable_lines`: 5-8 reusable lines from the article.
- `fact_check_items`: concrete claims that must be verified before external publishing.

Keep `fact_check_required: true` when claims depend on public-account articles, product capability descriptions, company events, report claims, market data, rankings, or numbers.

## Rewrite sequence

1. Clarify the publishing angle.
2. Generate 3-5 title candidates. Keep the H1 as the selected title, not the filename date prefix.
3. Rewrite the opening with a concrete scene, contradiction, or reader problem.
4. Build a visible argument spine: problem -> diagnosis -> deeper cause -> better model -> action.
5. Add at least 4 argument sections.
6. Add at least 2 concrete scenes, cases, or examples.
7. Add a counterpoint, misconception, or tension section.
8. Add 5-8 memorable lines. They may appear in body text and also in a `## 可复用金句` section.
9. Add an actionable ending: checklist, next step, decision rule, or diagnostic questions.
10. Add `## 发布前核查` with specific fact-check items.
11. Preserve `## 事实边界` and `## 关联知识`.

## Body shape

Recommended section order:

```markdown
# Selected publishable title

## 标题候选
## 发布角度
## 场景
## 核心观点
## 读者问题
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
## 关联知识
```

The final body may use Chinese section titles. The section names are less important than preserving the functions.

## Publishable quality gate

A `publishable_draft` should satisfy:

- Main article body has at least 2500 Chinese characters.
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
