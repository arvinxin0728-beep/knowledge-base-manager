"""Researcher registry and workspace lifecycle services."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kbm.domain.researcher import ResearcherIdentity, researcher_from_config
from kbm.application.privacy_boundary import validate_instance_connector_config
from kbm.platform.config import load_config, validate_config
from kbm.platform.paths import local_runtime_dir, system_dir


REGISTRY_VERSION = 1
VALID_STATUSES = {"active", "inactive"}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def empty_registry(shared_methods: str = "") -> dict[str, Any]:
    return {
        "version": REGISTRY_VERSION,
        "selected_researcher": None,
        "shared_methods": shared_methods,
        "researchers": [],
    }


def load_registry(path: Path, *, allow_missing: bool = False) -> dict[str, Any]:
    if not path.exists():
        if allow_missing:
            return empty_registry()
        raise ValueError("registry_not_found")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != REGISTRY_VERSION:
        raise ValueError("unsupported_registry_version")
    if not isinstance(data.get("researchers"), list):
        raise ValueError("registry_researchers_must_be_array")
    data.setdefault("selected_researcher", None)
    data.setdefault("shared_methods", "")
    return data


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    tmp = Path(raw)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def registry_errors(registry: dict[str, Any]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    seen_configs: set[str] = set()
    seen_workspaces: set[str] = set()
    for index, entry in enumerate(registry.get("researchers", [])):
        prefix = f"researchers[{index}]"
        if not isinstance(entry, dict):
            errors.append({"field": prefix, "error": "must_be_object"})
            continue
        researcher_id = str(entry.get("id") or "")
        config_raw = str(entry.get("config") or "")
        workspace_raw = str(entry.get("workspace") or "")
        if not researcher_id:
            errors.append({"field": f"{prefix}.id", "error": "required"})
        elif researcher_id in seen_ids:
            errors.append({"field": f"{prefix}.id", "error": "duplicate"})
        seen_ids.add(researcher_id)
        if not Path(config_raw).is_absolute():
            errors.append({"field": f"{prefix}.config", "error": "must_be_absolute"})
        elif config_raw in seen_configs:
            errors.append({"field": f"{prefix}.config", "error": "duplicate"})
        seen_configs.add(config_raw)
        if not Path(workspace_raw).is_absolute():
            errors.append({"field": f"{prefix}.workspace", "error": "must_be_absolute"})
        elif workspace_raw in seen_workspaces:
            errors.append({"field": f"{prefix}.workspace", "error": "duplicate"})
        seen_workspaces.add(workspace_raw)
        if entry.get("status") not in VALID_STATUSES:
            errors.append({"field": f"{prefix}.status", "error": "must_be_active_or_inactive"})
    selected = registry.get("selected_researcher")
    if selected is not None and selected not in seen_ids:
        errors.append({"field": "selected_researcher", "error": "unknown_researcher"})
    return errors


def entry_from_config(config_path: Path, *, status: str = "active") -> dict[str, Any]:
    resolved = config_path.expanduser().resolve()
    cfg = load_config(resolved)
    errors = validate_config(cfg)
    errors.extend(
        {"field": "connectors", "error": error}
        for error in validate_instance_connector_config(cfg)
    )
    if errors:
        raise ValueError(json.dumps({"config_errors": errors}, ensure_ascii=False))
    identity = researcher_from_config(cfg)
    return {
        "id": identity.id,
        "name": identity.name,
        "domain": identity.domain,
        "workspace": str(Path(cfg["ai_knowledge_base"]).expanduser().resolve()),
        "config": str(resolved),
        "status": status,
        "registered_at": now_iso(),
    }


def register(registry: dict[str, Any], config_path: Path, *, status: str = "active") -> tuple[dict[str, Any], dict[str, Any]]:
    entry = entry_from_config(config_path, status=status)
    for current in registry["researchers"]:
        if current["id"] == entry["id"]:
            if current["config"] == entry["config"]:
                return registry, current
            raise ValueError("researcher_id_already_registered")
        if current["config"] == entry["config"]:
            raise ValueError("config_already_registered_to_another_researcher")
        if current["workspace"] == entry["workspace"]:
            raise ValueError("workspace_already_registered_to_another_researcher")
    updated = dict(registry)
    updated["researchers"] = [*registry["researchers"], entry]
    if updated.get("selected_researcher") is None:
        updated["selected_researcher"] = entry["id"]
    errors = registry_errors(updated)
    if errors:
        raise ValueError(json.dumps({"registry_errors": errors}, ensure_ascii=False))
    return updated, entry


def select(registry: dict[str, Any], researcher_id: str) -> dict[str, Any]:
    matches = [item for item in registry["researchers"] if item.get("id") == researcher_id and item.get("status") == "active"]
    if not matches:
        raise ValueError("active_researcher_not_found")
    updated = dict(registry)
    updated["selected_researcher"] = researcher_id
    return updated


def resolve_entry(registry: dict[str, Any], researcher_id: str | None = None) -> dict[str, Any]:
    target = researcher_id or registry.get("selected_researcher")
    if not target:
        raise ValueError("researcher_not_selected")
    for entry in registry["researchers"]:
        if entry.get("id") == target:
            return entry
    raise ValueError("researcher_not_found")


@dataclass(frozen=True)
class DoctorResult:
    researcher_id: str
    healthy: bool
    checks: dict[str, Any]


def doctor_entry(entry: dict[str, Any]) -> DoctorResult:
    config_path = Path(entry["config"])
    checks: dict[str, Any] = {"config_exists": config_path.is_file()}
    if not config_path.is_file():
        return DoctorResult(str(entry["id"]), False, checks)
    try:
        cfg = load_config(config_path)
        config_issues = validate_config(cfg)
        config_issues.extend(
            {"field": "connectors", "error": error}
            for error in validate_instance_connector_config(cfg)
        )
        identity = researcher_from_config(cfg)
        checks.update({
            "config_valid": not config_issues,
            "config_issues": config_issues,
            "identity_matches_registry": identity.id == entry.get("id"),
            "workspace_matches_registry": str(Path(cfg["ai_knowledge_base"]).expanduser().resolve()) == entry.get("workspace"),
            "system_exists": system_dir(cfg).is_dir(),
            "runtime_storage": cfg.get("pipeline", {}).get("runtime_storage", "legacy"),
            "runtime_path": str(local_runtime_dir(cfg)) if cfg.get("pipeline", {}).get("runtime_storage") == "local" else str(system_dir(cfg) / "runtime"),
        })
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        checks["load_error"] = str(exc)
    required = ("config_exists", "config_valid", "identity_matches_registry", "workspace_matches_registry", "system_exists")
    return DoctorResult(str(entry["id"]), all(checks.get(key) is True for key in required), checks)
