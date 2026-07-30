# dSPACE ControlDesk MCP Server

This MCP server automates dSPACE ControlDesk through its COM automation interface.
It lets MCP clients use ControlDesk for application lifecycle, projects and
experiments, platforms, measurement and calibration, variables, instruments,
layouts, recorder operations, and bus logging, monitoring, and replay.

ControlDesk MCP provides a controlled way for AI-assisted workflows to inspect
and operate an existing ControlDesk setup while preserving the normal
ControlDesk project and experiment workflow.

> **Early release:** This MCP server is an initial release. dSPACE plans to
> extend and improve the server — additional tools, improved AI guidance, and
> broader workflow coverage — in future releases.

## Prerequisites

- **Windows** with dSPACE ControlDesk installed and licensed.
  ControlDesk 2025-A or later is supported; ControlDesk 2026-A is recommended.
- **An MCP-compatible client application** that supports the Model Context
  Protocol (MCP) and can launch and communicate with MCP servers via the STDIO
  transport. Examples:
  - Visual Studio Code with the GitHub Copilot extension
  - Claude Desktop
  - Cursor or Claude Code
- **PowerShell** — available by default on Windows; required to run the server
  launcher script and development scripts.

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

The executable contains the Python runtime and all server dependencies (including
the MCP SDK). It does not require a separate Python, `uv`, or any additional
package installation.

### Source checkout

Use this workflow only when developing or running a local checkout. Install a
64-bit Python 3.11 or newer and `uv` from
<https://docs.astral.sh/uv/getting-started/installation/>.

> **Note:** The released executable already bundles the Python runtime and
> all dependencies, including the MCP SDK (FastMCP). A separate Python
> installation is only needed for development from source.

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

> **How the MCP server runs:** Despite the name "server", ControlDesk MCP runs
> as a **local subprocess** launched by the MCP client on the same Windows
> machine as ControlDesk. It communicates over **stdin/stdout** (STDIO
> transport) and is not accessible from outside the local machine. It is not a
> multi-user server and does not open any network port in the default
> configuration.

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

> **ControlDesk VEOS platform:** When a VEOS platform is configured in the
> experiment, `controldesk_platform_connect(...)` starts the VEOS process via
> its command-line interface rather than COM. All subsequent measurement,
> calibration, and variable operations then proceed the same as with hardware
> platforms. Ensure the VEOS executable is correctly configured in the
> ControlDesk experiment before connecting.

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
- **Verify the server without an AI client:** run `ControlDeskMCP.exe --list-tools`
  from a terminal to confirm the server starts and registers tools independently of
  any MCP client.
- **Test the COM API independently:** open PowerShell and check that ControlDesk
  COM automation is reachable before using the MCP server:

  ```powershell
  $app = New-Object -ComObject ControlDeskNG.Application
  $app.GetType().FullName
  ```

  If this fails, the COM server is not registered or ControlDesk is not installed
  correctly. Fix the ControlDesk installation before troubleshooting the MCP server.
- **MCP client cannot launch the server or sees no tools:** verify the absolute
  path to `ControlDeskMCP.exe` in the client configuration is correct and the file
  exists. In VS Code, confirm that Copilot is signed in and that `mcp.json` is
  valid. Some clients require explicit permission to launch subprocess executables.

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
- [dSPACE Support](https://www.dspace.com/en/pub/home/support.cfm): official
  user documentation, installation guides, COM API reference, and product support.

## Support

For questions and issues related to this MCP server, open a
[GitHub issue](https://github.com/dspace-group/ControlDeskMCP/issues).

For questions about dSPACE ControlDesk itself — installation, licensing, COM
API, or product behavior — contact dSPACE support:

- Web: <https://www.dspace.com/en/pub/home/support.cfm>
- dSPACE GmbH, Rathenaustraße 26, 33102 Paderborn, Germany

## License

Copyright 2026 dSPACE GmbH

Licensed under the [Apache License, Version 2.0](LICENSE.txt). You may not use
this software except in compliance with the License. A copy of the License is
included in this repository as `LICENSE.txt`.

Unless required by applicable law or agreed to in writing, software distributed
under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
CONDITIONS OF ANY KIND. See the License for the specific language governing
permissions and limitations under the License.
