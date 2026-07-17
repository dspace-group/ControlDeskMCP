@echo off
setlocal

REM Prefer uv-managed execution when available.
where uv >nul 2>nul
if %ERRORLEVEL%==0 (
	uv --directory "%~dp0." run python -m controldesk_mcp.server %*
	exit /b %ERRORLEVEL%
)

REM Fallback for environments where uv is not on PATH (for example VS Code extension host).
where py >nul 2>nul
if %ERRORLEVEL%==0 (
	py -m controldesk_mcp.server %*
	exit /b %ERRORLEVEL%
)

where python >nul 2>nul
if %ERRORLEVEL%==0 (
	python -m controldesk_mcp.server %*
	exit /b %ERRORLEVEL%
)

echo ERROR: Neither uv, py, nor python is available on PATH. 1>&2
exit /b 1