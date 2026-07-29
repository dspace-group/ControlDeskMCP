# Variable Resolution Behavior and Operator Guide

## Overview

ControlDesk MCP resolves natural variable phrases into concrete connection paths before read/write operations run. Operators do not need to provide full `XCP(...)://...` paths up front for typical workflows.

The resolver is shared by variable and measurement signal-add flows and follows a deterministic fallback order.

## Ordered Resolution Flow

The resolver executes these steps in order and stops at the first high-confidence match:

1. Instrument hint extraction from semantic instrument names.
2. Bounded `controldesk_variable_find(search_mode='name')` attempts using deterministic name variants.
3. Authoritative `controldesk_variable_list(action='list_all')` fallback with pagination.
4. Candidate ranking over `name` and `connection_path` tokens.
5. Explicit operator pick for ambiguous outcomes.

### Deterministic Name Variants

The bounded name-attempt order is:

1. PascalCase
2. camelCase
3. snake_case
4. UPPER_SNAKE_CASE
5. Title Case
6. ALL CAPS spaced
7. lowercase spaced
8. kebab-case
9. original raw input

## Path and Serialization Rules

- Returned connection paths are used verbatim. Do not reconstruct suffixes, ranges, or units.
- Serialized `<COMObject <unknown>>` placeholders are treated as non-authoritative and ignored for path selection.
- Instrument names are used as hints only, not as guaranteed path authorities.

## Write Safety Enforcement

Before `controldesk_variable_write` executes, the server enforces:

- `is_writable == true`
- init-only lock check while online calibration is active

If a safety check fails, the write is blocked with a structured error envelope and recovery hint.

## Ambiguity Handling

When multiple close candidates exist, the resolver returns an `ambiguous` status and top ranked candidates. Operators should select one of the presented candidates.

Recommended operator action:

1. Pick one of the top candidates returned in `resolution_details.candidates`.
2. Retry using the selected connection path or exact internal name.
3. If all candidates look stale, reload/activate variable descriptions and retry.

## Grouped Instruments Troubleshooting

Symptoms:

- Instrument phrase resolves weakly.
- Top-level list looks incomplete.

Actions:

1. Keep resolver flow enabled and allow list-all fallback to complete.
2. Use `controldesk_variable_list(action='list_all')` and `list_group_variables` to inspect full availability.
3. Confirm active variable description files are loaded for the target platform.

## Debug and Cache Controls

Settings:

- `VARIABLE_RESOLUTION_CACHE_TTL_SECONDS` controls in-memory resolver cache TTL.
- `VARIABLE_RESOLUTION_DEBUG_TELEMETRY` includes verbose resolver telemetry in result payloads.

Telemetry fields include:

- `strategy`
- `attempts_count`
- `fallback_activated`
- `candidate_count`
- `confidence`
- `hint_used`
- `cache_hit`

## Prompt Change Notes

Variable-operation prompts now enforce these assistant behaviors:

- Do not ask for a full path before resolver attempts and list-all fallback are executed.
- Use ordered resolver flow and expose top candidates on ambiguity.
- Preserve returned connection paths exactly.
- Enforce write safety checks before write attempts.

## Operator Examples

### Example A: Natural phrase resolves directly

Input phrase:

- `air mass flow`

Expected behavior:

1. Resolver tries bounded name variants.
2. Direct name match is found.
3. Read/write continues using resolved path.

### Example B: Ambiguous phrase requires pick

Input phrase:

- `control out`

Expected behavior:

1. Resolver falls back to list-all ranking.
2. Multiple candidates are returned.
3. Operator picks one candidate.
4. Tool call continues with selected connection path.

### Example C: Grouped instrument hint assists ranking

Input phrase:

- `dSPACE Data Measurements air_mass`

Expected behavior:

1. Instrument tail hint (`air_mass`) is extracted.
2. Hint is prioritized in direct attempts and ranking.
3. Resolved connection path is used verbatim.
