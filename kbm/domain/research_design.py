"""Orthogonal researcher design dimensions with optional starter presets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from kbm.domain.capabilities import CAPABILITY_CONTRACTS, execution_plan


CORE_CAPABILITIES = (
    "core.identity", "core.workspace-isolation", "core.transactional-pipeline",
    "core.source-traceability", "core.quality-gates",
)

SOURCE_OPTIONS = {
    "article": "source.article",
    "public-account": "source.public-account",
    "ebook": "source.ebook",
    "video": "source.video",
    "transcript": "source.transcript",
}

PROCESS_OPTIONS = {
    "active-reading": "research.active-reading",
    "topic-synthesis": "research.topic-synthesis",
    "fact-verification": "research.fact-verification",
    "role-enablement": "research.role-enablement",
}

OUTPUT_OPTIONS = {
    "feynman": "output.feynman",
    "article": "output.article",
    "video-script": "output.video-script",
    "research-report": "output.research-report",
    "decision-memo": "output.decision-memo",
    "operations-sop": "output.operations-sop",
    "training-module": "output.training-module",
}

RESEARCH_PRESETS: dict[str, dict[str, Any]] = {
    "general-knowledge": {
        "name": "通用知识研究方案", "purpose": "长期积累、综合和输出一个主题的知识",
        "sources": ("article", "public-account", "ebook"),
        "process": ("active-reading", "topic-synthesis"),
        "outputs": ("feynman", "article"),
        "capabilities": ("asset.method", "asset.case", "asset.expression", "asset.framework", "integration.obsidian"),
        "governance_policy": "research-standard",
    },
    "content-publication": {
        "name": "内容出版研究方案", "purpose": "把研究证据转化为可发布内容",
        "sources": ("article",), "process": ("active-reading", "topic-synthesis"),
        "outputs": ("article", "video-script"),
        "capabilities": ("asset.case", "asset.expression"),
        "governance_policy": "publication-standard",
    },
    "project-decision": {
        "name": "项目决策研究方案", "purpose": "支持有期限的项目和决策",
        "sources": ("article",), "process": ("active-reading", "topic-synthesis", "fact-verification"),
        "outputs": ("research-report", "decision-memo"), "capabilities": (),
        "governance_policy": "research-standard",
    },
    "industry-intelligence": {
        "name": "行业研究方案", "purpose": "持续研究行业、公司、案例和趋势",
        "sources": ("article",), "process": ("active-reading", "topic-synthesis", "fact-verification"),
        "outputs": ("research-report",), "capabilities": ("asset.case", "asset.framework"),
        "governance_policy": "evidence-strict",
    },
    "learning": {
        "name": "学习研究方案", "purpose": "学习课程、书籍或稳定学科",
        "sources": ("ebook",), "process": ("active-reading", "topic-synthesis"),
        "outputs": ("feynman",), "capabilities": (), "governance_policy": "learning-light",
    },
    "role-enablement": {
        "name": "岗位赋能研究方案", "purpose": "把业务与产品知识转化为面向角色的可执行知识",
        "sources": ("article",),
        "process": ("active-reading", "topic-synthesis", "fact-verification", "role-enablement"),
        "outputs": ("operations-sop", "training-module"),
        "capabilities": ("asset.product-knowledge-card",), "governance_policy": "evidence-strict",
    },
    "video-content": {
        "name": "视频内容研究方案", "purpose": "以视频和转录为来源开展内容研究",
        "sources": ("video", "transcript"), "process": ("active-reading", "topic-synthesis"),
        "outputs": ("video-script",), "capabilities": ("asset.media-clip",),
        "governance_policy": "publication-standard",
    },
}

LEGACY_TYPE_ALIASES = {
    "knowledge-researcher": "general-knowledge",
    "content-researcher": "content-publication",
    "project-researcher": "project-decision",
    "industry-researcher": "industry-intelligence",
    "learning-researcher": "learning",
    "enablement-researcher": "role-enablement",
}

LEGACY_PROFILES = {
    "knowledge": {"preset": "general-knowledge", "legacy_type": "knowledge-researcher"},
    "video": {"preset": "video-content", "legacy_type": "content-researcher"},
}


@dataclass(frozen=True)
class ResearchDesignPlan:
    preset: str | None
    theme: str
    questions: tuple[str, ...]
    boundaries_in: tuple[str, ...]
    boundaries_out: tuple[str, ...]
    audience: tuple[str, ...]
    time_horizon: str
    sources: tuple[str, ...]
    process: tuple[str, ...]
    outputs: tuple[str, ...]
    capabilities: tuple[str, ...]
    unavailable: tuple[dict[str, str], ...]
    governance_policy: str
    layout_profile: str
    execution_steps: tuple[dict[str, Any], ...]
    legacy_type: str | None = None

    @property
    def researcher_type(self) -> str:
        """Deprecated compatibility surface."""
        return self.legacy_type or self.preset or "custom"

    def design_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 2,
            "preset": self.preset,
            "scope": {
                "theme": self.theme, "questions": list(self.questions),
                "boundaries": {"included": list(self.boundaries_in), "excluded": list(self.boundaries_out)},
                "audience": list(self.audience), "time_horizon": self.time_horizon,
            },
            "sources": list(self.sources), "process": list(self.process),
            "outputs": list(self.outputs), "governance_policy": self.governance_policy,
        }

    def to_dict(self) -> dict[str, Any]:
        value = {
            "preset": self.preset, "research_design": self.design_dict(),
            "capabilities": list(self.capabilities), "unavailable": list(self.unavailable),
            "governance_policy": self.governance_policy, "layout_profile": self.layout_profile,
            "execution_steps": list(self.execution_steps),
        }
        if self.legacy_type:
            value["researcher_type"] = self.legacy_type
            value["deprecated_type_alias"] = True
        return value


def _option_capabilities(values: Iterable[str], catalog: dict[str, str], dimension: str) -> set[str]:
    capabilities: set[str] = set()
    for value in values:
        if value not in catalog:
            raise ValueError(f"unknown_{dimension}:{value}")
        capabilities.add(catalog[value])
    return capabilities


def _expand_dependencies(selected: Iterable[str]) -> set[str]:
    resolved = set(CORE_CAPABILITIES)
    pending = list(selected)
    while pending:
        capability = pending.pop()
        if capability not in CAPABILITY_CONTRACTS:
            raise ValueError(f"unknown_capability:{capability}")
        if capability in resolved:
            continue
        resolved.add(capability)
        pending.extend(CAPABILITY_CONTRACTS[capability].requires)
    return resolved


def resolve_research_design(
    *, preset: str | None = None, theme: str = "", questions: Iterable[str] = (),
    boundaries_in: Iterable[str] = (), boundaries_out: Iterable[str] = (),
    audience: Iterable[str] = (), time_horizon: str = "continuous",
    sources: Iterable[str] = (), process: Iterable[str] = (), outputs: Iterable[str] = (),
    enable: Iterable[str] = (), disable: Iterable[str] = (), legacy_type: str | None = None,
) -> ResearchDesignPlan:
    if preset is not None and preset not in RESEARCH_PRESETS:
        raise ValueError(f"unknown_research_preset:{preset}")
    base = RESEARCH_PRESETS.get(preset, {})
    resolved_sources = tuple(dict.fromkeys((*base.get("sources", ()), *sources)))
    resolved_process = tuple(dict.fromkeys((*base.get("process", ()), *process)))
    resolved_outputs = tuple(dict.fromkeys((*base.get("outputs", ()), *outputs)))
    selected = set(base.get("capabilities", ())) | set(enable)
    selected |= _option_capabilities(resolved_sources, SOURCE_OPTIONS, "source")
    selected |= _option_capabilities(resolved_process, PROCESS_OPTIONS, "process")
    selected |= _option_capabilities(resolved_outputs, OUTPUT_OPTIONS, "output")
    disabled = set(disable)
    illegal = disabled & set(CORE_CAPABILITIES)
    if illegal:
        raise ValueError(f"cannot_disable_core_capability:{','.join(sorted(illegal))}")
    selected -= disabled
    capabilities = _expand_dependencies(selected)
    required = {dependency for item in capabilities for dependency in CAPABILITY_CONTRACTS[item].requires}
    conflicts = disabled & required
    if conflicts:
        raise ValueError(f"disabled_required_capability:{','.join(sorted(conflicts))}")
    unavailable = tuple(
        {"id": item, "status": CAPABILITY_CONTRACTS[item].availability}
        for item in sorted(capabilities) if CAPABILITY_CONTRACTS[item].availability != "available"
    )
    governance = str(base.get("governance_policy", "research-standard"))
    has_video = "video" in resolved_sources or "source.video" in capabilities
    has_knowledge = bool(set(resolved_sources) & {"article", "public-account", "ebook"})
    layout = "mixed" if has_video and has_knowledge else "video" if has_video else "knowledge"
    return ResearchDesignPlan(
        preset=preset, theme=theme, questions=tuple(questions), boundaries_in=tuple(boundaries_in),
        boundaries_out=tuple(boundaries_out), audience=tuple(audience), time_horizon=time_horizon,
        sources=resolved_sources, process=resolved_process, outputs=resolved_outputs,
        capabilities=tuple(sorted(capabilities)), unavailable=unavailable,
        governance_policy=governance,
        layout_profile=layout,
        execution_steps=execution_plan(capabilities), legacy_type=legacy_type,
    )


def plan_from_legacy_type(researcher_type: str, **kwargs: Any) -> ResearchDesignPlan:
    if researcher_type not in LEGACY_TYPE_ALIASES:
        raise ValueError(f"unknown_legacy_researcher_type:{researcher_type}")
    return resolve_research_design(
        preset=LEGACY_TYPE_ALIASES[researcher_type], legacy_type=researcher_type, **kwargs
    )


def plan_from_legacy_profile(profile: str, **kwargs: Any) -> ResearchDesignPlan:
    if profile not in LEGACY_PROFILES:
        raise ValueError(f"unknown_legacy_profile:{profile}")
    mapping = LEGACY_PROFILES[profile]
    return resolve_research_design(
        preset=mapping["preset"], legacy_type=mapping["legacy_type"], **kwargs,
    )
