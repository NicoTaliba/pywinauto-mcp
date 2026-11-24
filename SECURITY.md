# Security Policy

## Supported Versions

The latest released version on the `main` branch is supported with security fixes.

## Reporting a Vulnerability

Please do **not** open a public issue for security-sensitive reports.

- Preferred: use GitHub **Private vulnerability reporting** (Security tab → "Report a vulnerability").
- Alternatively, open an issue tagged `security` with a high-level description and we will move it to a private channel.

Please include: affected version/commit, OS/Windows build, a minimal reproduction, and impact. We aim to acknowledge reports within 5 business days.

## Scope

`pywinauto-mcp` runs locally and drives Windows GUI automation via `pywinauto`. Relevant areas include: the MCP transport surface, input injection, and anything that executes on behalf of a connected MCP client.
