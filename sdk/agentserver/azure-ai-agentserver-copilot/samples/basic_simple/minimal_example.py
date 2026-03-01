# Copyright (c) Microsoft. All rights reserved.

"""Minimal example: custom agent with @-mention routing.

Registers a custom agent named ``pirate`` that responds in pirate speak,
then starts the server.  To test::

    # Non-streaming — routes to the pirate agent via @pirate prefix
    curl -sS -H "Content-Type: application/json" \
      -X POST http://localhost:8088/responses \
      -d '{"input":"@pirate What is the capital of France?","stream":false}'

    # Streaming
    curl -N -H "Content-Type: application/json" \
      -X POST http://localhost:8088/responses \
      -d '{"input":"@pirate Explain Python decorators.","stream":true}'

    # Without @pirate — uses default Copilot behaviour
    curl -sS -H "Content-Type: application/json" \
      -X POST http://localhost:8088/responses \
      -d '{"input":"What is the capital of France?","stream":false}'
"""

import asyncio

from copilot.types import CustomAgentConfig

from azure.ai.agentserver.copilot import from_copilot


async def main() -> None:
    agent = from_copilot(
        session_config={
            "model": "gpt-5",
            "custom_agents": [
                CustomAgentConfig(
                    name="pirate",
                    display_name="Pirate Agent",
                    description="Answers every question in pirate speak.",
                    prompt=(
                        "You are a pirate. You MUST answer every question "
                        "entirely in pirate speak. Use pirate slang, say "
                        "'Arrr', 'matey', 'ye', 'shiver me timbers', etc. "
                        "Never break character."
                    ),
                    infer=True,
                ),
            ],
        },
    )
    await agent.run_async()


if __name__ == "__main__":
    asyncio.run(main())
