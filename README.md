# dSPACE ControlDesk MCP Server

This MCP server automates dSPACE ControlDesk through its COM automation interface.
It lets MCP clients use ControlDesk for application lifecycle, projects and
experiments, platforms, measurement and calibration, variables, instruments,
layouts, recorder operations, and bus logging, monitoring, and replay.

ControlDesk MCP provides a controlled way for AI-assisted workflows to inspect
and operate an existing ControlDesk setup while preserving the normal
ControlDesk project and experiment workflow.

## Prerequisites

- Windows with dSPACE ControlDesk installed and licensed
- A 64-bit Python 3.11 or newer installation
- `uv`, the Python package and project manager used by the command launcher.
  Install it from the official Astral documentation:
  <https://docs.astral.sh/uv/getting-started/installation/>
- An MCP client, such as Visual Studio Code, Cursor, Claude Code, or Claude Desktop

Set `CONTROLDESK_VERSION` to a version such as `2026-A` when a specific
ControlDesk version is required. Leave it unset to use the newest detected
installation.

## Installation

1. Clone the repository and open its root folder.
2. Create the project environment and install the runtime dependencies:

    ```powershell
    uv sync
    ```

3. For local development, install the development dependencies as well:

    ```powershell
    uv sync --extra dev
    ```

## Using With an MCP Client

1. In your MCP client, add a new **stdio** MCP server.
2. Configure the server to call [ControlDeskMCP.cmd](ControlDeskMCP.cmd). The
   launcher uses `uv` in the repository directory and starts `python -m sources.main`.

    ```powershell
    C:\path\to\ControlDeskMCP\ControlDeskMCP.cmd
    ```

    For example, configure the server in `.vscode/mcp.json` as follows:

    ```json
    {
        "servers": {
            "ControlDesk MCP": {
                "type": "stdio",
                "command": "C:\\path\\to\\ControlDeskMCP\\ControlDeskMCP.cmd",
                "args": []
            }
        }
    }
    ```

    To select a particular installed ControlDesk release, add an environment value:

    ```json
    {
        "env": {
            "CONTROLDESK_VERSION": "2026-A"
        }
    }
    ```

3. Reload or reconnect MCP servers in the client.

The workspace configuration in [.vscode/mcp.json](.vscode/mcp.json) is useful
for development. For a cloned checkout used outside VS Code, prefer the
`ControlDeskMCP.cmd` configuration above because it resolves the repository
location itself.

## Typical ControlDesk Workflow

The appropriate sequence depends on the task, but a normal online workflow is:

1. `start_controldesk(...)`
2. `project_open(...)` or `project_discover(...)`
3. `platform_manage(...)` and `platform_connect(...)`, when communication with
   an ECU or virtual platform is required
4. Use the required measurement, calibration, variable, recording, or bus tool
5. Stop active measurement, calibration, and recorder operations before calling
   `platform_disconnect(...)`
6. Call `stop_controldesk(...)` only when ControlDesk should be closed

Use the relevant `*_discover()` tool when a domain offers additional on-demand
operations. Tool calls return structured results; failures contain an error code,
retryability indicator, and recovery hint.

## Available MCP Tool Domains

- Application lifecycle and ControlDesk windows
- Projects and experiments
- Platforms and online connections
- Measurements, triggers, and data loggers
- Online calibration and calibration data sets
- Variables and variable descriptions
- Instruments and layouts
- Recorder Main
- Bus logging, bus monitoring, and bus replay

The complete, current catalog is available through the MCP resources
`controldesk://server/tool-catalog` and `controldesk://server/tool-groups`.

## Development

Run the uv-based setup once after cloning:

```powershell
.\scripts\setup.ps1
```

Run the quality gate after changes:

```powershell
.\scripts\quality-gate.ps1
```

Start the MCP Inspector to browse tool schemas and test calls. Node.js 18 or
newer must be available on `PATH`.

```powershell
.\scripts\inspect.ps1
```

For direct local debugging, use:

```powershell
.\scripts\debug.ps1
```

Integration tests need a live ControlDesk installation and are skipped by the
normal quality gate. Run them explicitly when needed:

```powershell
uv run pytest -m integration
```

## Troubleshooting

- **`uv` is not recognized:** install `uv` and open a new terminal so it is on `PATH`.
- **Python version or bitness error:** use 64-bit Python 3.11 or newer.
- **ControlDesk is not found:** verify the installation and license; optionally
  set `CONTROLDESK_VERSION` to the installed release, for example `2026-A`.
- **COM call is blocked or rejected:** close modal dialogs in ControlDesk and retry.
- **A tool call times out or ControlDesk exits:** call `app_get_logs(...)` for
  candidate ControlDesk log files, then restart and reattach with `start_controldesk(...)`.

## Further Documentation

- [MCP Inspector guide](docs/mcp-inspector.md)
- [Client configuration and examples](docs/clients.md)
- [Server architecture](docs/architecture.md)
- [Error handling](docs/error-handling.md)
- [Contributing guide](CONTRIBUTING.md)
