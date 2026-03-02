# MCP Client Configuration

This page covers configuration for MCP clients other than Claude Desktop. For Claude Desktop, see the [README](../README.md).

In all cases, replace `/absolute/path/to/benkyou` with your actual clone path and restart the client after saving.

---

## Codex Desktop

In Codex Desktop, go to **Settings → MCP → Connect to a custom MCP** and fill in:

| Field | Value |
|---|---|
| Name | `benkyou` |
| Transport | `STDIO` |
| Command to launch | `/path/to/uv` (find with `which uv`) |
| Arguments (one per line) | `--directory` → `/absolute/path/to/benkyou` → `run` → `python` → `-m` → `mcp_server.server` → `--data-dir` → `/absolute/path/to/benkyou/data` |
| Working directory | `/absolute/path/to/benkyou` |
