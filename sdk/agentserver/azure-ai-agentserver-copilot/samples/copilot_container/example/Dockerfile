# Example: Derive from the Copilot base image with a greeting skill.
#
# Build (from the azure-ai-agentserver-copilot package root):
#   docker build -f samples/copilot_container/example/Dockerfile -t my-greeting-agent .
#
# Run:
#   docker run -p 8088:8088 -e COPILOT_MODEL=gpt-4o my-greeting-agent

FROM copilot-base:latest

# Copy the greeting skill into the well-known skills directory
COPY samples/copilot_container/example/skills/ /app/foundry/skills/

# Copy MCP config (empty in this example)
COPY samples/copilot_container/example/mcp.json /app/foundry/mcp.json
