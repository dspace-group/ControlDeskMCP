"""Service layer (Facade) — business orchestration between MCP tools and the COM bridge.

Each service module owns:
  - Deciding which COM methods to call and in what order
  - Formatting results from raw COM dicts into JSON strings
  - Handling BridgeError and converting to error envelopes

Strict rules:
  - Service modules MUST NOT import from controldesk_mcp.server or controldesk_mcp.tools
  - Service modules MUST NOT import win32com, comtypes, or pythoncom
  - Service modules call com_bridge ONLY through com_bridge.dispatch()
    and com_bridge.get_connection() — no direct domain internals
"""
