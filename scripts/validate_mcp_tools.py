"""Validate that all @mcp.tool() decorators have required arguments.

Rule: Every @mcp.tool() decorator MUST include:
  - name= (string)
  - description= (string — no newline characters; multi-line via + or implicit concat is allowed)
  - annotations= (dict literal OR AnnotationInfo(...) call)

Exit code: 0 if all valid, 1 if violations found.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path


def _extract_string_value(node: ast.expr) -> str | None:
    """Recursively extract a string from a constant or + concatenation expression.

    Handles:
      - ``ast.Constant`` — a plain string literal
      - ``ast.BinOp(op=Add)`` — explicit ``"a" + "b"`` concatenation
      - ``ast.JoinedStr`` is intentionally rejected (f-strings are not allowed)
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _extract_string_value(node.left)
        right = _extract_string_value(node.right)
        if left is not None and right is not None:
            return left + right
    return None


class ToolDecoratorValidator(ast.NodeVisitor):
    """Find and validate @mcp.tool() decorators."""

    def __init__(self, filename: str):
        self.filename = filename
        self.violations: list[str] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check function decorators for @mcp.tool()."""
        for decorator in node.decorator_list:
            if self._is_mcp_tool_call(decorator):
                self._validate_tool_decorator(decorator, node.name)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Check async function decorators for @mcp.tool()."""
        for decorator in node.decorator_list:
            if self._is_mcp_tool_call(decorator):
                self._validate_tool_decorator(decorator, node.name)
        self.generic_visit(node)

    @staticmethod
    def _is_mcp_tool_call(node: ast.expr) -> bool:
        """Check if decorator is @mcp.tool() call."""
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                return (
                    func.attr == "tool"
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "mcp"
                )
        return False

    def _validate_tool_decorator(self, decorator: ast.Call, func_name: str) -> None:
        """Validate a single @mcp.tool() decorator has all required arguments."""
        has_name = False
        has_description = False
        has_annotations = False
        description_value: str | None = None

        for keyword in decorator.keywords:
            if keyword.arg == "name":
                has_name = (
                    isinstance(keyword.value, ast.Constant)
                    and isinstance(keyword.value.value, str)
                )
            elif keyword.arg == "description":
                description_value = _extract_string_value(keyword.value)
                has_description = description_value is not None
            elif keyword.arg == "annotations":
                has_annotations = isinstance(keyword.value, (ast.Dict, ast.Call))

        line_no = decorator.lineno
        if not has_name:
            self.violations.append(f"{self.filename}:{line_no}  {func_name}() missing name= argument")
        if not has_description:
            self.violations.append(
                f"{self.filename}:{line_no}  {func_name}() missing description= argument"
            )
        elif "\n" in description_value:  # type: ignore[operator]
            self.violations.append(
                f"{self.filename}:{line_no}  {func_name}() description contains newline (must be single-line)"
            )
        if not has_annotations:
            self.violations.append(
                f"{self.filename}:{line_no}  {func_name}() missing annotations= argument"
            )


def validate_file(filepath: Path) -> list[str]:
    """Parse a Python file and return tool decorator violations."""
    try:
        with open(filepath, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(filepath))
    except SyntaxError as e:
        return [f"{filepath}: Syntax error: {e}"]

    validator = ToolDecoratorValidator(str(filepath))
    validator.visit(tree)
    return validator.violations


def main() -> int:
    """Scan all tool files and validate decorators."""
    tool_dir = Path("sources/tools")
    if not tool_dir.exists():
        print("sources/tools/ not found", file=sys.stderr)
        return 1

    all_violations: list[str] = []
    for py_file in tool_dir.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue
        violations = validate_file(py_file)
        all_violations.extend(violations)

    if all_violations:
        print("MCP TOOL DECORATOR VIOLATIONS:", file=sys.stderr)
        for violation in all_violations:
            print(f"  {violation}", file=sys.stderr)
        print("", file=sys.stderr)
        print("Every @mcp.tool() decorator MUST have:", file=sys.stderr)
        print("  - name='tool_name'", file=sys.stderr)
        print("  - description='Use this to ...' (single line, no \\n)", file=sys.stderr)
        print("  - annotations={...} (all 4 hints required)", file=sys.stderr)
        return 1

    print("MCP tool decorators OK (all have name, description, annotations)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
