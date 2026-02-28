# Hacker News Summarizer Agent

An example agent that fetches and summarizes top Hacker News articles,
built on the Copilot base image.

## What's Included

- **Skill**: `hackernews-summarizer` — instructs Copilot to fetch, summarize,
  and categorize HN stories
- **MCP Server**: `mcp-hacker-news` — provides live access to the Hacker News
  API (top stories, comments, users)

## Build

```bash
# From the azure-ai-agentserver-copilot package root:

# 1. Build the base image first (if not already built)
docker build --platform linux/amd64 \
  -t copilot-base:latest \
  -f samples/copilot_container/Dockerfile .

# 2. Build the HN agent
docker build --platform linux/amd64 \
  -t hackernews-agent:latest \
  -f samples/copilot_container/example/hackernews/Dockerfile .
```

## Run Locally

```bash
docker run -p 8088:8088 \
  -e COPILOT_MODEL=gpt-4o \
  -e AZURE_AI_FOUNDRY_RESOURCE_URL=https://<resource>.cognitiveservices.azure.com \
  -e AZURE_AI_FOUNDRY_API_KEY=<key> \
  hackernews-agent:latest
```

## Test

```bash
# Non-streaming
curl -sS -H "Content-Type: application/json" \
  -X POST http://localhost:8088/responses \
  -d '{"input":"What are the top stories on Hacker News right now?","stream":false}'

# Streaming
curl -N -H "Content-Type: application/json" \
  -X POST http://localhost:8088/responses \
  -d '{"input":"Summarize the top 3 HN stories","stream":true}'
```

## How It Works

1. The base image provides the Copilot SDK adapter and Foundry Responses API server
2. The `hackernews-summarizer` skill injects instructions for how to present HN stories
3. The `mcp-hacker-news` MCP server gives Copilot live access to the HN API
4. When a user asks about HN, Copilot uses the MCP tools to fetch stories and
   the skill instructions to format the response
