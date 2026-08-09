"""Researcher identity and isolation rules, independent of storage adapters."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


RESEARCHER_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized or "default-researcher"


@dataclass(frozen=True)
class ResearcherIdentity:
    id: str
    name: str
    domain: str
    role: str = "researcher"
    isolation: str = "independent_workspace"
    shared_methods: tuple[str, ...] = ()
    implicit_legacy: bool = False

    def to_config(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "domain": self.domain,
            "role": self.role,
            "isolation": self.isolation,
            "shared_methods": list(self.shared_methods),
        }

    def validation_errors(self) -> list[dict[str, str]]:
        errors: list[dict[str, str]] = []
        if not RESEARCHER_ID_PATTERN.fullmatch(self.id):
            errors.append({"field": "researcher.id", "error": "must_be_lowercase_kebab_case"})
        if not self.name.strip():
            errors.append({"field": "researcher.name", "error": "required"})
        if not self.domain.strip():
            errors.append({"field": "researcher.domain", "error": "required"})
        if self.role != "researcher":
            errors.append({"field": "researcher.role", "error": "must_be_researcher"})
        if self.isolation != "independent_workspace":
            errors.append({"field": "researcher.isolation", "error": "must_be_independent_workspace"})
        return errors


def researcher_from_config(cfg: dict[str, Any]) -> ResearcherIdentity:
    raw = cfg.get("researcher")
    if not isinstance(raw, dict):
        name = str(cfg.get("name") or "Default Researcher")
        return ResearcherIdentity(
            id=slug(name),
            name=name,
            domain="legacy knowledge base",
            implicit_legacy=True,
        )
    shared = raw.get("shared_methods", [])
    if not isinstance(shared, list):
        shared = []
    return ResearcherIdentity(
        id=str(raw.get("id") or ""),
        name=str(raw.get("name") or ""),
        domain=str(raw.get("domain") or ""),
        role=str(raw.get("role") or "researcher"),
        isolation=str(raw.get("isolation") or "independent_workspace"),
        shared_methods=tuple(str(item) for item in shared),
    )
