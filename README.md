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
- An MCP client, such as Visual Studio Code, Cursor, Claude Code, or Claude Desktop

Set `CONTROLDESK_VERSION` to a version such as `2026-A` when a specific
ControlDesk version is required. Leave it unset to use the newest detected
installation.

## Installation

### Released executable

1. Download `ControlDeskMCP.exe` and `ControlDeskMCP.exe.sha256` from the
   required GitHub release.
2. Verify the download:

    ```powershell
    (Get-FileHash .\ControlDeskMCP.exe -Algorithm SHA256).Hash
    ```

    Compare the result with `ControlDeskMCP.exe.sha256` from the same release.

3. Configure the MCP client to execute the downloaded `ControlDeskMCP.exe`.

The executable contains the Python runtime and server dependencies. It does not
require a separate Python or `uv` installation.

### Source checkout

Use this workflow only when developing or running a local checkout. Install a
64-bit Python 3.11 or newer and `uv` from
<https://docs.astral.sh/uv/getting-started/installation/>.

1. Clone the repository and open its root folder.
2. Create the project environment and install runtime dependencies:

    ```powershell
    uv sync
    ```

3. For local development, install the development dependencies as well:

    ```powershell
    uv sync --extra dev
    ```

`uv sync` is the developer workflow and may refresh `uv.lock` when dependency
metadata changes. The lockfile is committed; CI and release automation use
locked installs and fail when it needs to be regenerated. Update it
intentionally with `uv lock` whenever declared dependencies change.

## Using With an MCP Client

1. In your MCP client, add a new **stdio** MCP server.
2. Configure the server to call the released executable. For a source checkout,
   use [ControlDeskMCP.cmd](ControlDeskMCP.cmd), which starts the server through
   `uv` from the repository directory.

    ```powershell
    C:\path\to\ControlDeskMCP\ControlDeskMCP.exe
    ```

    For example, configure the server in `.vscode/mcp.json` as follows:

    ```json
    {
        "servers": {
            "controlDesk": {
                "type": "stdio",
                "command": "C:/path/to/ControlDeskMCP/ControlDeskMCP.exe",
                "args": [],
                "cwd": "${workspaceFolder}"
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
for source development. A released executable can be placed in a stable
directory and referenced by its absolute path.

## Typical ControlDesk Workflow

The appropriate sequence depends on the task, but a normal online workflow is:

1. `controldesk_app_start_or_attach(...)`
2. `controldesk_project_open(...)` or `controldesk_project_discover(...)`
3. `controldesk_platform_manage(...)` and `controldesk_platform_connect(...)`, when communication with
   an ECU or virtual platform is required
4. Use the required measurement, calibration, variable, recording, or bus tool
5. Stop active measurement, calibration, and recorder operations before calling
   `controldesk_platform_disconnect(...)`
6. Call `controldesk_app_stop(...)` only when ControlDesk should be closed

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

## Dynamic Tool Discovery

ControlDesk MCP uses a **two-tier tool model** to keep the LLM's context window lean:

| Tier                            | Description                                                                               |
| ------------------------------- | ----------------------------------------------------------------------------------------- |
| **MAIN tools** (always visible) | Entry points, discovery tools, and lifecycle operations — always present in `tools/list`. |
| **ADD-ON tools** (on-demand)    | Per-domain helper tools, loaded only after a `*_discover` call activates that domain.     |

When an ADD-ON domain is activated the server emits a `notifications/tools/list_changed`
notification so clients that support it (VS Code Copilot, Claude Code, etc.) refresh their
tool list automatically.

**TTL eviction:** an idle ADD-ON domain is evicted after `TOOL_TTL_SECONDS` (default: 120 s)
of inactivity. Stateful domains (`bus_logging`, `bus_monitor`, `bus_replay`, `measurement`,
`recorder`) are **never** auto-evicted while a session is running.

**Typical sequence:** call `*_discover` to activate a domain → use its ADD-ON tools →
the domain expires when unused; call `*_discover` again to reactivate if needed.

## Server Verification

The following commands run without a live ControlDesk installation:

```powershell
# Print the server version
ControlDeskMCP.cmd --version

# List all registered tools
ControlDeskMCP.cmd --list-tools

# List all registered resources
ControlDeskMCP.cmd --list-resources

# List all registered prompts
ControlDeskMCP.cmd --list-prompts
```

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
- **A tool call times out or ControlDesk exits:** call `controldesk_app_get_logs(...)` for
  candidate ControlDesk log files, then restart and reattach with `controldesk_app_start_or_attach(...)`.
- **Variable lookup is ambiguous:** allow resolver fallback to complete, review the
  top candidates returned by `resolution_details`, and retry with the selected
  candidate path.
- **Grouped instrument phrases resolve poorly:** run variable discovery/list-all,
  verify the active variable description, and retry with the same phrase.

## Further Documentation

- [Documentation index](docs/README.md)
- [MCP Inspector guide](docs/mcp-inspector.md)
- [Client configuration and examples](docs/clients.md)
- [Server architecture](docs/architecture.md)
- [Error handling](docs/error-handling.md)
- [Release verification and artifact policy](docs/release.md)
- [Variable resolution behavior and operator guide](docs/variable-resolution.md)
- [Contributing guide](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Changelog](CHANGELOG.md)
