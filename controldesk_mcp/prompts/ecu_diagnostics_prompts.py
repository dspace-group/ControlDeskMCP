"""MCP prompts for ControlDesk ECU Diagnostics workflows.

Prompts registered:
  ecu_diagnostics_setup_workflow       — End-to-end guide: add platform → load ODX →
                                         select vehicle → configure link → connect
  ecu_diagnostics_link_configuration   — Focused guide for protocol/interface config only

ECU Diagnostics tools used across these prompts:
    Platform:     controldesk_platform_manage, controldesk_platform_connect
    DB setup:     controldesk_ecu_diagnostics_setup
    Link setup:   controldesk_ecu_diagnostics_link_setup
    Add-ons:      controldesk_ecu_diagnostics_db_manage,
                  controldesk_ecu_diagnostics_vehicle_manage,
                  controldesk_ecu_diagnostics_link_manage

Layer: MCP Prompt adapter — pure Python; no COM or service calls.
"""

from __future__ import annotations

from controldesk_mcp.server.app import mcp

# ── Prompt 1 — ECU Diagnostics Setup Workflow ─────────────────────────────────


@mcp.prompt(
    name="ecu_diagnostics_setup_workflow",
    description=(
        "End-to-end guide for setting up a ControlDesk ECU Diagnostics session: "
        "create Diagnostic2 platform, load ODX database, select vehicle, "
        "configure logical link with protocol and interface, then connect. "
        "Accepts optional platform_name and odx_directory_path to pre-fill steps."
    ),
)
def ecu_diagnostics_setup_workflow(
    platform_name: str = "ECU Diagnostics",
    odx_directory_path: str = "",
    vehicle_name: str = "",
    link_name: str = "",
    protocol: str = "ISO_14229_UDS",
    physical_connection: str = "CAN",
    vendor_name: str = "dSPACE",
    interface_name: str = "Virtual",
    channel_index: int = 0,
) -> list[dict]:
    """Generate an ECU Diagnostics end-to-end setup workflow prompt."""
    odx_arg = odx_directory_path or "C:\\\\<path>\\\\<ODX_folder>"
    vehicle_arg = vehicle_name or "<vehicle_short_name>"
    link_arg = link_name or "<link_short_name>"

    return [
        {
            "role": "user",
            "content": (
                f"Set up an ECU Diagnostics session in ControlDesk.\n\n"
                f"**Parameters:**\n"
                f"- Platform name: {platform_name}\n"
                f"- ODX directory: {odx_arg}\n"
                f"- Vehicle: {vehicle_arg}\n"
                f"- Logical link: {link_arg}\n"
                f"- Protocol: {protocol}\n"
                f"- Physical connection: {physical_connection}\n"
                f"- Vendor: {vendor_name} / Interface: {interface_name} "
                f"/ Channel: {channel_index}\n\n"
                f"**Steps — execute in order:**\n\n"
                f"1. Create the Diagnostic2 platform:\n"
                f"   `controldesk_platform_manage(action='add', "
                f"platform_type='Diagnostic2')`\n"
                f"   → note the returned platform name (e.g. '{platform_name}').\n\n"
                f"2. Load the ODX database:\n"
                f"   `controldesk_ecu_diagnostics_setup(action='add_odx_directory', "
                f"platform_name='{platform_name}', directory_path='{odx_arg}')`\n"
                f"   → this also sets DisplayStatusInformation=False to suppress "
                f"UI dialogs.\n\n"
                f"3. List available vehicles:\n"
                f"   `controldesk_ecu_diagnostics_link_setup(action='list_vehicles', "
                f"platform_name='{platform_name}')`\n"
                f"   → pick a vehicle short_name from the response.\n\n"
                f"4. Select the vehicle:\n"
                f"   `controldesk_ecu_diagnostics_link_setup(action='select_vehicle', "
                f"platform_name='{platform_name}', vehicle_name='{vehicle_arg}')`\n\n"
                f"5. List logical links:\n"
                f"   `controldesk_ecu_diagnostics_link_setup("
                f"action='list_logical_links', "
                f"platform_name='{platform_name}')`\n"
                f"   → pick a link short_name from the response.\n\n"
                f"6. Configure the logical link (protocol + physical connection):\n"
                f"   `controldesk_ecu_diagnostics_link_setup("
                f"action='configure_logical_link', "
                f"platform_name='{platform_name}', link_name='{link_arg}', "
                f"protocol='{protocol}', "
                f"physical_connection='{physical_connection}')`\n\n"
                f"7. List available interfaces for the link:\n"
                f"   `controldesk_ecu_diagnostics_link_setup(action='list_interfaces', "
                f"platform_name='{platform_name}', link_name='{link_arg}')`\n"
                f"   → pick vendor_name and interface_name from the response.\n\n"
                f"8. Select the interface channel:\n"
                f"   `controldesk_ecu_diagnostics_link_setup(action='select_interface', "
                f"platform_name='{platform_name}', link_name='{link_arg}', "
                f"vendor_name='{vendor_name}', interface_name='{interface_name}', "
                f"channel_index={channel_index})`\n\n"
                f"9. Connect the platform:\n"
                f"   `controldesk_platform_connect(platform_name='{platform_name}')`\n\n"
                f"10. Report: platform name, ODX files loaded, selected vehicle, "
                f"configured link, interface selection, and connection state."
            ),
        }
    ]


