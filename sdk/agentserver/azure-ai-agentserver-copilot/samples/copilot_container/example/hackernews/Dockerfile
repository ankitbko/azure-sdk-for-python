# Hacker News Summarizer Agent
#
# Derives from the Copilot base image and adds:
#   - A skill that instructs Copilot to summarize HN articles
#   - An MCP server (mcp-hacker-news) for fetching live HN data
#
# Build (from the azure-ai-agentserver-copilot package root):
#   docker build -f samples/copilot_container/example/hackernews/Dockerfile \
#     -t hackernews-agent .
#
# Run:
#   docker run -p 8088:8088 \
#     -e COPILOT_MODEL=gpt-4o \
#     -e AZURE_AI_FOUNDRY_RESOURCE_URL=https://<resource>.cognitiveservices.azure.com \
#     -e AZURE_AI_FOUNDRY_API_KEY=<key> \
#     hackernews-agent

FROM copilot-base:latest

# Install Node.js for the MCP server (npx requires it)
RUN apt-get update -qq && apt-get install -y --no-install-recommends nodejs npm && \
    rm -rf /var/lib/apt/lists/*

# Copy the HN summarizer skill
COPY samples/copilot_container/example/hackernews/skills/ /app/foundry/skills/

# Copy MCP server configuration
COPY samples/copilot_container/example/hackernews/mcp.json /app/foundry/mcp.json
