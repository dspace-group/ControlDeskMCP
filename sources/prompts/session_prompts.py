"""MCP prompts for ControlDesk session setup and connection diagnosis.

Prompts registered:
  start_automation_session — full session setup: app → project → platform
  diagnose_connection      — troubleshoot COM / connection failures

Layer: MCP Prompt adapter — pure Python; no COM or service calls.
"""

from __future__ import annotations

from sources.server.app import mcp

# ── Prompt — Start Automation Session ─────────────────────────────────────────


@mcp.prompt(
    name="start_automation_session",
    description=(
        "Step-by-step guide for setting up a full ControlDesk automation session: "
        "verify server, start the application, open a project, connect a platform, "
        "and confirm the environment is ready. "
        "Use at the beginning of any automation workflow."
    ),
)
def start_automation_session(
    project_path: str = "",
    platform_name: str = "",
    controldesk_version: str = "",
) -> list[dict]:
    """Generate a session setup workflow prompt."""
    version_clause = f" (version `{controldesk_version}`)" if controldesk_version else ""
    version_arg = f", controldesk_version='{controldesk_version}'" if controldesk_version else ""
    project_arg = f", project_path='{project_path}'" if project_path else ""
    platform_arg = f", platform_name='{platform_name}'" if platform_name else ""

    return [
        {
            "role": "user",
            "content": (
                f"Set up a ControlDesk automation session{version_clause}.\n\n"
                f"**Required steps — execute in order:**\n\n"
                f"1. Read the resource `controldesk://server/info` to confirm the server is "
                f"reachable and report its version.\n"
                f"2. Call `start_controldesk`{version_arg} to launch or attach to ControlDesk. "
                f"   Report whether a new instance was started or an existing one was attached.\n"
                f"3. Read the resource `controldesk://server/connection-status` to confirm the "
                f"   bridge state.\n"
                f"4. If a project path was provided: call `project_open`{project_arg} and confirm "
                f"   the project opened successfully.\n"
                f"5. If a platform was specified: call `platform_connect`{platform_arg}, then "
                f"   call `platform_get_connection_state` to verify.\n"
                f"6. Summarise the session state: ControlDesk version, open project, platform "
                f"   connection state, and any warnings."
            ),
        }
    ]


# ── Prompt — Diagnose Connection ──────────────────────────────────────────────


@mcp.prompt(
    name="diagnose_connection",
    description=(
        "Diagnostic guide for troubleshooting ControlDesk COM / connection failures. "
        "Use when tools return BridgeError, RPC errors, or unexpected disconnections. "
        "Accepts an optional error message and the failing tool name for context."
    ),
)
def diagnose_connection(
    error_message: str = "",
    tool_name: str = "",
) -> list[dict]:
    """Generate a connection-diagnosis workflow prompt."""
    error_context = f"\n\n**Error reported:** `{error_message}`" if error_message else ""
    tool_context = f" (reported while calling `{tool_name}`)" if tool_name else ""

    return [
        {
            "role": "user",
            "content": (
                f"Diagnose a ControlDesk connection problem{tool_context}.{error_context}\n\n"
                f"**Diagnostic sequence — work through each step and report findings:**\n\n"
                f"1. Read the resource `controldesk://server/info` — if this fails, the MCP "
                f"   server process is not running; stop here and report.\n"
                f"2. Read `controldesk://server/connection-status` to get the current bridge "
                f"   state (NOT_STARTED / DISCONNECTED / CONNECTED / FAILED).\n"
                f"3. Read `controldesk://server/info` to confirm which server version and "
                f"   ControlDesk target version are configured.\n"
                f"4. If state is NOT_STARTED or DISCONNECTED: call `start_controldesk` "
                f"   and repeat step 2.\n"
                f"5. If state is FAILED or the error mentions HRESULT / RPC_E_DISCONNECTED: "
                f"   ControlDesk may have crashed. Advise restarting ControlDesk manually, "
                f"   then calling `start_controldesk` again.\n"
                f"6. Call `platform_list` to see registered platforms; call "
                f"   `platform_get_connection_state` for each to check platform-level health.\n"
                f"7. Provide a concise root-cause assessment and the recommended fix."
            ),
        }
    ]
