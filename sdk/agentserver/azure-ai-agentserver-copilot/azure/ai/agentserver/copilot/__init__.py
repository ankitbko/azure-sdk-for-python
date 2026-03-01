# ---------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# ---------------------------------------------------------
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

import os
from typing import Optional, Union

from copilot import SessionConfig
from copilot.types import SystemMessageConfig

from ._version import VERSION


def from_copilot(
    session_config: Optional[SessionConfig] = None,
    *,
    acl_path: Optional[Union[str, os.PathLike]] = None,
    system_message: Optional[Union[str, SystemMessageConfig]] = None,
):
    """Create a CopilotAdapter agent server from a Copilot SessionConfig.

    System Message
    ----------------
    You can customise the system prompt that the Copilot session uses.
    Pass a plain string to **append** to the default Copilot system prompt,
    or a :class:`~copilot.types.SystemMessageConfig` dict for full control
    over the mode (``"append"`` or ``"replace"``).

    The ``COPILOT_SYSTEM_MESSAGE`` environment variable is also supported
    (treated as ``append`` mode).  An explicit *system_message* parameter
    takes priority over the environment variable, which in turn takes
    priority over any ``system_message`` key inside *session_config*.

    Tool Access Control List (ACL)
    --------------------------------
    The ACL controls which tools the Copilot agent is permitted to call.
    You can supply it via *acl_path* or the ``TOOL_ACL_PATH`` environment
    variable.  If neither is set, **every tool request is auto-approved**
    (convenient for local development, but not recommended for production).

    See :class:`~azure.ai.agentserver.copilot.tool_acl.ToolAcl` and the
    ``samples/hosted_agent/tools_acl.yaml`` example for the YAML schema.

    :param session_config: Configuration for the Copilot session (model etc.).
    :type session_config: Optional[SessionConfig]
    :param acl_path: Path to a YAML tool ACL file.  Takes priority over the
        ``TOOL_ACL_PATH`` environment variable.
    :type acl_path: Optional[str | os.PathLike]
    :param system_message: System message for the Copilot session.  A plain
        string is treated as ``{"mode": "append", "content": text}``.
        A :class:`~copilot.types.SystemMessageConfig` dict gives full control.
    :type system_message: Optional[str | SystemMessageConfig]
    :return: A CopilotAdapter instance ready to run.
    :rtype: CopilotAdapter
    """
    from .copilot_adapter import CopilotAdapter
    from .tool_acl import ToolAcl

    acl = ToolAcl.from_file(acl_path) if acl_path is not None else None
    return CopilotAdapter(session_config=session_config, acl=acl, system_message=system_message)


__all__ = ["from_copilot", "ToolAcl"]
__version__ = VERSION
