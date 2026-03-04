FROM python:3.12

# Ensure Python output is sent straight to the container logs (no buffering)
ENV PYTHONUNBUFFERED=1

# Install Node.js for the MCP server (npx requires it)
RUN apt-get update -qq && apt-get install -y --no-install-recommends nodejs npm && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the package source and install it with all dependencies
COPY . package/
RUN pip install --no-cache-dir ./package/ azure-identity "github-copilot-sdk>=0.1.25"

# Create the well-known directories for user content
RUN mkdir -p /app/foundry/skills

# Enable Copilot CLI staff mode to unlock the SKILLS_INSTRUCTIONS feature flag.
# Without this, skill directories are discovered but the full SKILL.md content
# is NOT injected into the model context — only the short description from the
# YAML frontmatter is visible.  This is a server-side feature flag gated behind
# staff mode; see ARCHITECTURE.md for details.
RUN mkdir -p /root/.copilot && \
    echo '{"staff": true}' > /root/.copilot/config.json

# Copy the base entrypoint, default ACL, and MCP package installer
COPY samples/copilot_container/main.py main.py
COPY samples/copilot_container/tools_acl.yaml tools_acl.yaml
COPY samples/copilot_container/install_mcp_packages.py install_mcp_packages.py

EXPOSE 8088

ENV AZURE_CLI_DISABLE_CONNECTION_VERIFICATION=1
ENV ADAL_PYTHON_SSL_NO_VERIFY=1
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

CMD bash -c '\
    if [ -f /etc/ssl/certs/adc-egress-proxy-ca.crt ]; then \
    cat /etc/ssl/certs/adc-egress-proxy-ca.crt >> /etc/ssl/certs/ca-certificates.crt && \
    cat /etc/ssl/certs/adc-egress-proxy-ca.crt >> /usr/local/lib/python3.12/site-packages/certifi/cacert.pem; \
    fi && \
    python main.py'
