# ControlDesk MCP Server — Architecture

> **Scope:** Everything from the MCP host connection down to the COM automation layer.
> **Language:** Python 3.11+ · **Framework:** FastMCP (official MCP SDK) · **Target:** ControlDesk COM automation (`ControlDeskNG.Application.2026-A`)

---

## Table of Contents

1. [Project Structure](#1-project-structure)
2. [Five-Layer Architecture](#2-five-layer-architecture)
3. [Layer Rules](#3-layer-rules)
4. [Transport & Protocol Layer (L1)](#4-transport--protocol-layer-l1)
5. [Tools Layer (L2)](#5-tools-layer-l2)
6. [COM Bridge Layer (L5)](#6-com-bridge-layer-l5)
7. [Tool Design Contract](#7-tool-design-contract)
8. [Key Files](#8-key-files)
9. [Dependency Stack](#9-dependency-stack)

---

## 1. Project Structure

```
root/
│
├── AGENTS.md                          ✅ AI agent context (non-obvious knowledge only)
├── pyproject.toml                     ✅ PEP 517 project + pip/hatch deps
├── README.md                          ✅
│
├── controldesk_mcp/                           ✅ Python MCP server package
│   ├── __init__.py                    ✅
│   ├── __main__.py                    ✅ `python -m controldesk_mcp` support
│   ├── main.py                        ✅ Entry point — runs FastMCP via stdio/HTTP
│   │
│   ├── server/                        ✅ MCP server bootstrap
│   │   ├── __init__.py                ✅
│   │   ├── app.py                     ✅ FastMCP instance + lifespan (COM bridge startup/shutdown)
│   │   └── registry.py                ✅ Single import point for all tools, resources, prompts
│   │
│   ├── tools/                         ✅ MCP tool adapters (thin @mcp.tool wrappers only)
│   │   ├── __init__.py                ✅
│   │   ├── application/               ✅ Domain: app lifecycle (attach, quit, window state)
│   │   ├── bus_logging/               ✅ Domain: bus logger, filter management
│   │   ├── bus_monitor/               ✅ Domain: bus monitor management
│   │   ├── bus_replay/                ✅ Domain: bus replay management
│   │   ├── calibration/               ✅ Domain: online calibration, proposed calibration
│   │   ├── measurement/               ✅ Domain: measurement signals, rasters, recorders
│   │   ├── platform/                  ✅ Domain: platform registration, config, connection
│   │   ├── project/                   ✅ Domain: project root, project & experiment lifecycle
│   │   ├── recorder/                  ✅ Domain: main recorder, data loggers, triggers
│   │   ├── tool_window/               ✅ Domain: ControlDesk panel show/hide/dock
│   │   └── variable_management/       ✅ Domain: variable read/write/calibration, data sets
│   │
│   ├── models/                        ✅ Shared Pydantic models
│   │   ├── base.py                    ✅ DictModelMixin, pagination helpers
│   │   ├── errors.py                  ✅ CdError hierarchy + ErrorEnvelope
│   │   ├── envelope_builder.py        ✅ CdError → CallToolResult
│   │   ├── requests.py                ✅ Tool input models (BaseModel per tool)
│   │   └── tooldecorator/
│   │       └── metainfo.py            ✅ ToolDomain, ToolGroup, MCPToolCategory, MetaInfo
│   │
│   ├── config/
│   │   └── settings.py                ✅ pydantic-settings: env vars, COM ProgID, timeouts
│   │
│   ├── resources/                     ✅ MCP resources (read-only context for the LLM)
│   │   ├── server_resources.py        ✅ Server-level resources (info, tool catalog, status)
│   │   └── domain_resources.py        ✅ Domain tool catalog + URI template resource
│   │
│   ├── prompts/                       ✅ Parameterised MCP prompts per domain
│   │   ├── session_prompts.py         ✅
│   │   ├── measurement_prompts.py     ✅
│   │   ├── variable_prompts.py        ✅
│   │   ├── calibration_prompts.py     ✅
│   │   ├── bus_prompts.py             ✅
│   │   └── project_prompts.py         ✅
│   │
│   └── com_bridge/                    ✅ The sealed COM layer — all win32com lives here
│       ├── __init__.py                ✅ Public API: dispatch(), shutdown()
│       ├── sta_thread.py              ✅ STA thread + asyncio.Queue gateway (THE chokepoint)
│       ├── connection.py              ✅ COM connection lifecycle: connect, reconnect, health
│       ├── detector.py                ✅ ControlDesk version/process detection
│       ├── errors.py                  ✅ CdError subclass definitions
│       ├── error_handling/            ✅ Error pipeline components
│       │   ├── hresult.py             ✅ pywintypes.com_error → typed CdError subclass
│       │   ├── guard.py               ✅ COM Guard: STA executor, timeout, retry
│       │   ├── circuit_breaker.py     ✅ Per-interface circuit breaker (CLOSED/OPEN/HALF-OPEN)
│       │   └── preconditions.py       ✅ Domain-state precondition checks
│       └── domains/                   ✅ Per-domain COM wrappers (synchronous, STA-thread only)
│           ├── __init__.py            ✅
│           ├── application_com.py     ✅ IXaApplication / IApplication
│           ├── bus_logging_com.py     ✅ Bus logger & filter COM wrappers
│           ├── bus_monitor_com.py     ✅ Bus monitor COM wrappers
│           ├── bus_replay_com.py      ✅ Bus replay COM wrappers
│           ├── calibration_com.py     ✅ IXaOnlineCalibration wrappers
│           ├── measurement_com.py     ✅ IXaMeasurementConfiguration wrappers
│           ├── platform_com.py        ✅ IXaPlatformManagement wrappers
│           ├── project_com.py         ✅ IXaProject / IXaExperiment wrappers
│           ├── recorder_com.py        ✅ Recorder & data logger COM wrappers
│           ├── tool_window_com.py     ✅ IXaWindows / tool panel wrappers
│           └── variable_com.py        ✅ IXaVariableManagement wrappers
│
├── tests/
│   ├── conftest.py                    ✅ Shared fixtures (mock COM bridge stubs)
│   ├── unit/                          ✅ Pure unit tests — COM mocked at dispatch() boundary
│   │   ├── test_tools/                ✅
│   │   ├── test_com_bridge/           ✅
│   │   ├── test_resources/            ✅
│   │   └── test_prompts/              ✅
│   └── product/                       ✅ Requires live ControlDesk
│       ├── conftest.py                ✅ ComVerifier + session fixtures
│       ├── manual/                    ✅ Tier 1: direct tool call tests (@pytest.mark.product)
│       └── agentic/                   ✅ Tier 2: LLM-driven agentic tests (@pytest.mark.llm_product)
│
├── scripts/
│   ├── quality-gate.ps1               ✅ lint + format + layering check + unit tests
│   ├── inspect.ps1                    ✅ MCP Inspector launcher
│   └── run_product_tests.ps1          ✅ Product test convenience runner
│
└── docs/
    ├── INDEX.md                       ✅ Navigation entry point
    ├── architecture.md                ✅ (this file)
    ├── error-handling.md              ✅ Error taxonomy, CdError hierarchy, envelope builder
    ├── performance.md                 ✅ COM marshaling, STA bottleneck, process overhead
    ├── tool-design.md                 ✅ Tool consolidation, progressive discovery pattern
    ├── testing.md                     ✅ Product test setup, LLM-driven test architecture
    ├── mcp-inspector.md               ✅ Inspector developer guide
    └── tools/                         ✅ Tool specifications per domain
```

---

## 2. Five-Layer Architecture

```
┌─────────────────────────────────────────────┐
│         MCP Host (Claude / VS Code)          │
└───────────────────┬─────────────────────────┘
                    │  stdio / Streamable HTTP
┌───────────────────▼─────────────────────────┐
│  Layer 1 — Transport & Protocol              │
│  server/app.py  — FastMCP Instance           │
│  models/  — Pydantic input/output contracts  │
│  Handles: handshake, validation, logging     │
└───────────────────┬─────────────────────────┘
                    │ tools/
┌───────────────────▼─────────────────────────┐
│  Layer 2 — Tools (thin adapters)             │
│  controldesk_mcp/tools/<domain>/                     │
│  Handles: @mcp.tool decorator only           │
│  Every function body: single-line delegate   │
└───────────────────┬─────────────────────────┘
                    │ calls via com_bridge.dispatch()
┌───────────────────▼─────────────────────────┐
│  Layer 3 — Services / Facade                 │
│  (business logic, COM orchestration,         │
│   BridgeError handling, result mapping)      │
│  Note: may be integrated into tools layer    │
│  or implemented as helpers in com_bridge     │
└───────────────────┬─────────────────────────┘
                    │  com_bridge.dispatch()
┌───────────────────▼─────────────────────────┐
│  Layer 4 — Dispatch Gateway                  │
│  controldesk_mcp/com_bridge/__init__.dispatch()      │
│  Single async crossing point to STA thread  │
│  Timeout + enqueue; returns awaitable Future │
└───────────────────┬─────────────────────────┘
                    │  STA-thread queue
┌───────────────────▼─────────────────────────┐
│  Layer 5 — COM Bridge                        │
│  com_bridge/sta_thread.py — STA + msg loop   │
│  com_bridge/domains/      — per-domain COM   │
│  com_bridge/connection.py — lifecycle        │
│  com_bridge/error_handling/ — HRESULT maps  │
└───────────────────┬─────────────────────────┘
                    │  COM (pywin32)
           ┌────────▼────────┐
           │  ControlDesk.exe │
           │  (COM automation)│
           └─────────────────┘
```

### Why Five Layers

| Layer | Reason |
|---|---|
| L1 — Transport | Separates protocol concerns (Pydantic schema, stderr logging, JSON-RPC) from all domain logic |
| L2 — Tools | Keeps `@mcp.tool` declarations thin so schema/description can be read at a glance |
| L3 — Services | Owns business orchestration and maps COM results to Pydantic models without MCP coupling |
| L4 — Dispatch | Single async entry point to the STA thread — enforces the apartment contract in one place |
| L5 — COM Bridge | Isolates `win32com` and STA threading; protects upper layers from COM apartment bugs |

---

## 3. Layer Rules

**Skipping a layer is forbidden.**

```
Layer 1 (controldesk_mcp/server/, controldesk_mcp/main.py)
    Must NOT: import com_bridge, call COM, check domain state
Layer 2 (controldesk_mcp/tools/)
    Must NOT: contain business logic, call COM, handle BridgeError
    Must NOT: import win32com/comtypes or com_bridge internals (only dispatch)
    Rule: every function body is a single-line service/dispatch delegate
Layer 3 (service helpers)
    Must NOT: import from controldesk_mcp.server or controldesk_mcp.tools
    Must NOT: import win32com/comtypes directly
Layer 4 (com_bridge dispatch gateway)
    Single function: com_bridge.dispatch()
Layer 5 (com_bridge internals)
    Must NOT: import mcp, Context, tools, server, or services
    Must NOT: return pywintypes.com_error or COM objects to callers
```

### Quality Gate Check

```powershell
# scripts/quality-gate.ps1
Select-String `
    -Path "controldesk_mcp/server/*.py","controldesk_mcp/tools/**/*.py" `
    -Pattern "from controldesk_mcp\.com_bridge\.(connection|domains|error_handling|sta_thread)" `
    -Recurse
# Any match = build failure
```

---

## 4. Transport & Protocol Layer (L1)

Layer 1 owns exactly three concerns: handshake, input validation, and protocol logging.

### MCP Initialization Handshake

```
Host → Server:  initialize(protocolVersion, capabilities, clientInfo)
Server → Host:  initialize result(protocolVersion, capabilities, serverInfo)
Host → Server:  initialized (notification)
```

Server capabilities declared:
```json
{
  "protocolVersion": "2024-11-05",
  "capabilities": {
    "tools": { "listChanged": false },
    "logging": {}
  },
  "serverInfo": { "name": "ControlDesk MCP Server", "version": "0.1.0" }
}
```

`listChanged: false` — the tool list is static at startup; no dynamic registration at runtime.

### Startup Validation (lifespan hook)

Before accepting any tool call, `controldesk_mcp/server/app.py` verifies:

1. Python ≥ 3.11 (required for `tomllib`, `asyncio.TaskGroup`)
2. Process bitness = 64-bit (COM automation objects are 64-bit only)
3. All required settings present (`controldesk_mcp/config/settings.py`)

Failure raises `RuntimeError` during lifespan startup — server exits before accepting connections.

### Input Validation Pipeline

```
Host sends tool call
    → 1. Schema presence check (unknown field → protocol error -32601)
    → 2. Pydantic type coercion (type mismatch → ValidationError -32602)
    → 3. Pydantic field validators (constraint violated → ValidationError -32602)
    → Tool logic runs (Layer 2+)
```

Required shape for every tool input model:

```python
class ReadVariableInput(BaseModel):
    variable_path: str = Field(
        description="Full signal path, e.g. 'Model Root/Engine/Speed'.",
        min_length=1,
        examples=["Model Root/Engine/Speed"],
    )
    data_type: str = Field(
        default="auto",
        description="Expected data type: 'float', 'int', 'bool', or 'auto'.",
        pattern=r"^(float|int|bool|auto)$",
    )
```

Rules:
- Every `Field` MUST have a `description` with a concrete example.
- `min_length`, `max_length`, `ge`, `le`, `pattern` must be set wherever applicable.
- No `Optional[X]` without a default value.

### Logging — Non-Negotiable Rule

**The stdio transport uses stdout exclusively for JSON-RPC messages. Any non-JSON byte corrupts the stream.**

- All server-side logging → **stderr only** via structured JSON logger.
- `print()` in production code is a build error — ruff `T201` catches it.
- `logging.basicConfig()` must never be called (defaults to stdout).
- `ctx.info()` / `ctx.warning()` / `ctx.error()` → `notifications/message` channel (safe, JSON-RPC).

```python
# controldesk_mcp/utils/logger.py pattern
handler = logging.StreamHandler(sys.stderr)  # ← stderr, NOT stdout
```

### Argument Naming Rules (enforced)

Every tool argument must be **descriptive, unambiguous snake_case**:

| Forbidden | Correct |
|---|---|
| `arg1`, `p1`, `v` | `variable_path`, `platform_name`, `target_value` |
| `name` (bare) | `experiment_name`, `project_name` |
| `data` (bare) | `measurement_data`, `calibration_value` |
| `type` | `data_type`, `signal_type` |
| `file` | `project_file_path`, `sdf_file_path` |
| `id` (bare) | `experiment_id`, `platform_id` |
| `cfg`, `val` | `recorder_config`, `current_value` |

### Protocol Error Codes

| JSON-RPC Code | Name | When Used |
|---|---|---|
| `-32700` | Parse error | Malformed JSON |
| `-32600` | Invalid Request | Not valid JSON-RPC 2.0 |
| `-32601` | Method not found | Unknown tool name |
| `-32602` | Invalid params | Pydantic `ValidationError` |
| `-32603` | Internal error | Unhandled exception in server |

Domain errors (COM failures, preconditions) are **never** protocol errors — they use `isError: true` in the `result` body. See [error-handling.md](error-handling.md).

### Transport Configuration

| Setting | Default | Description |
|---|---|---|
| `MCP_TRANSPORT` | `stdio` | Transport type: `stdio` or `streamable-http` |
| `MCP_HOST` | `127.0.0.1` | HTTP host (ignored for stdio) |
| `MCP_PORT` | `8000` | HTTP port (ignored for stdio) |
| `LOG_LEVEL` | `INFO` | Python log level for stderr output |

---

## 5. Tools Layer (L2)

### Tool Category System

Tools use `MCPToolCategory` to control registration and context window costs:

| Category | `lazy_loading` | When registered |
|---|---|---|
| `MAIN` | N/A | Always — at server start |
| `ADD_ON` (eager) | `False` | Always — at server start |
| `ADD_ON` (lazy) | `True` | **Never** — deferred; described by Meta-tool |
| `SEARCH` (Meta/Discovery) | N/A | Only when ≥1 lazy ADD_ON exists in domain |

The META tool (`<domain>_discover`) returns a catalogue of all lazy ADD_ON tools. The LLM calls it once to learn what operations exist, then calls the specific manage-tool.

See [tool-design.md](tool-design.md) for the full consolidation pattern and categorisation rules.

### TTL-Based Eviction

Once an ADD_ON domain is activated (via `<domain>_discover`), its tools are registered in the LLM context. Left unchecked, every activated domain accumulates in the context window for the entire session. The TTL eviction mechanism reclaims that context automatically.

**How it works:**

1. Every tool call updates a `_tool_last_used[tool_name]` timestamp (`time.monotonic()`).
2. Each SEARCH (`<domain>_discover`) call triggers `mcp.evict_stale_domains(ttl_seconds, ctx)` before activating any new domain.
3. `evict_stale_domains` checks every currently-active ADD_ON domain. If the most-recent tool call for that domain is older than `tool_ttl_seconds`, the domain is evicted:
   - All its ADD_ON tools are removed from FastMCP's tool manager.
   - The `(fn, kwargs)` pairs are moved back to `_deferred_addon_tools` so the domain can be re-activated on the next discover call.
   - A `tools/list_changed` notification is sent to the client so it re-fetches the tool list.

**Stateful domain protection:**

Domains with long-lived background COM state are **never** auto-evicted, regardless of idle time:

| Protected domain | Reason |
|---|---|
| `BUS_LOGGING` | Logger may be running in the background |
| `BUS_MONITOR` | Monitor captures live frames |
| `BUS_REPLAY` | Replay actively transmits frames |
| `MEASUREMENT` | Measurement session active |
| `RECORDER` | Recorder writing to MF4 file |

**Configuration (`settings.py`):**

| Setting | Default | Description |
|---|---|---|
| `tool_ttl_enabled` | `True` | Enable/disable TTL eviction |
| `tool_ttl_seconds` | `120.0` | Inactivity threshold in seconds (min: 30) |

**Lifecycle (eviction + re-activation):**

```
LLM calls <domain>_discover
    → evict_stale_domains() runs first
        → stale ADD_ON domains removed, tools/list_changed sent
    → requested domain tools activated
        → tools/list_changed sent
LLM calls ADD_ON tool
    → _tool_last_used[tool_name] = time.monotonic()  ← resets TTL
LLM idles > 120 s without touching a domain
    → next discover call evicts that domain
```

MAIN tools and SEARCH tools are **never** evicted — they remain registered for the entire session.

### Tool Annotations

Every tool declares `AnnotationInfo`:

```python
@mcp.tool(
    name="variable_read_scalar",
    annotations=AnnotationInfo(read_only=True, destructive=False, idempotent=True),
    meta=MetaInfo(ToolDomain.VARIABLE, ToolGroup.VARIABLE_READ),
)
```

---

## 6. COM Bridge Layer (L5)

### Why a Dedicated Bridge

ControlDesk COM objects are **apartment-bound**: they must only be called from the thread that created them. FastMCP runs on an asyncio event loop across multiple threads. Without a bridge:

- Any tool handler calling COM runs on the wrong thread.
- Windows raises `RPC_E_WRONGTHREAD` (`0x8001010E`) or silently corrupts state.
- Failure is non-deterministic and hard to reproduce.

The COM bridge is the **single gatekeeper**: one dedicated STA thread owns all COM objects; every tool call crosses into it via a queue.

### STA Threading — Non-Negotiable Rules

| Rule | Consequence of Violation |
|---|---|
| All COM objects **created on the STA thread** | `CoInitializeEx` must be called before `Dispatch()` on the same thread |
| All COM method calls **on the STA thread** | `RPC_E_WRONGTHREAD` → silent data corruption or crash |
| **Never `await`** inside an STA callback | Creates a second event loop on the STA thread → deadlock |
| STA thread must pump Windows messages (`PumpMessages`) | COM callbacks require the message loop |
| `CoUninitialize` called **on teardown on the STA thread** | Leaked COM refs keep ControlDesk.exe alive after server exits |
| **One STA thread** per server process | Multiple STAs add marshaling complexity without benefit |

### Module Map

```
controldesk_mcp/com_bridge/
├── __init__.py             ← Public API: dispatch(), shutdown()
├── sta_thread.py           ← STA thread + asyncio.Queue gateway
├── connection.py           ← COM lifecycle: connect, reconnect, health
├── detector.py             ← ControlDesk version/process detection
├── errors.py               ← CdError subclass definitions
├── error_handling/
│   ├── hresult.py          ← pywintypes.com_error → typed CdError subclass
│   ├── guard.py            ← COM Guard: STA executor, timeout, retry
│   ├── circuit_breaker.py  ← Per-interface circuit breaker
│   └── preconditions.py    ← Domain-state precondition checks
└── domains/                ← Per-domain COM wrappers (11 files)
    ├── application_com.py, bus_logging_com.py, bus_monitor_com.py,
    ├── bus_replay_com.py, calibration_com.py, measurement_com.py,
    ├── platform_com.py, project_com.py, recorder_com.py,
    ├── tool_window_com.py, variable_com.py
```

**Only `dispatch()` from `com_bridge/__init__.py` is imported by code outside `com_bridge/`.**

### STA Thread Data Flow

```
async tool call
      │
      ▼ asyncio
┌─────────────────────────────┐
│  loop.run_in_executor(      │
│    sta_executor,            │
│    _submit, callable, *args │
│  )                          │
└──────────────┬──────────────┘
               │  thread boundary
               ▼ STA thread
┌─────────────────────────────┐
│  _sta_worker()              │
│  while running:             │
│    pythoncom.PumpWaitingMessages()
│    item = queue.get(timeout=0.05)
│    result = item.fn(*item.args)
│    item.future.set_result(result)
└─────────────────────────────┘
               │
               ▼ asyncio (resumes)
   result returned to tool
```

### Startup / Shutdown (lifespan)

```python
# controldesk_mcp/server/app.py
@asynccontextmanager
async def lifespan(app):
    await startup()    # starts STA thread, calls CoInitialize
    try:
        yield
    finally:
        await shutdown()  # stops STA thread, calls CoUninitialize
```

### ProgID Pinning

```python
COM_PROG_ID = "ControlDeskNG.Application.2026-A"
```

Always use the version-pinned ProgID. If `DISP_E_MEMBERNOTFOUND` is raised on a known method at startup → wrong ControlDesk version is running → classified as `CD_VERSION_MISMATCH`.

### Connection State Machine

```
[*] → DISCONNECTED
DISCONNECTED → CONNECTED: connect()
CONNECTED → RECONNECTING: RPC_E_DISCONNECTED / RPC_E_SERVERFAULT
RECONNECTING → CONNECTED: reconnect success
RECONNECTING → FAILED: max_retries exceeded
FAILED → [*]: raises CdConnectionError
```

When `RPC_E_DISCONNECTED` is received, **all cached COM object references must be released** before reconnecting:

```python
def _release_all(self) -> None:
    for attr in ("_app", "_active_experiment", "_platform"):
        obj = getattr(self, attr, None)
        if obj is not None:
            try:
                win32com.client.Dispatch.__del__(obj)
            except Exception:
                pass
            finally:
                setattr(self, attr, None)
    gc.collect()
```

### Disable Modal Dialogs (UI-Blocking Prevention)

Before any long-running operation, disable ControlDesk status dialogs to prevent the COM thread from hanging indefinitely:

```python
for platform in connection.app.ActiveExperiment.Platforms:
    platform.DisplayStatusInformation = False
```

This must be set per-experiment when the experiment is activated.

### HRESULT Classification

`com_bridge/error_handling/hresult.py` converts `pywintypes.com_error` to a typed `CdError`:

```
pywintypes.com_error
    │
    ├── hresult in RETRYABLE_SET → CdBlockedByUiError or CdConnectionError
    ├── facility == FACILITY_RPC (1) → CdConnectionError
    ├── facility == FACILITY_DISPATCH (2) → CdVersionError
    ├── facility == FACILITY_WIN32 (7) → CdSystemError
    └── default → CdOperationError
                  (use IErrorInfo Description — richest text available)
```

Key HRESULT constants:

```python
RPC_E_CALL_REJECTED   = 0x80010001  # STA busy — message box blocking
RPC_E_DISCONNECTED    = 0x80010108  # ControlDesk process died
RPC_E_SERVERFAULT     = 0x80010105  # Exception from COM server
RPC_E_WRONGTHREAD     = 0x8001010E  # Bug in bridge — wrong apartment
CO_E_SERVER_STOPPING  = 0x80004007  # ControlDesk shutting down
DISP_E_MEMBERNOTFOUND = 0x80020003  # Version mismatch
DISP_E_EXCEPTION      = 0x80020009  # ControlDesk app-level error — read IErrorInfo
```

> **Key rule:** `DISP_E_EXCEPTION` (`0x80020009`) is ControlDesk's generic HRESULT for virtually all internal errors. The actual error text is in `IErrorInfo.Description` (`e.args[2][2]`) — not the HRESULT code.

### Domain Wrapper Rules

Each file in `domains/` wraps COM calls for one functional area:

1. **One function per COM operation** — no multi-step COM sequences.
2. **Synchronous only** — no `async def`, no `await`.
3. **Return plain Python types** — `str`, `int`, `float`, `bool`, `list`, `dict`. Never return COM objects.
4. **No error handling** — let `pywintypes.com_error` propagate; `error_handling/hresult.py` classifies it.
5. **Explicit property access** — no `getattr(com_obj, name)` dynamically.

### COM Testing Strategy

**Layer 1 — Unit Tests (full COM mock):** Mock `dispatch()` at the boundary. Test Pydantic validation, JSON response shape, precondition logic.

**Layer 2 — COM Bridge Unit Tests:** Test `sta_thread.py` dispatch queue, timeout logic, HRESULT classification using `pywintypes.com_error` mocks.

**Layer 3 — Integration Tests (live ControlDesk):** Marked `@pytest.mark.integration`. Run with `pytest -m integration`. Skipped in CI with `pytest -m "not integration"`.

See [testing.md](testing.md) for full test setup.

---

## 7. Tool Design Contract

Every tool follows this exact shape:

```python
@mcp.tool(
    name="variable_read_scalar",
    description="Reads the current value of a scalar variable...",
    annotations=AnnotationInfo(read_only=True, destructive=False, idempotent=True),
    meta=MetaInfo(ToolDomain.VARIABLE, ToolGroup.VARIABLE_READ),
)
async def variable_read_scalar(params: VariableReadScalarInput) -> str:
    return await dispatch("variable.read_scalar", params)
```

- Input: `Pydantic BaseModel` with `Field(description=...)` on every field.
- Output: `str` (JSON) — never `dict`, never bare Python types.
- No COM imports — the tool never touches `win32com` or `comtypes`.
- Single-line body delegating to `dispatch()` or a service function.

### JSON-RPC Response Shapes

**Successful tool response:**
```json
{
  "jsonrpc": "2.0", "id": 42,
  "result": {
    "content": [{ "type": "text", "text": "{\"value\": 1234.5, \"unit\": \"rpm\"}" }],
    "isError": false
  }
}
```

**Domain error (isError: true — not a protocol error):**
```json
{
  "jsonrpc": "2.0", "id": 42,
  "result": {
    "content": [{ "type": "text", "text": "## ControlDesk Error\n**Code:** `COM_DISCONNECTED`\n..." }],
    "structuredContent": {
      "error_code": "COM_DISCONNECTED",
      "category": "CONNECTION",
      "retryable": true,
      "recovery_hint": "Call app_start_or_attach to re-establish the COM connection."
    },
    "isError": true
  }
}
```

---

## 8. Key Files

| File | Purpose |
|---|---|
| `controldesk_mcp/main.py` | `mcp.run(transport="stdio")` — nothing else |
| `controldesk_mcp/server/app.py` | FastMCP instance + lifespan that starts/stops COM bridge |
| `controldesk_mcp/server/registry.py` | Single import point for all tools, resources, prompts |
| `controldesk_mcp/tools/<domain>/` | Thin adapters: `@mcp.tool` decorator + one-line body |
| `controldesk_mcp/com_bridge/__init__.py` | `dispatch()` — the only `com_bridge` symbol imported elsewhere |
| `controldesk_mcp/com_bridge/sta_thread.py` | `threading.Thread` + `asyncio.Queue`; STA blocks on queue, executes COM synchronously, returns via `Future` |
| `controldesk_mcp/com_bridge/connection.py` | `COMConnection` class — holds root COM object; reconnects on `RPC_E_DISCONNECTED` |
| `controldesk_mcp/com_bridge/errors.py` | `CdError` subclass definitions with `retryable` and `recovery_hint` |
| `controldesk_mcp/com_bridge/error_handling/hresult.py` | `pywintypes.com_error` → typed `CdError` subclass |
| `controldesk_mcp/com_bridge/error_handling/guard.py` | COM Guard: STA executor, `asyncio.timeout`, retry |
| `controldesk_mcp/com_bridge/error_handling/circuit_breaker.py` | Per-interface CLOSED/OPEN/HALF-OPEN circuit breaker |
| `controldesk_mcp/com_bridge/detector.py` | ControlDesk version/process detection on the local machine |
| `controldesk_mcp/config/settings.py` | `pydantic-settings`: `COM_PROG_ID`, `COM_TIMEOUT_MS`, `LOG_LEVEL`, `MCP_TRANSPORT` |
| `AGENTS.md` | AI agent context: STA rules, ProgID, mock setup, test markers |

---

## 9. Dependency Stack

```toml
[project]
requires-python = ">=3.11"
dependencies = [
    "mcp[cli]>=1.2",          # FastMCP server framework
    "pywin32>=306",            # COM automation (win32com)
    "pydantic>=2.7",           # Input/output models
    "pydantic-settings>=2.3",  # Config from env vars
]

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.23",
    "pytest-mock>=3.14",
]
product = ["openai"]           # GitHub Models LLM runner
agentic = ["github-copilot-sdk"]
```

---

*See also: [error-handling.md](error-handling.md) · [performance.md](performance.md) · [tool-design.md](tool-design.md) · [testing.md](testing.md) · [mcp-inspector.md](mcp-inspector.md)*
