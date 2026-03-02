# Agent Builder

A meta-agent that creates, deploys, and tests other Foundry hosted agents.

Users describe the agent they want, and this agent:
1. Scaffolds a new project using `fa init -t ghcp`
2. Customizes skills and MCP config based on user requirements
3. Deploys to Foundry using `fa deploy`
4. Tests the deployed agent using `fa invoke --remote`

## Prerequisites

- The `fa` (foundry-agent) CLI wheel built from the private repo `coreai-microsoft/hosted-agent-cli`
- Access to the ACR registry `acrhostedagentbugbash`
- The base Copilot adapter image `acrhostedagentbugbash.azurecr.io/ghcp-adapter:vnext-3`

## Build

The `fa` CLI is from a private repo and is installed via a pre-built wheel at Docker build time.

```bash
# 1. Build the wheel (if not already built)
cd ~/src/github/hosted-agent-cli
uv build

# 2. Copy the wheel into the agent-builder build context
cp ~/src/github/hosted-agent-cli/dist/hosted_agent_cli-0.1.0-py3-none-any.whl \
   samples/copilot_container/example/agent-builder/

# 3. Build the Docker image locally
cd <azure-ai-agentserver-copilot-root>
docker build --platform linux/amd64 \
  -t agent-builder:latest \
  -f samples/copilot_container/example/agent-builder/Dockerfile \
  samples/copilot_container/example/agent-builder/

# 4. Or build via ACR (for deploying to Foundry)
az acr build --registry acrhostedagentbugbash \
  --image agent-builder:1 \
  --platform linux/amd64 \
  -f Dockerfile \
  samples/copilot_container/example/agent-builder/

# 5. Clean up the wheel (don't commit it)
rm samples/copilot_container/example/agent-builder/*.whl
```

## Run Locally

```bash
docker run -p 8088:8088 \
  -e GH_TOKEN=<github-pat> \
  -e COPILOT_MODEL=claude-opus-4.6 \
  agent-builder:latest
```

## Deploy to Foundry (vNext)

After pushing to ACR, create a hosted agent with these settings:

| Property | Value |
|----------|-------|
| Image | `acrhostedagentbugbash.azurecr.io/agent-builder:<tag>` |
| CPU | 2 |
| Memory | 4Gi |
| Protocol | responses (v2025-03-26) |
| vNext | `enableVnextExperience: true` |

Required environment variables:
- `GH_TOKEN` — GitHub PAT with Copilot scope
- `COPILOT_MODEL` — e.g. `claude-opus-4.6`
- `ACR_NAME` — ACR registry name where child agent images are pushed (e.g. `acrhostedagentbugbash`)
- `FOUNDRY_PROJECT_URL` — Foundry project endpoint where child agents are deployed (e.g. `https://<account>.services.ai.azure.com/api/projects/<project>`)
- `TOOL_ACL_PATH` — `/app/tools_acl.yaml`
- `APPLICATIONINSIGHTS_CONNECTION_STRING` — (optional) App Insights connection string

## What the Agent Does

When a user asks to build an agent, it:
1. Runs `fa init --name <name> -t ghcp` to scaffold in `/tmp/<name>/`
2. Edits `skills/<name>/SKILL.md` with the user's instructions
3. Edits `mcp.json` if the agent needs MCP tool servers
4. Sets `GH_TOKEN` in `.env` from its own environment (never asks the user)
5. Runs `fa deploy` to build and deploy to Foundry
6. Reports `FOUNDRY_HOSTED_AGENT_URL: <playground-url>` to the user
7. Tests with `fa invoke --remote "<message>"`

## Important Notes

- **Do NOT commit** the `.whl` file or `hosted-agent-cli/` directory — the CLI is from a private repo
- The `.gitignore` excludes both `hosted-agent-cli/` and `*.whl`
- Local `fa invoke` won't work (no `main.py` in scaffolded ghcp projects) — always use `--remote`
- The agent needs Azure CLI auth inside the container for `fa deploy` (ACR build + az rest)

