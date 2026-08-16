#!/usr/bin/env python3
from __future__ import annotations

from kbm.domain.capabilities import (
    CAPABILITY_CONTRACTS, dependency_order, execution_plan, validate_capability_catalog,
)


def test_every_capability_has_a_valid_execution_contract() -> None:
    assert validate_capability_catalog() == []
    for contract in CAPABILITY_CONTRACTS.values():
        assert contract.entrypoint
        assert contract.inputs
        assert contract.outputs
        assert contract.execution_mode in {"builtin", "instruction", "adapter"}


def test_dependency_order_places_requirements_before_consumers() -> None:
    ordered = dependency_order({
        "core.identity", "core.source-traceability", "research.active-reading",
        "research.topic-synthesis", "output.article",
    })
    assert ordered.index("core.identity") < ordered.index("core.source-traceability")
    assert ordered.index("research.active-reading") < ordered.index("research.topic-synthesis")
    assert ordered.index("research.topic-synthesis") < ordered.index("output.article")


def test_adapter_contract_is_blocked_without_embedding_instance_configuration() -> None:
    steps = execution_plan({"core.identity", "core.workspace-isolation", "integration.dingtalk"})
    connector = next(step for step in steps if step["id"] == "integration.dingtalk")
    assert connector["status"] == "blocked_adapter_required"
    assert connector["config_scope"] == "instance_only"
    assert connector["entrypoint"] == "adapter:enterprise-docs"
    assert connector["required_config"] == (
        "connectors.dingtalk.adapter", "connectors.dingtalk.secret_ref"
    )
    assert not any(key in connector for key in ("node_id", "mcp_id", "server_url", "token"))


def test_builtin_and_instruction_entrypoints_exist_in_skill_package() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    for contract in CAPABILITY_CONTRACTS.values():
        if contract.execution_mode == "adapter" or contract.entrypoint.startswith("kbm."):
            continue
        relative = contract.entrypoint.split(":", 1)[0]
        assert (root / relative).is_file(), contract.id


if __name__ == "__main__":
    test_every_capability_has_a_valid_execution_contract()
    test_dependency_order_places_requirements_before_consumers()
    test_adapter_contract_is_blocked_without_embedding_instance_configuration()
    test_builtin_and_instruction_entrypoints_exist_in_skill_package()
    print("ok")
