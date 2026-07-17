#!/usr/bin/env bash
set -euo pipefail

# Python
if [ -d servers/python ]; then
  python -m pip install -e servers/python[dev] >/dev/null
  ruff check servers/python
  black --check servers/python
  pytest -q servers/python
fi

# .NET
if [ -d servers/csharp ]; then
  dotnet restore servers/csharp
  dotnet build servers/csharp -warnaserror
  dotnet test servers/csharp --no-build --verbosity normal
fi

echo "Quality gate passed."
