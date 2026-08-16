# Capability Contracts

Use a capability contract to make researcher composition executable and auditable. Do not add a capability as a label only.

Every capability must declare:

- a namespaced ID and category;
- dependency capabilities;
- one execution mode: `builtin`, `instruction`, or `adapter`;
- a portable entrypoint;
- accepted input artifact types;
- produced output artifact types;
- quality gates;
- required and optional configuration keys;
- availability and configuration scope.

`builtin` points to a bundled deterministic module or script. `instruction` points to a bundled reference that the model must follow. `adapter` points to a generic adapter interface and remains blocked until an instance provides and verifies an implementation.

Never put a real MCP server name, URL, tenant, node ID, credential, enterprise taxonomy, or enterprise content in a contract. Adapter configuration must use `instance_only`; the contract may name configuration fields but not their values.

Resolve dependencies before consumers. Present the plan in the stable category order core, source, research, asset, output, integration. Mark a missing adapter as `blocked_adapter_required`; mark a consumer of a blocked dependency as `blocked_dependency`. Never report these steps as ready or silently skip them.

Write only the compact sequence, capability ID, status, and portable entrypoint into a researcher's resolved manifest. Keep the full shared contract in the skill package so each researcher does not duplicate it.
