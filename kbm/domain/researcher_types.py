"""Deprecated researcher-type compatibility facade.

New code should import :mod:`kbm.domain.research_design` and compose orthogonal
scope, source, process, output, capability, and governance dimensions.
"""

from __future__ import annotations

from typing import Any, Iterable

from kbm.domain.capabilities import CAPABILITY_CONTRACTS
from kbm.domain.research_design import (
    CORE_CAPABILITIES, LEGACY_PROFILES, LEGACY_TYPE_ALIASES, RESEARCH_PRESETS,
    ResearchDesignPlan, plan_from_legacy_profile, plan_from_legacy_type,
)


CAPABILITIES = {key: value.to_dict() for key, value in CAPABILITY_CONTRACTS.items()}
RESEARCHER_TYPES: dict[str, dict[str, Any]] = {
    legacy: {
        "name": RESEARCH_PRESETS[preset]["name"],
        "purpose": RESEARCH_PRESETS[preset]["purpose"],
        "preset": preset,
        "deprecated": True,
    }
    for legacy, preset in LEGACY_TYPE_ALIASES.items()
}
ResearcherPlan = ResearchDesignPlan


def resolve_researcher_plan(
    researcher_type: str, *, enable: Iterable[str] = (), disable: Iterable[str] = (),
) -> ResearchDesignPlan:
    return plan_from_legacy_type(researcher_type, enable=enable, disable=disable)


__all__ = [
    "CAPABILITIES", "CORE_CAPABILITIES", "LEGACY_PROFILES", "RESEARCHER_TYPES",
    "ResearcherPlan", "plan_from_legacy_profile", "resolve_researcher_plan",
]
