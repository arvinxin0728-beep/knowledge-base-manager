#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path

from kbm.application.privacy_boundary import scan_portable_package, validate_instance_connector_config


def test_portable_package_rejects_private_paths_connector_values_and_enterprise_markers() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        (root / "bad.yaml").write_text(
            "output_node_id: real-node\npath: /Users/realperson/Desktop/private\nenterprise-secret-term\n",
            encoding="utf-8",
        )
        result = scan_portable_package(root, forbidden_markers=["enterprise-secret-term"])
        assert result["passed"] is False
        assert {item["issue"] for item in result["issues"]} == {
            "private_absolute_path", "embedded_instance_configuration", "forbidden_enterprise_marker"
        }


def test_generic_connector_contract_and_secret_references_are_portable() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        (root / "connector.yaml").write_text(
            "id: integration.example\nclient_secret: ${EXAMPLE_CLIENT_SECRET}\n",
            encoding="utf-8",
        )
        assert scan_portable_package(root)["passed"] is True
    assert validate_instance_connector_config({
        "connectors": {"example": {"client_secret": "env:EXAMPLE_CLIENT_SECRET", "node_id": "instance-local"}}
    }) == []


def test_raw_connector_secret_is_rejected() -> None:
    errors = validate_instance_connector_config({
        "connectors": {"example": {"client_secret": "plaintext-secret"}}
    })
    assert errors == ["raw_secret_forbidden:example:client_secret"]


def test_secret_ref_must_be_an_external_reference() -> None:
    errors = validate_instance_connector_config({
        "connectors": {"example": {"secret_ref": "plaintext-secret"}}
    })
    assert errors == ["secret_reference_required:example:secret_ref"]


if __name__ == "__main__":
    test_portable_package_rejects_private_paths_connector_values_and_enterprise_markers()
    test_generic_connector_contract_and_secret_references_are_portable()
    test_raw_connector_secret_is_rejected()
    test_secret_ref_must_be_an_external_reference()
    print("ok")
