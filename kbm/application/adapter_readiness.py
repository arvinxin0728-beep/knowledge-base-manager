"""Resolve adapter-backed capability readiness without exposing instance values."""

from __future__ import annotations

import os
from typing import Any, Iterable

from kbm.domain.capabilities import CAPABILITY_CONTRACTS, dependency_order


def available_adapters_from_env() -> set[str]:
    raw = os.environ.get("KBM_AVAILABLE_ADAPTERS", "")
    return {item.strip() for item in raw.split(",") if item.strip()}


def _lookup(config: dict[str, Any], dotted: str) -> tuple[bool, Any]:
    current: Any = config
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            return False, None
        current = current[part]
    return current not in (None, ""), current


def resolve_instance_execution(
    capability_ids: Iterable[str],
    config: dict[str, Any],
    *,
    available_adapters: Iterable[str] = (),
) -> dict[str, Any]:
    """Return redacted readiness; never include connector configuration values."""
    adapter_set = set(available_adapters)
    statuses: dict[str, str] = {}
    steps: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    for sequence, capability_id in enumerate(dependency_order(capability_ids), start=1):
        contract = CAPABILITY_CONTRACTS[capability_id]
        missing = [field for field in contract.required_config if not _lookup(config, field)[0]]
        connector_name = capability_id.split(".", 1)[1]
        connector = config.get("connectors", {}).get(connector_name, {})
        disabled = isinstance(connector, dict) and connector.get("enabled") is False
        adapter_name = contract.entrypoint.split(":", 1)[1] if contract.execution_mode == "adapter" else ""
        if any(statuses.get(dependency) != "ready" for dependency in contract.requires):
            status, reason = "blocked_dependency", "dependency_not_ready"
        elif contract.execution_mode != "adapter":
            status, reason = "ready", ""
        elif disabled:
            status, reason = "blocked_configuration", "connector_disabled"
        elif missing:
            status, reason = "blocked_configuration", "required_config_missing"
        elif adapter_name not in adapter_set:
            status, reason = "blocked_adapter_required", "adapter_not_available"
        else:
            status, reason = "ready", ""
        statuses[capability_id] = status
        step = {"sequence": sequence, "id": capability_id, "status": status}
        steps.append(step)
        if status != "ready":
            blocker: dict[str, Any] = {"id": capability_id, "reason": reason}
            if missing:
                blocker["missing_fields"] = missing
            blockers.append(blocker)
    return {"ready": not blockers, "steps": steps, "blockers": blockers}
