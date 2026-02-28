FROM python:3.12-slim

# Ensure Python output is sent straight to the container logs (no buffering)
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy the package source and install it with all dependencies
COPY . package/
RUN pip install --no-cache-dir ./package/ azure-identity "github-copilot-sdk>=0.1.25"

# Create the well-known directories for user content
RUN mkdir -p /app/foundry/skills

# Copy the base entrypoint, default ACL, and MCP package installer
COPY samples/copilot_container/main.py main.py
COPY samples/copilot_container/tools_acl.yaml tools_acl.yaml
COPY samples/copilot_container/install_mcp_packages.py install_mcp_packages.py

EXPOSE 8088

CMD bash -c '\
    if [ -f /etc/ssl/certs/adc-egress-proxy-ca.crt ]; then \
    cat /etc/ssl/certs/adc-egress-proxy-ca.crt >> /etc/ssl/certs/ca-certificates.crt && \
    cat /etc/ssl/certs/adc-egress-proxy-ca.crt >> /usr/local/lib/python3.12/site-packages/certifi/cacert.pem; \
    fi && \
    python main.py'
