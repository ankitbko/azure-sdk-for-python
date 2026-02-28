#!/usr/bin/env python3
"""Pre-install npm packages referenced in mcp.json during Docker build.

Parses the MCP config file and runs `npm install -g <package>` for any
local/stdio server that uses `npx -y <package>` as its command+args.
This eliminates the cold-start delay of npx downloading packages at runtime.
"""

import json
import subprocess
import sys
from pathlib import Path


def extract_npm_packages(mcp_path: str) -> list[str]:
    """Extract npm package names from mcp.json npx entries."""
    path = Path(mcp_path)
    if not path.is_file():
        return []

    with open(path) as f:
        config = json.load(f)

    if not isinstance(config, dict):
        return []

    packages = []
    for name, server in config.items():
        cmd = server.get("command", "")
        args = server.get("args", [])
        server_type = server.get("type", "local")

        if server_type in ("local", "stdio", None):
            # Pattern: "command": "npx", "args": ["-y", "<package>", ...]
            if cmd == "npx" and len(args) >= 2 and args[0] == "-y":
                pkg = args[1]
                packages.append(pkg)
                print(f"  [{name}] Found npm package: {pkg}")
            # Pattern: "command": "npx", "args": ["<package>", ...]
            elif cmd == "npx" and len(args) >= 1 and not args[0].startswith("-"):
                pkg = args[0]
                packages.append(pkg)
                print(f"  [{name}] Found npm package: {pkg}")
            # Pattern: "command": "node", "args": ["node_modules/.bin/<pkg>", ...]
            # Skip — user manages their own node_modules

    return packages


def main():
    mcp_path = sys.argv[1] if len(sys.argv) > 1 else "/app/foundry/mcp.json"
    print(f"Scanning {mcp_path} for npm packages to pre-install...")

    packages = extract_npm_packages(mcp_path)
    if not packages:
        print("No npm packages found to pre-install.")
        return

    print(f"Installing {len(packages)} package(s): {', '.join(packages)}")
    for pkg in packages:
        print(f"  npm install -g {pkg}")
        result = subprocess.run(
            ["npm", "install", "-g", pkg],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"  WARNING: Failed to install {pkg}: {result.stderr.strip()}")
        else:
            print(f"  ✓ {pkg} installed")

    print("Done.")


if __name__ == "__main__":
    main()
