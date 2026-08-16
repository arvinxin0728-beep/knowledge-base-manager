# Researcher System Model

Use this reference when initializing, naming, auditing, or coordinating multiple independent researchers on one computer or across workspaces.

## Core positioning

A researcher is an independently configured research unit. It has its own:

- research domain or project scope
- source libraries
- source-intake decisions
- processing indexes and run state
- refined knowledge base
- topic pages, reusable assets, and outputs
- quality gates, health reviews, verification records, and publication handoffs

The skill package is shared. Researcher workspaces are isolated.

## What may be shared

Researchers may learn from one another at the method layer:

- reading and extraction protocols
- source-quality rubrics
- evidence-gap handling
- health-review workflows
- article maturity rubrics
- templates, checklists, and reusable research procedures
- lessons learned from closed-loop validations

Shared methods should live in a shared-methods area or in the skill package itself when they are general enough to benefit all researchers.

## What must stay isolated

Do not silently share these across researchers:

- raw source libraries
- processed-index records
- active run state
- verification ledgers
- evidence-intake candidates
- domain conclusions
- topic pages, assets, and outputs
- publication schedules

Cross-researcher knowledge transfer is allowed only through explicit import, citation, or method extraction. A researcher may cite another researcher's output as an external source, but it must be marked as such and should not count as independent primary evidence.

## Researcher design contract

A researcher is not a nominal type. Model these independent dimensions:

- identity: stable ID, name, owner, language, and isolated workspace;
- scope: theme, research questions, included/excluded boundaries, audience, and time horizon;
- sources: article, public account, ebook, video, transcript, or future adapters;
- process: active reading, synthesis, verification, role enablement, or another procedure;
- outputs: explanation, article, script, report, decision memo, SOP, or training module;
- capabilities: executable contracts derived from the selected sources, process, and outputs;
- governance: evidence, privacy, review, and publication policy.

A preset is only an editable bundle of defaults. It must not become the researcher's identity, an exclusive class, or a new implementation hierarchy. For example, an industry theme may use articles and video, perform fact verification and role enablement, then produce both a report and an SOP.

Preview before writing:

```bash
python3 scripts/kb_researcher.py presets
python3 scripts/kb_researcher.py capabilities
python3 scripts/kb_researcher.py plan-init --workspace <path> --researcher-id <id> --name <name> --theme <theme> --preset <preset> [--source <source>] [--process <process>] [--output <output>]
```

Legacy `--profile knowledge|video` and `--type` remain supported as deprecated aliases. They resolve into the same multidimensional plan and retain an explicit deprecation marker. New configs persist `research_design.schema_version: 2` and do not write `researcher.type`.

When creating a researcher, record:

```yaml
researcher:
  id:
  name:
  domain:
  role: researcher
  owner:
  language:
  shared_methods:
  allowed_cross_researcher_imports:
research_design:
  schema_version: 2
  preset: general-knowledge
  scope:
    theme:
    questions: []
    boundaries: {included: [], excluded: []}
    audience: []
    time_horizon: continuous
  sources: [article, public-account, ebook]
  process: [active-reading, topic-synthesis]
  outputs: [feynman, article]
  governance_policy: research-standard
```

Minimum rule: one researcher must have one primary `ai_knowledge_base` and one system config. Multiple researchers must not write to the same `00-system/active` files.

Legacy configs without a `researcher` object are treated as one implicit researcher in memory and remain valid without a forced file migration. New configs must write an explicit researcher identity and `pipeline.runtime_namespace`. Existing configs without `runtime_namespace` keep their historical name-based runtime path; new configs use researcher ID as the namespace. The knowledge-base path identity remains part of every local runtime path, so separate workspaces never share a pipeline database or artifact cache.

## Directory pattern

Portable default:

```text
Research-System/
├── shared-methods/
│   ├── rubrics/
│   ├── templates/
│   └── playbooks/
├── researchers/
│   ├── ai-knowledge-researcher/
│   │   ├── sources/
│   │   └── knowledge-base/
│   └── sales-researcher/
│       ├── sources/
│       └── knowledge-base/
└── registry/
    └── researchers.json
```

`researchers.json` is a registry for discovery, not a shared process state. Each researcher still owns its own config and runtime state.

## Researcher registry

Use a registry when multiple researchers exist:

```json
{
  "version": 1,
  "researchers": [
    {
      "id": "ai-knowledge-researcher",
      "name": "AI Knowledge Researcher",
      "domain": "AI knowledge management and personal research systems",
      "config": "/absolute/path/to/researchers/ai-knowledge-researcher/knowledge-base/00-system/kb-config.json",
      "status": "active"
    }
  ],
  "shared_methods": "/absolute/path/to/shared-methods"
}
```

## Operating rules

1. Select the researcher before processing sources or writing knowledge artifacts.
2. Validate the selected researcher's config before writing.
3. Keep active state and ledgers researcher-local.
4. Share methods only when they are domain-agnostic or explicitly generalized.
5. Treat another researcher's conclusion as secondary evidence unless its original sources are imported and verified.
6. When a method improvement is discovered in one researcher, update the shared skill/reference only after it has a reproducible closed loop or clear general rule.
7. Record cross-researcher imports in the receiving researcher's source refinement or evidence field.

## Preset rule

Presets may cover common starting situations such as general knowledge, publication, project decision, industry intelligence, learning, role enablement, or video content. Their names are conveniences only. Every preset expands into visible dimensions, every dimension can be extended, and custom designs require no preset.

## Completion checks

For multi-researcher work, completion requires:

- the intended researcher was selected or created;
- no files were written into another researcher's active state by accident;
- shared methods were updated only when the rule is portable;
- any cross-researcher citation or import is explicit;
- the selected researcher's quality gates pass or report the remaining warnings.
