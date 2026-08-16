#!/usr/bin/env python3
from __future__ import annotations

from kbm.application.adapter_readiness import resolve_instance_execution


CAPABILITIES = {"core.identity", "core.workspace-isolation", "integration.dingtalk"}


def test_missing_adapter_configuration_is_redacted_and_blocked() -> None:
    result = resolve_instance_execution(CAPABILITIES, {}, available_adapters={"enterprise-docs"})
    assert result["ready"] is False
    blocker = next(item for item in result["blockers"] if item["id"] == "integration.dingtalk")
    assert blocker == {
        "id": "integration.dingtalk",
        "reason": "required_config_missing",
        "missing_fields": ["connectors.dingtalk.adapter", "connectors.dingtalk.secret_ref"],
    }
    assert "values" not in blocker


def test_configured_connector_stays_blocked_until_runtime_adapter_exists() -> None:
    config = {"connectors": {"dingtalk": {
        "enabled": True, "adapter": "private-runtime-name", "secret_ref": "env:PRIVATE_SECRET"
    }}}
    result = resolve_instance_execution(CAPABILITIES, config)
    assert result["ready"] is False
    assert result["blockers"][-1] == {
        "id": "integration.dingtalk", "reason": "adapter_not_available"
    }
    assert "private-runtime-name" not in str(result)
    assert "PRIVATE_SECRET" not in str(result)


def test_configured_connector_becomes_ready_with_generic_adapter_interface() -> None:
    config = {"connectors": {"dingtalk": {
        "enabled": True, "adapter": "private-runtime-name", "secret_ref": "secret:PRIVATE_SECRET"
    }}}
    result = resolve_instance_execution(CAPABILITIES, config, available_adapters={"enterprise-docs"})
    assert result["ready"] is True
    assert result["blockers"] == []


if __name__ == "__main__":
    test_missing_adapter_configuration_is_redacted_and_blocked()
    test_configured_connector_stays_blocked_until_runtime_adapter_exists()
    test_configured_connector_becomes_ready_with_generic_adapter_interface()
    print("ok")
