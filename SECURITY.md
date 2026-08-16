# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| 0.8.x beta | Yes |
| 0.7.x beta | Security fixes only |
| < 0.7 | No |

## Privacy and Local Data Boundary

`knowledge-base-manager` is designed to operate on user-provided local knowledge materials such as ebooks, Markdown notes, public-account exports, articles, and Obsidian vaults.

The deterministic scripts in this package do not intentionally upload user files to external services. However, when an agent platform uses this skill, that platform may send prompts, excerpts, paths, or generated content to its configured model provider. Users and integrators are responsible for understanding the privacy model of the agent platform they run this package inside.

Do not process confidential, regulated, copyrighted, or third-party private materials unless you have permission and understand the data-handling boundary of your runtime.

MCP, DingTalk, Feishu, and other enterprise connector values must remain in one researcher instance. The shared package may contain only generic adapter contracts and synthetic fixtures. Store credentials through environment or secret-store references; do not commit instantiated configs, tenant/node identifiers, private paths, or enterprise knowledge.

## High-Risk Content

This project helps structure and reuse knowledge. It is not a source of truth for high-risk domains.

Before using generated outputs for legal, medical, financial, policy, market, company, or business-critical decisions, run verification workflows and review claims against authoritative sources.

## Reporting a Vulnerability

For now, report issues through the GitHub repository issue tracker once the project is published.

When reporting, include:

- package version
- operating system
- agent platform or script-only usage
- command or workflow used
- minimal reproduction steps
- whether private source content is involved

Do not paste private source materials, secrets, access tokens, or confidential knowledge-base content into public issues.
