#!/usr/bin/env python3
from __future__ import annotations

from kbm.domain.researcher_types import (
    CAPABILITIES, CORE_CAPABILITIES, plan_from_legacy_profile, resolve_researcher_plan,
)


def test_knowledge_profile_resolves_core_and_knowledge_capabilities() -> None:
    plan = plan_from_legacy_profile("knowledge")
    assert plan.researcher_type == "knowledge-researcher"
    assert set(CORE_CAPABILITIES) <= set(plan.capabilities)
    assert {"source.public-account", "source.ebook", "output.article"} <= set(plan.capabilities)
    assert plan.layout_profile == "knowledge"
    assert plan.unavailable == ()


def test_video_profile_is_content_type_with_explicit_adapter_gap() -> None:
    plan = plan_from_legacy_profile("video")
    assert plan.researcher_type == "content-researcher"
    assert {"source.video", "source.transcript", "asset.media-clip", "output.video-script"} <= set(plan.capabilities)
    assert plan.layout_profile == "video"
    assert {item["id"] for item in plan.unavailable} == {"source.video", "asset.media-clip"}


def test_custom_type_expands_dependencies() -> None:
    plan = resolve_researcher_plan("project-researcher", enable=["integration.obsidian"])
    assert "research.fact-verification" in plan.capabilities
    assert "core.quality-gates" in plan.capabilities
    assert "integration.obsidian" in plan.capabilities


def test_core_capability_cannot_be_disabled() -> None:
    try:
        resolve_researcher_plan("knowledge-researcher", disable=["core.identity"])
    except ValueError as exc:
        assert "cannot_disable_core_capability" in str(exc)
    else:
        raise AssertionError("core capability disable should fail")


def test_enterprise_connectors_are_generic_instance_only_adapters() -> None:
    plan = resolve_researcher_plan(
        "industry-researcher", enable=["integration.dingtalk", "integration.feishu"]
    )
    assert {item["id"] for item in plan.unavailable} == {"integration.dingtalk", "integration.feishu"}
    assert CAPABILITIES["integration.dingtalk"]["config_scope"] == "instance_only"
    assert CAPABILITIES["integration.feishu"]["config_scope"] == "instance_only"