# ── Prompt 2 — ECU Diagnostics Link Configuration ────────────────────────────


@mcp.prompt(
    name="ecu_diagnostics_link_configuration",
    description=(
        "Focused guide for configuring the logical link protocol and interface "
        "on an existing Diagnostic2 platform. Use when the platform and ODX "
        "database are already loaded and a vehicle has been selected, and only "
        "the link protocol or interface needs to be changed."
    ),
)
def ecu_diagnostics_link_configuration(
    platform_name: str = "ECU Diagnostics",
    link_name: str = "",
    protocol: str = "ISO_14229_UDS",
    physical_connection: str = "CAN",
) -> list[dict]:
    """Generate a focused logical-link configuration prompt."""
    link_arg = link_name or "<link_short_name>"

    return [
        {
            "role": "user",
            "content": (
                f"Configure the logical link for ECU Diagnostics on platform "
                f"'{platform_name}'.\n\n"
                f"**Parameters:**\n"
                f"- Platform: {platform_name}\n"
                f"- Logical link: {link_arg}\n"
                f"- Protocol: {protocol}\n"
                f"- Physical connection: {physical_connection}\n\n"
                f"**Steps — execute in order:**\n\n"
                f"1. (If needed) List logical links to find the correct name:\n"
                f"   `controldesk_ecu_diagnostics_link_setup("
                f"action='list_logical_links', "
                f"platform_name='{platform_name}')`\n\n"
                f"2. Select the logical link:\n"
                f"   `controldesk_ecu_diagnostics_link_setup("
                f"action='select_logical_link', "
                f"platform_name='{platform_name}', link_name='{link_arg}')`\n\n"
                f"3. Configure protocol and physical connection:\n"
                f"   `controldesk_ecu_diagnostics_link_setup("
                f"action='configure_logical_link', "
                f"platform_name='{platform_name}', link_name='{link_arg}', "
                f"protocol='{protocol}', "
                f"physical_connection='{physical_connection}')`\n\n"
                f"4. List available interfaces for the link:\n"
                f"   `controldesk_ecu_diagnostics_link_setup(action='list_interfaces', "
                f"platform_name='{platform_name}', link_name='{link_arg}')`\n"
                f"   → note vendor names and interface names.\n\n"
                f"5. Select an interface channel:\n"
                f"   `controldesk_ecu_diagnostics_link_setup(action='select_interface', "
                f"platform_name='{platform_name}', link_name='{link_arg}', "
                f"vendor_name='<vendor>', interface_name='<interface>', channel_index=0)`\n\n"
                f"6. Verify by listing the link again or checking platform state.\n\n"
                f"7. Report: configured protocol, physical connection, and selected interface."
            ),
        }
    ]
