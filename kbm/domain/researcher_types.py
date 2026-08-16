"""Composable researcher types, capabilities, and initialization plans."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from kbm.domain.capabilities import CAPABILITY_CONTRACTS, execution_plan, validate_capability_catalog


CORE_CAPABILITIES = (
    "core.identity", "core.workspace-isolation", "core.transactional-pipeline",
    "core.source-traceability", "core.quality-gates",
)

CAPABILITIES: dict[str, dict[str, Any]] = {
    capability_id: contract.to_dict()
    for capability_id, contract in CAPABILITY_CONTRACTS.items()
}

RESEARCHER_TYPES: dict[str, dict[str, Any]] = {
    "knowledge-researcher": {
        "name": "知识研究员", "purpose": "长期积累、综合和输出领域知识",
        "capabilities": ["source.public-account", "source.ebook", "research.active-reading", "research.topic-synthesis", "asset.method", "asset.case", "asset.expression", "asset.framework", "output.feynman", "output.article", "integration.obsidian"],
        "governance_policy": "research-standard",
    },
    "content-researcher": {
        "name": "内容研究员", "purpose": "把多种来源转化为可发布内容",
        "capabilities": ["research.active-reading", "research.topic-synthesis", "asset.case", "asset.expression", "output.article", "output.video-script"],
        "governance_policy": "publication-standard",
    },
    "project-researcher": {
        "name": "项目研究员", "purpose": "支持有期限的项目和决策",
        "capabilities": ["research.active-reading", "research.topic-synthesis", "research.fact-verification", "output.research-report", "output.decision-memo"],
        "governance_policy": "research-standard",
    },
    "industry-researcher": {
        "name": "行业研究员", "purpose": "持续跟踪行业、公司、案例和趋势",
        "capabilities": ["research.active-reading", "research.topic-synthesis", "research.fact-verification", "asset.case", "asset.framework", "output.research-report"],
        "governance_policy": "evidence-strict",
    },
    "learning-researcher": {
        "name": "学习研究员", "purpose": "学习课程、书籍或一个稳定学科",
        "capabilities": ["source.ebook", "research.active-reading", "research.topic-synthesis", "output.feynman"],
        "governance_policy": "learning-light",
    },
}

LEGACY_PROFILES = {
    "knowledge": {"type": "knowledge-researcher", "enable": []},
    "video": {"type": "content-researcher", "enable": ["source.video", "source.transcript", "asset.media-clip"]},
}


@dataclass(frozen=True)
class ResearcherPlan:
    researcher_type: str
    capabilities: tuple[str, ...]
    unavailable: tuple[dict[str, str], ...]
    governance_policy: str
    layout_profile: str
    execution_steps: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "researcher_type": self.researcher_type,
            "capabilities": list(self.capabilities),
            "unavailable": list(self.unavailable),
            "governance_policy": self.governance_policy,
            "layout_profile": self.layout_profile,
            "execution_steps": list(self.execution_steps),
        }


def _expand_dependencies(selected: Iterable[str]) -> set[str]:
    resolved = set(CORE_CAPABILITIES)
    pending = list(selected)
    while pending:
        capability = pending.pop()
        if capability not in CAPABILITIES:
            raise ValueError(f"unknown_capability:{capability}")
        if capability in resolved:
            continue
        resolved.add(capability)
        pending.extend(CAPABILITIES[capability].get("requires", []))
    return resolved


def resolve_researcher_plan(
    researcher_type: str,
    *,
    enable: Iterable[str] = (),
    disable: Iterable[str] = (),
) -> ResearcherPlan:
    catalog_errors = validate_capability_catalog()
    if catalog_errors:
        raise ValueError(f"invalid_capability_catalog:{','.join(catalog_errors)}")
    if researcher_type not in RESEARCHER_TYPES:
        raise ValueError(f"unknown_researcher_type:{researcher_type}")
    definition = RESEARCHER_TYPES[researcher_type]
    selected = set(definition["capabilities"]) | set(enable)
    disabled = set(disable)
    protected = set(CORE_CAPABILITIES)
    illegal = disabled & protected
    if illegal:
        raise ValueError(f"cannot_disable_core_capability:{','.join(sorted(illegal))}")
    selected -= disabled
    resolved = _expand_dependencies(selected)
    required_by_enabled = {
        required for capability in resolved for required in CAPABILITIES[capability].get("requires", [])
    }
    conflicts = disabled & required_by_enabled
    if conflicts:
        raise ValueError(f"disabled_required_capability:{','.join(sorted(conflicts))}")
    unavailable = tuple(
        {"id": capability, "status": str(CAPABILITIES[capability]["availability"])}
        for capability in sorted(resolved)
        if CAPABILITIES[capability]["availability"] != "available"
    )
    return ResearcherPlan(
        researcher_type=researcher_type,
        capabilities=tuple(sorted(resolved)),
        unavailable=unavailable,
        governance_policy=str(definition["governance_policy"]),
        layout_profile="video" if "source.video" in resolved else "knowledge",
        execution_steps=execution_plan(resolved),
    )


def plan_from_legacy_profile(profile: str) -> ResearcherPlan:
    if profile not in LEGACY_PROFILES:
        raise ValueError(f"unknown_legacy_profile:{profile}")
    mapping = LEGACY_PROFILES[profile]
    return resolve_researcher_plan(mapping["type"], enable=mapping["enable"])
