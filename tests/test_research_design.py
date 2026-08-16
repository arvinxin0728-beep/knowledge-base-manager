#!/usr/bin/env python3
from __future__ import annotations

from kbm.domain.research_design import plan_from_legacy_type, resolve_research_design


def test_dimensions_are_orthogonal_and_composable() -> None:
    plan = resolve_research_design(
        preset="industry-intelligence", theme="restaurant SaaS",
        sources=["video"], process=["role-enablement"],
        outputs=["decision-memo", "operations-sop"], audience=["sales"],
    )
    assert plan.layout_profile == "mixed"
    assert {"article", "video"} <= set(plan.sources)
    assert {"fact-verification", "role-enablement"} <= set(plan.process)
    assert {"research-report", "decision-memo", "operations-sop"} <= set(plan.outputs)
    assert plan.design_dict()["scope"]["audience"] == ["sales"]
    assert "researcher_type" not in plan.to_dict()


def test_custom_design_requires_no_nominal_type() -> None:
    plan = resolve_research_design(
        theme="custom", sources=["article"], process=["active-reading"], outputs=["feynman"]
    )
    assert plan.preset is None
    assert plan.researcher_type == "custom"
    assert {"source.article", "research.active-reading", "output.feynman"} <= set(plan.capabilities)


def test_legacy_type_is_an_explicit_deprecated_alias() -> None:
    plan = plan_from_legacy_type("industry-researcher", theme="legacy")
    assert plan.preset == "industry-intelligence"
    assert plan.to_dict()["deprecated_type_alias"] is True
    assert plan.to_dict()["researcher_type"] == "industry-researcher"
