# Privacy and Enterprise Connector Boundary

Use this reference when a researcher reads from or writes to MCP servers, DingTalk, Feishu, or another enterprise system.

## Non-negotiable boundary

The shared skill package may contain only portable connector contracts, configuration schemas, adapter interfaces, generic quality gates, and synthetic fixtures. It must not contain a researcher's real MCP configuration, server URL, tenant identifier, node or folder identifier, credential, absolute personal path, enterprise taxonomy, internal product knowledge, customer case, or source material.

Enterprise knowledge belongs to the researcher workspace. It must not enter another researcher through a shared cache, registry, method directory, test fixture, domain default, or release package. Cross-researcher transfer requires an explicit import with source attribution.

## Configuration placement

Keep non-secret instance identifiers in the selected researcher's config. Store credentials only as environment or secret-store references:

```yaml
connectors:
  enterprise-docs:
    enabled: true
    node_id: <INSTANCE_NODE_ID>
    client_secret: env:ENTERPRISE_DOCS_CLIENT_SECRET
```

Never publish the instantiated config as part of the skill. A connector capability remains `adapter_required` until its adapter and required instance fields are available.

## Release and runtime gates

1. Package lint must reject concrete private paths and embedded MCP/connector values.
2. Researcher registration and doctor checks must reject raw credentials.
3. Connector execution must resolve only the selected researcher config and namespace.
4. Sync state, caches, evidence and outputs must remain under that researcher's runtime/workspace.
5. A failed authoritative-store write must not mark an item committed.
6. Tests published with the skill must use synthetic organizations, IDs, paths and content.
