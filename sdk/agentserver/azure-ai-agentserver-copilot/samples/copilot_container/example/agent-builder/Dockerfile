# Agent Builder
#
# A meta-agent that creates, deploys, and tests other Foundry hosted agents.
# The fa CLI is installed from a pre-built wheel at build time (private repo).
#
# Build (see README.md for full instructions):
#   cp ~/src/github/hosted-agent-cli/dist/*.whl .
#   docker build --platform linux/amd64 -t agent-builder .
#
# Run:
#   docker run -p 8088:8088 \
#     -e COPILOT_GITHUB_TOKEN=<github-pat> \
#     -e COPILOT_MODEL=claude-opus-4.6 \
#     agent-builder

ARG BASE_IMAGE=acrhostedagentbugbash.azurecr.io/ghcp-adapter:vnext-5
FROM ${BASE_IMAGE}

# Install fa CLI from pre-built wheel (private repo — not published to PyPI)
# Copy the wheel into the build context before building:
#   cp ~/src/github/hosted-agent-cli/dist/*.whl .
COPY hosted_agent_cli-0.1.0-py3-none-any.whl /tmp/
RUN pip install --no-cache-dir /tmp/hosted_agent_cli-0.1.0-py3-none-any.whl && rm /tmp/*.whl

# Install Azure CLI (needed by fa deploy for az acr build and az rest)
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends curl ca-certificates gnupg lsb-release && \
    curl -sL https://aka.ms/InstallAzureCLIDeb | bash && \
    rm -rf /var/lib/apt/lists/*

# Patch Azure CLI ACR module to respect AZURE_CLI_DISABLE_CONNECTION_VERIFICATION
# when uploading build context and streaming logs via BlobClient.
# Without this, `az acr build` fails with SSL errors behind a TLS-intercepting proxy.
COPY fix_acr_ssl.py /tmp/
RUN python3 /tmp/fix_acr_ssl.py && rm /tmp/fix_acr_ssl.py

# Copy skills
COPY skills/ /app/foundry/skills/

# Copy MCP config (empty — agent-builder doesn't need MCP servers itself)
COPY mcp.json /app/foundry/mcp.json

# Override CMD to add az login --identity before starting the agent.
# Preserves the base image's certificate validation setup.
# az login runs AFTER cert setup so it can use the proxy CA.
CMD bash -c '\
    if [ -f /etc/ssl/certs/adc-egress-proxy-ca.crt ]; then \
    cat /etc/ssl/certs/adc-egress-proxy-ca.crt >> /etc/ssl/certs/ca-certificates.crt && \
    cat /etc/ssl/certs/adc-egress-proxy-ca.crt >> /usr/local/lib/python3.12/site-packages/certifi/cacert.pem; \
    fi && \
    echo "Attempting az login --identity..." && \
    az login --identity --allow-no-subscriptions 2>&1 && echo "az login succeeded" || echo "az login --identity failed" && \
    python main.py'
