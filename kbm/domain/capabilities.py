"""Portable capability contracts and dependency-ordered execution plans."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable


VALID_CATEGORIES = {"core", "source", "research", "asset", "output", "integration"}
VALID_EXECUTION_MODES = {"builtin", "instruction", "adapter"}
VALID_AVAILABILITY = {"available", "adapter_required"}
CATEGORY_ORDER = {name: index for index, name in enumerate(("core", "source", "research", "asset", "output", "integration"))}


@dataclass(frozen=True)
class CapabilityContract:
    id: str
    category: str
    requires: tuple[str, ...]
    execution_mode: str
    entrypoint: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    quality_gates: tuple[str, ...]
    required_config: tuple[str, ...] = ()
    optional_config: tuple[str, ...] = ()
    availability: str = "available"
    config_scope: str = "portable"

    def to_dict(self) -> dict:
        return asdict(self)


def _contract(
    capability_id: str,
    category: str,
    *,
    requires: tuple[str, ...] = (),
    mode: str,
    entrypoint: str,
    inputs: tuple[str, ...],
    outputs: tuple[str, ...],
    gates: tuple[str, ...] = (),
    required_config: tuple[str, ...] = (),
    optional_config: tuple[str, ...] = (),
    availability: str = "available",
    config_scope: str = "portable",
) -> CapabilityContract:
    return CapabilityContract(
        capability_id, category, requires, mode, entrypoint, inputs, outputs,
        gates, required_config, optional_config, availability, config_scope,
    )


CONTRACTS = (
    _contract("core.identity", "core", mode="builtin", entrypoint="kbm.domain.researcher", inputs=("researcher-config",), outputs=("researcher-identity",), gates=("identity-valid",)),
    _contract("core.workspace-isolation", "core", requires=("core.identity",), mode="builtin", entrypoint="kbm.application.researcher_registry", inputs=("researcher-identity",), outputs=("isolated-workspace",), gates=("workspace-unique",)),
    _contract("core.transactional-pipeline", "core", requires=("core.workspace-isolation",), mode="builtin", entrypoint="scripts/kb_pipeline.py", inputs=("isolated-workspace", "source-candidate"), outputs=("pipeline-task",), gates=("state-transition-valid",)),
    _contract("core.source-traceability", "core", requires=("core.identity",), mode="builtin", entrypoint="kbm.application.source_index", inputs=("source-candidate",), outputs=("traceable-source",), gates=("source-attributed",)),
    _contract("core.quality-gates", "core", requires=("core.source-traceability",), mode="builtin", entrypoint="scripts/kb_manager.py:quality-gate", inputs=("knowledge-artifact",), outputs=("quality-result",), gates=("quality-contract-valid",)),
    _contract("source.public-account", "source", requires=("core.transactional-pipeline",), mode="builtin", entrypoint="scripts/official_account_library.rb", inputs=("public-account-library",), outputs=("source-candidate",), gates=("source-readable",)),
    _contract("source.ebook", "source", requires=("core.transactional-pipeline",), mode="builtin", entrypoint="scripts/ebook_probe.py", inputs=("ebook-file",), outputs=("extracted-source",), gates=("extraction-readable",)),
    _contract("source.video", "source", requires=("core.transactional-pipeline",), mode="adapter", entrypoint="adapter:video-source", inputs=("video-source",), outputs=("transcript-source",), gates=("adapter-available", "source-readable"), required_config=("connectors.video.adapter",), optional_config=("connectors.video.options",), availability="adapter_required", config_scope="instance_only"),
    _contract("source.transcript", "source", requires=("core.transactional-pipeline",), mode="instruction", entrypoint="references/reading-and-refinement.md", inputs=("transcript-source",), outputs=("source-candidate",), gates=("source-readable",)),
    _contract("research.active-reading", "research", requires=("core.source-traceability",), mode="instruction", entrypoint="references/reading-and-refinement.md", inputs=("traceable-source",), outputs=("source-refinement",), gates=("gate-10",)),
    _contract("research.topic-synthesis", "research", requires=("research.active-reading",), mode="instruction", entrypoint="references/asset-output-matrix.md", inputs=("source-refinement",), outputs=("topic-page",), gates=("evidence-threshold", "quality-gate")),
    _contract("research.fact-verification", "research", requires=("core.quality-gates",), mode="instruction", entrypoint="references/verification.md", inputs=("high-risk-claim",), outputs=("verification-record",), gates=("verification-resolved",)),
    _contract("asset.method", "asset", requires=("research.topic-synthesis",), mode="instruction", entrypoint="references/asset-output-matrix.md", inputs=("topic-page",), outputs=("method-asset",), gates=("asset-quality",)),
    _contract("asset.case", "asset", requires=("research.topic-synthesis",), mode="instruction", entrypoint="references/asset-output-matrix.md", inputs=("topic-page",), outputs=("case-asset",), gates=("asset-quality",)),
    _contract("asset.expression", "asset", requires=("research.topic-synthesis",), mode="instruction", entrypoint="references/asset-output-matrix.md", inputs=("topic-page",), outputs=("expression-asset",), gates=("asset-quality",)),
    _contract("asset.framework", "asset", requires=("research.topic-synthesis",), mode="instruction", entrypoint="references/asset-output-matrix.md", inputs=("topic-page",), outputs=("framework-asset",), gates=("asset-quality",)),
    _contract("asset.media-clip", "asset", requires=("source.video",), mode="adapter", entrypoint="adapter:media-clip", inputs=("video-source",), outputs=("media-clip",), gates=("adapter-available",), required_config=("connectors.media-clip.adapter",), availability="adapter_required", config_scope="instance_only"),
    _contract("output.feynman", "output", requires=("research.topic-synthesis",), mode="instruction", entrypoint="references/feynman-template.md", inputs=("topic-page",), outputs=("feynman-output",), gates=("output-quality",)),
    _contract("output.article", "output", requires=("research.topic-synthesis",), mode="instruction", entrypoint="references/publishable-article-workflow.md", inputs=("topic-page",), outputs=("article-output",), gates=("editorial-quality", "output-review")),
    _contract("output.video-script", "output", requires=("research.topic-synthesis",), mode="instruction", entrypoint="references/asset-output-matrix.md", inputs=("topic-page",), outputs=("video-script",), gates=("output-quality",)),
    _contract("output.research-report", "output", requires=("research.fact-verification",), mode="instruction", entrypoint="references/output-rules.md", inputs=("verified-topic",), outputs=("research-report",), gates=("verification-resolved", "output-review")),
    _contract("output.decision-memo", "output", requires=("research.fact-verification",), mode="instruction", entrypoint="references/output-rules.md", inputs=("verified-topic",), outputs=("decision-memo",), gates=("verification-resolved", "output-review")),
    _contract("integration.obsidian", "integration", requires=("core.workspace-isolation",), mode="builtin", entrypoint="scripts/obsidian_linker.py", inputs=("knowledge-artifact",), outputs=("linked-artifact",), gates=("relation-audit",)),
    _contract("integration.dingtalk", "integration", requires=("core.workspace-isolation",), mode="adapter", entrypoint="adapter:enterprise-docs", inputs=("researcher-local-source",), outputs=("researcher-local-artifact",), gates=("adapter-available", "authoritative-sync-confirmed"), required_config=("connectors.dingtalk.adapter", "connectors.dingtalk.secret_ref"), optional_config=("connectors.dingtalk.source_ref", "connectors.dingtalk.output_ref"), availability="adapter_required", config_scope="instance_only"),
    _contract("integration.feishu", "integration", requires=("core.workspace-isolation",), mode="adapter", entrypoint="adapter:enterprise-docs", inputs=("researcher-local-source",), outputs=("researcher-local-artifact",), gates=("adapter-available", "authoritative-sync-confirmed"), required_config=("connectors.feishu.adapter", "connectors.feishu.secret_ref"), optional_config=("connectors.feishu.source_ref", "connectors.feishu.output_ref"), availability="adapter_required", config_scope="instance_only"),
)

CAPABILITY_CONTRACTS = {contract.id: contract for contract in CONTRACTS}


def validate_capability_catalog() -> list[str]:
    errors: list[str] = []
    if len(CAPABILITY_CONTRACTS) != len(CONTRACTS):
        errors.append("duplicate_capability_id")
    for capability_id, contract in CAPABILITY_CONTRACTS.items():
        if contract.category not in VALID_CATEGORIES or not capability_id.startswith(f"{contract.category}."):
            errors.append(f"invalid_category:{capability_id}")
        if contract.execution_mode not in VALID_EXECUTION_MODES:
            errors.append(f"invalid_execution_mode:{capability_id}")
        if contract.availability not in VALID_AVAILABILITY:
            errors.append(f"invalid_availability:{capability_id}")
        if not contract.entrypoint or not contract.inputs or not contract.outputs:
            errors.append(f"incomplete_contract:{capability_id}")
        if contract.execution_mode == "adapter" and contract.availability != "adapter_required":
            errors.append(f"adapter_must_be_required:{capability_id}")
        if contract.execution_mode == "adapter" and (
            contract.config_scope != "instance_only" or not contract.required_config
        ):
            errors.append(f"adapter_contract_not_instance_scoped:{capability_id}")
        for dependency in contract.requires:
            if dependency not in CAPABILITY_CONTRACTS:
                errors.append(f"unknown_dependency:{capability_id}:{dependency}")
    try:
        dependency_order(CAPABILITY_CONTRACTS)
    except ValueError as exc:
        errors.append(str(exc))
    return errors


def dependency_order(selected: Iterable[str]) -> tuple[str, ...]:
    selected_set = set(selected)
    ordered: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(capability_id: str) -> None:
        if capability_id in visited:
            return
        if capability_id in visiting:
            raise ValueError(f"capability_dependency_cycle:{capability_id}")
        if capability_id not in CAPABILITY_CONTRACTS:
            raise ValueError(f"unknown_capability:{capability_id}")
        visiting.add(capability_id)
        for dependency in sorted(CAPABILITY_CONTRACTS[capability_id].requires):
            if dependency in selected_set:
                visit(dependency)
        visiting.remove(capability_id)
        visited.add(capability_id)
        ordered.append(capability_id)

    def sort_key(capability_id: str) -> tuple[int, str]:
        contract = CAPABILITY_CONTRACTS.get(capability_id)
        return (CATEGORY_ORDER.get(contract.category if contract else "", 99), capability_id)

    for capability_id in sorted(selected_set, key=sort_key):
        visit(capability_id)
    return tuple(ordered)


def execution_plan(selected: Iterable[str]) -> tuple[dict, ...]:
    steps: list[dict] = []
    statuses: dict[str, str] = {}
    for sequence, capability_id in enumerate(dependency_order(selected), start=1):
        contract = CAPABILITY_CONTRACTS[capability_id]
        if contract.availability == "adapter_required":
            status = "blocked_adapter_required"
        elif any(statuses.get(dependency) != "ready" for dependency in contract.requires):
            status = "blocked_dependency"
        else:
            status = "ready"
        statuses[capability_id] = status
        steps.append({"sequence": sequence, "status": status, **contract.to_dict()})
    return tuple(steps)
