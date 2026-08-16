"""Enforce the boundary between a portable skill and private researcher instances."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable


TEXT_SUFFIXES = {".md", ".json", ".yaml", ".yml", ".py", ".rb", ".toml"}
PRIVATE_VALUE_KEYS = {
    "access_token", "api_key", "app_secret", "client_secret", "mcp_id",
    "mcp_server", "node_id", "output_node_id", "tenant_key", "webhook_url",
}
PLACEHOLDER_PREFIXES = ("${", "env:", "secret:", "<")
ABSOLUTE_PRIVATE_PATH = re.compile(
    r"/(?:Users|home)/(?!xxx/|example/|user/)([A-Za-z0-9_.-]+)/(?:Desktop|Documents|Downloads)/"
)
SECRET_ASSIGNMENT = re.compile(
    r"(?im)^\s*[\"']?(" + "|".join(sorted(PRIVATE_VALUE_KEYS)) + r")[\"']?\s*[:=]\s*[\"']?([^\s,}\"']+)"
)


def _is_placeholder(value: str) -> bool:
    lowered = value.strip().lower()
    return lowered in {"", "null", "none", "false"} or value.startswith(PLACEHOLDER_PREFIXES)


def scan_portable_package(root: Path, *, forbidden_markers: Iterable[str] = ()) -> dict[str, Any]:
    """Find instance data that must never ship in the shared skill package."""
    issues: list[dict[str, str]] = []
    markers = tuple(marker for marker in forbidden_markers if marker)
    scanned = 0
    for path in sorted(root.rglob("*")):
        if (
            not path.is_file()
            or path.suffix.lower() not in TEXT_SUFFIXES
            or ".git" in path.parts
            or "tests" in path.parts
        ):
            continue
        relative = str(path.relative_to(root))
        if relative.startswith("tests/fixtures/"):
            continue
        scanned += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        if ABSOLUTE_PRIVATE_PATH.search(text):
            issues.append({"file": relative, "issue": "private_absolute_path"})
        for match in SECRET_ASSIGNMENT.finditer(text):
            key, value = match.groups()
            if not _is_placeholder(value):
                issues.append({"file": relative, "issue": "embedded_instance_configuration", "key": key})
        for marker in markers:
            if marker in text:
                issues.append({"file": relative, "issue": "forbidden_enterprise_marker"})
                break
    return {"passed": not issues, "files_scanned": scanned, "issue_count": len(issues), "issues": issues}


def validate_instance_connector_config(config: dict[str, Any]) -> list[str]:
    """Reject raw secrets while allowing instance-local IDs and environment references."""
    errors: list[str] = []
    connectors = config.get("connectors", config.get("integrations", {}))
    if not isinstance(connectors, dict):
        return ["connectors_must_be_object"]
    for connector, settings in connectors.items():
        if not isinstance(settings, dict):
            errors.append(f"connector_settings_must_be_object:{connector}")
            continue
        for key, value in settings.items():
            normalized = str(key).lower()
            if normalized in {"access_token", "api_key", "app_secret", "client_secret"}:
                if isinstance(value, str) and not _is_placeholder(value):
                    errors.append(f"raw_secret_forbidden:{connector}:{key}")
    return errors
