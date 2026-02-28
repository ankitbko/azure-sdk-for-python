FROM python:3.12-slim

# Ensure Python output is sent straight to the container logs (no buffering)
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy the package source and install it with all dependencies
COPY . package/
RUN pip install --no-cache-dir ./package/ azure-identity "github-copilot-sdk>=0.1.25"

# Create the well-known directories for user content
RUN mkdir -p /app/foundry/skills

# Copy the base entrypoint and default ACL
COPY samples/copilot_container/main.py main.py
COPY samples/copilot_container/tools_acl.yaml tools_acl.yaml

EXPOSE 8088

CMD ["python", "main.py"]
