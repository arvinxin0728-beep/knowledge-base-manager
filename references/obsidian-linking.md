# Obsidian Linking Rules

Use this reference when writing or updating files under source refinements, topic pages, reusable assets, or outputs for an Obsidian-based knowledge base.

## Required Metadata

Every `10-source-refinements`, `20-topic-pages`, `30-reusable-assets`, and `40-outputs` file should start with YAML frontmatter. The title must come after the frontmatter.

Required fields:

- `stage`
- `theme_cluster`
- `tags`
- `related_sources`
- `related_topics`
- `related_assets`
- `related_outputs`
- `moc`
- `obsidian_links_updated`

## Link Discipline

- Use tags for stable classification only; keep 3-6 tags per file.
- Use wikilinks for real reusable objects, not every noun.
- Wikilink targets must resolve to existing file stems in the vault. When a readable title differs from the file stem, use `[[FileStem|Readable Title]]`.
- Do not write links such as `[[Readable Title With Spaces]]` when the actual file is named without spaces; that creates empty Obsidian pages.
- Source links should prefer the source-refinement note file under `10-source-refinements`, not the raw source path.
- If a source index row has no generated source-refinement note yet, do not create a wikilink to the raw title; leave it as plain text or omit it from relationship fields until a real note exists.
- Source refinements should link upward to related topic pages, reusable assets, outputs, and MOC; avoid source-to-source bulk linking.
- Topic pages should link upstream sources, related topic pages, reusable assets, and outputs.
- Assets must link back to their source topic page or MOC.
- Outputs must link back to their source topic page and used assets.
- High-risk or unverified material should use `待核查` as a status tag when appropriate.

## Command

Run:

```bash
python3 scripts/obsidian_linker.py --config <kb-config> --apply
```

When an existing knowledge base has many conceptual wikilinks that do not resolve to real files, run:

```bash
python3 scripts/obsidian_linker.py --config <kb-config> --apply --unlink-unresolved
```

This preserves links to real files and converts unresolved concept links into plain text so Obsidian does not create empty pages.

The command normalizes Obsidian frontmatter placement, adds relationship fields, appends or replaces a `## 关联知识` section, and creates MOC pages for configured clusters. It covers `10/20/30/40` files, but MOC pages aggregate only `20/30/40` durable synthesis and output objects.

The command must canonicalize existing wikilinks when an unambiguous file match exists. If a link cannot be resolved, leave it unchanged and report it through relation audit instead of silently inventing a target.

## MOC Pages

MOC pages are navigation hubs, not synthesis pages. They should aggregate topic pages, reusable assets, and outputs by `theme_cluster`.

Keep MOC pages in the configured MOC subfolder under topic pages, for example `20-topic-pages/moc/` or `20-主题页/MOC/`. Keep normal synthesized topic pages in the configured pages subfolder, for example `20-topic-pages/pages/` or `20-主题页/主题页/`.

This folder split is a type boundary, not a methodology boundary:

- topic pages answer a concrete cross-source question;
- MOC pages help Obsidian users navigate related topic pages, assets, and outputs.
