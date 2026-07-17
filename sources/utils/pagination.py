"""Pagination utility for MCP list service operations."""

from __future__ import annotations

from typing import Any


def paginate(
    result: dict[str, Any] | list[Any],
    offset: int,
    limit: int,
    list_key: str = "items",
) -> dict[str, Any]:
    """Apply offset/limit pagination to a dict or flat list result.

    Args:
        result: Either a flat list or a dict containing a list at ``list_key``.
        offset: Zero-based start index.
        limit: Maximum number of items to return.
        list_key: Key in the dict whose value is the list to paginate.
                  Ignored when *result* is already a flat list.

    Returns:
        A dict with pagination metadata injected:
        ``total_count``, ``has_more``, ``next_offset``.
        When *result* is a flat list the items are returned under ``list_key``.
    """
    if isinstance(result, list):
        total = len(result)
        page = result[offset : offset + limit]
        has_more = offset + limit < total
        next_offset = offset + limit if has_more else None
        out: dict[str, Any] = {
            list_key: page,
            "total_count": total,
            "has_more": has_more,
            "next_offset": next_offset,
        }
        if has_more:
            end = offset + len(page) - 1
            out["pagination_hint"] = (
                f"{len(page)} of {total} records returned (offset {offset}–{end}). "
                f"Call again with offset={next_offset} to retrieve the next page."
            )
        return out
    result = dict(result)
    items = result.get(list_key, [])
    total = len(items)
    page = items[offset : offset + limit]
    has_more = offset + limit < total
    next_offset = offset + limit if has_more else None
    result[list_key] = page
    result["total_count"] = total
    result["has_more"] = has_more
    result["next_offset"] = next_offset
    if has_more:
        end = offset + len(page) - 1
        result["pagination_hint"] = (
            f"{len(page)} of {total} records returned (offset {offset}–{end}). "
            f"Call again with offset={next_offset} to retrieve the next page."
        )
    return result
