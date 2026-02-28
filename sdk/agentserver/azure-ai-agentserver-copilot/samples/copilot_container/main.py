# Copyright (c) Microsoft. All rights reserved.

"""Base entrypoint for Copilot hosted agent containers.

This script auto-discovers skills and MCP server configuration from
well-known paths and wires them into the Copilot SDK session.

Convention paths
----------------
/app/foundry/skills/   — Skill directories (each subdirectory has SKILL.md)
/app/foundry/mcp.json  — MCP server configuration (JSON dict)
/app/tools_acl.yaml    — Tool ACL rules

Environment variable overrides
------------------------------
SKILL_DIRS             Colon-separated skill directory paths
                       (default: /app/foundry/skills)
MCP_CONFIG_PATH        Path to MCP config JSON file
                       (default: /app/foundry/mcp.json)
TOOL_ACL_PATH          Path to tool ACL YAML file
                       (default: /app/tools_acl.yaml)
COPILOT_MODEL          Model deployment name
AZURE_AI_FOUNDRY_RESOURCE_URL   Foundry resource URL for BYOK mode
AZURE_AI_FOUNDRY_API_KEY        API key for BYOK (falls back to Managed Identity)
"""

import asyncio
import json
import os
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

from copilot import SessionConfig
from azure.ai.agentserver.copilot import from_copilot

_DEFAULT_SKILLS_DIR = "/app/foundry/skills"
_DEFAULT_MCP_CONFIG = "/app/foundry/mcp.json"
_DEFAULT_ACL_PATH = "/app/tools_acl.yaml"


def _load_mcp_config() -> dict | None:
    """Load MCP server configuration from JSON file."""
    path = os.getenv("MCP_CONFIG_PATH", _DEFAULT_MCP_CONFIG)
    if not Path(path).is_file():
        logger.info(f"No MCP config found at {path}")
        return None

    with open(path) as f:
        config = json.load(f)

    if not isinstance(config, dict) or not config:
        logger.info(f"MCP config at {path} is empty or not a dict")
        return None

    logger.info(f"Loaded MCP config from {path}: {list(config.keys())}")
    return config


def _load_skill_directories() -> list[str] | None:
    """Discover skill directories from well-known paths."""
    raw = os.getenv("SKILL_DIRS")
    if raw:
        dirs = [d.strip() for d in raw.split(":") if d.strip()]
    else:
        dirs = [_DEFAULT_SKILLS_DIR]

    # Only include directories that exist and contain subdirectories
    valid = []
    for d in dirs:
        p = Path(d)
        if p.is_dir() and any(child.is_dir() for child in p.iterdir()):
            valid.append(str(p))
            skills = [child.name for child in p.iterdir() if child.is_dir() and (child / "SKILL.md").exists()]
            logger.info(f"Skill directory {d}: found skills {skills}")
        else:
            logger.info(f"Skill directory {d}: no skills found (skipping)")

    return valid if valid else None


def _resolve_acl_path() -> str | None:
    """Resolve the tool ACL file path."""
    path = os.getenv("TOOL_ACL_PATH", _DEFAULT_ACL_PATH)
    if Path(path).is_file():
        return path
    return None


async def main() -> None:
    mcp_servers = _load_mcp_config()
    skill_dirs = _load_skill_directories()
    acl_path = _resolve_acl_path()

    # Build session config with discovered skills and MCP servers
    config_kwargs: dict = {}
    if mcp_servers:
        config_kwargs["mcp_servers"] = mcp_servers
    if skill_dirs:
        config_kwargs["skill_directories"] = skill_dirs

    session_config = SessionConfig(**config_kwargs) if config_kwargs else None

    if session_config:
        logger.info(f"Session config: mcp_servers={bool(mcp_servers)}, skill_directories={skill_dirs}")
    else:
        logger.info("No skills or MCP servers configured — running with defaults")

    agent = from_copilot(session_config=session_config, acl_path=acl_path)
    await agent.run_async()


if __name__ == "__main__":
    asyncio.run(main())
