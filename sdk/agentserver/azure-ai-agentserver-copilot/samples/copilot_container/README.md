# Copilot Container — Base Image for Hosted Agents

A pre-built Docker base image that has all the wiring for running a
GitHub Copilot SDK-backed hosted agent on Microsoft Foundry Agent Service.

Users derive from this image and simply `COPY` their **skills** and
**MCP server configuration** into well-known paths — no custom Python
code required.

## Quick Start

```dockerfile
FROM copilot-base:latest

# Add your skills
COPY my-skills/ /app/foundry/skills/

# Add MCP server configuration (optional)
COPY mcp.json /app/foundry/mcp.json
```

Build and run:

```bash
docker build -t my-agent .
docker run -p 8088:8088 \
  -e COPILOT_MODEL=gpt-4o \
  my-agent
```

## Convention Paths

| Path | Purpose |
|------|---------|
| `/app/foundry/skills/` | Skill directories — each subdirectory contains a `SKILL.md` |
| `/app/foundry/mcp.json` | MCP server configuration (JSON dict of server configs) |
| `/app/tools_acl.yaml` | Tool ACL rules (default: allow-all) |

## Skills

Skills are directories containing a `SKILL.md` file that provides
instructions to Copilot. Place them under `/app/foundry/skills/`:

```
/app/foundry/skills/
├── code-review/
│   └── SKILL.md
└── documentation/
    └── SKILL.md
```

### SKILL.md Format

```markdown
---
name: code-review
description: Specialized code review capabilities
---

# Code Review Guidelines

When reviewing code, always check for:
1. Security vulnerabilities
2. Performance issues
3. Test coverage
```

## MCP Server Configuration

Create a `mcp.json` file with MCP server definitions:

```json
{
    "filesystem": {
        "type": "local",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
        "tools": ["*"]
    },
    "github": {
        "type": "http",
        "url": "https://api.github.com/mcp",
        "headers": {"Authorization": "Bearer ${GITHUB_TOKEN}"},
        "tools": ["*"]
    }
}
```

### Server Types

| Type | Fields | Description |
|------|--------|-------------|
| `local` / `stdio` | `command`, `args`, `env`, `cwd` | Subprocess via stdin/stdout |
| `http` / `sse` | `url`, `headers` | Remote HTTP server |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `COPILOT_MODEL` | `gpt-4.1` (BYOK) / `gpt-5` (GitHub) | Model deployment name |
| `AZURE_AI_FOUNDRY_RESOURCE_URL` | *(none)* | Foundry resource URL for BYOK mode |
| `AZURE_AI_FOUNDRY_API_KEY` | *(none)* | API key for BYOK (falls back to Managed Identity) |
| `TOOL_ACL_PATH` | `/app/tools_acl.yaml` | Path to tool ACL YAML file |
| `MCP_CONFIG_PATH` | `/app/foundry/mcp.json` | Override MCP config file path |
| `SKILL_DIRS` | `/app/foundry/skills` | Colon-separated skill directory paths |

## Tool Access Control

The default `tools_acl.yaml` allows all tool calls (development mode).
For production, replace it with restrictive rules:

```dockerfile
COPY my-tools-acl.yaml /app/tools_acl.yaml
```

Or set `TOOL_ACL_PATH` to point to a custom file.

See the [hosted_agent sample](../hosted_agent/README.md) for the full
ACL YAML schema reference.

## Deploy to Foundry Agent Service

1. Build and push to ACR:

```bash
az acr build --registry <acr-name> \
  --image my-agent:v1 \
  --platform linux/amd64 .
```

2. Register as a hosted agent with the Responses API protocol.

## Example

See the [`example/`](./example/) directory for a complete working example
with a test skill and derived Dockerfile.
