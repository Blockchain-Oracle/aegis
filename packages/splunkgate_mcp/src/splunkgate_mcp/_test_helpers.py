"""Test-only helpers that bypass FastMCP's async protocol surface.

FastMCP exposes registered tools via the MCP protocol's async `tools/list`
method (returning over JSON-RPC). For unit tests we want sync inspection
of the registry without spinning up the protocol harness. The internal
`_REGISTERED_TOOLS` dict in `server.py` is the canonical source — this
module exposes it as a list under a test-only name.

This module's name starts with an underscore so it's never accidentally
imported from production code; downstream tool stories (mcp-02 through
mcp-05) import it only inside their `tests/` modules.
"""

from __future__ import annotations

from splunkgate_mcp.server import _REGISTERED_TOOLS, RegisteredTool


def list_tools_for_test() -> list[RegisteredTool]:
    """Return the values of the internal `_REGISTERED_TOOLS` registry."""
    return list(_REGISTERED_TOOLS.values())
