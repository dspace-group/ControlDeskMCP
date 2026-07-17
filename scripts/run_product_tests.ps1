<#
.SYNOPSIS
    Run ControlDesk MCP product tests (manual and/or agentic).

.DESCRIPTION
    manual  — Direct tool call tests. No LLM required. Needs a live ControlDesk instance.
    agentic — LLM-driven tests. Needs a live ControlDesk + a configured LLM API key.
    copilot — GitHub Copilot SDK tests. No API key required; uses VS Code Copilot CLI.

.PARAMETER Suite
    Which test suite to run: 'manual', 'agentic', or 'all'. Default: 'manual'.

.PARAMETER Verbose
    Pass -Verbose to get full pytest -v output.

.PARAMETER FailFast
    Stop on the first test failure (-x).

.PARAMETER LlmBaseUrl
    Override the LLM API base URL (sets GITHUB_MODELS_BASE_URL).
    Examples:
        Groq:        https://api.groq.com/openai/v1
        Azure OpenAI: https://<resource>.openai.azure.com/openai/deployments/<deployment>
        Ollama:      http://localhost:11434/v1

.PARAMETER LlmModel
    Override the LLM model name (sets GITHUB_MODELS_MODEL).

.PARAMETER ApiKey
    API key / PAT for the LLM endpoint (sets GITHUB_TOKEN).
    If not provided, falls back to the existing GITHUB_TOKEN env var.

.EXAMPLE
    # Run manual tests only (default)
    .\scripts\run_product_tests.ps1

.EXAMPLE
    # Run manual tests with verbose output, stop on first failure
    .\scripts\run_product_tests.ps1 -Suite manual -Verbose -FailFast

.EXAMPLE
    # Run agentic tests with Groq
    .\scripts\run_product_tests.ps1 -Suite agentic `
        -LlmBaseUrl https://api.groq.com/openai/v1 `
        -LlmModel llama-3.3-70b-versatile `
        -ApiKey gsk_...

.EXAMPLE
    # Run all tests
    .\scripts\run_product_tests.ps1 -Suite all
#>

[CmdletBinding()]
param(
    [ValidateSet('manual', 'agentic', 'copilot', 'all')]
    [string]$Suite = 'manual',

    [switch]$FailFast,

    [string]$LlmBaseUrl,
    [string]$LlmModel,
    [string]$ApiKey
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ── Resolve repo root ──────────────────────────────────────────────────────────
$RepoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $RepoRoot

# ── Load .env if present ───────────────────────────────────────────────────────
$envFile = Join-Path $RepoRoot '.env'
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^([^#][^=]+)=(.+)$') {
            $key = $Matches[1].Trim()
            $value = $Matches[2].Trim()
            if (-not [System.Environment]::GetEnvironmentVariable($key, 'Process')) {
                [System.Environment]::SetEnvironmentVariable($key, $value, 'Process')
            }
        }
    }
    Write-Host "Loaded .env" -ForegroundColor DarkGray
}

# ── Apply CLI overrides ────────────────────────────────────────────────────────
if ($LlmBaseUrl) { $env:GITHUB_MODELS_BASE_URL = $LlmBaseUrl }
if ($LlmModel) { $env:GITHUB_MODELS_MODEL = $LlmModel }
if ($ApiKey) { $env:GITHUB_TOKEN = $ApiKey }

# ── Build pytest arguments ─────────────────────────────────────────────────────
$pytestArgs = @()

switch ($Suite) {
    'manual' { $pytestArgs += 'tests/product/manual/'; $pytestArgs += '-m'; $pytestArgs += 'product' }
    'agentic' { $pytestArgs += 'tests/product/agentic/'; $pytestArgs += '-m'; $pytestArgs += 'llm_product' }
    'copilot' {
        $pytestArgs += 'tests/product/agentic/test_copilot_application_lifecycle.py'
        $pytestArgs += '-m'; $pytestArgs += 'llm_product'
    }
    'all' { $pytestArgs += 'tests/product/'; $pytestArgs += '-m'; $pytestArgs += 'product or llm_product' }
}

$pytestArgs += '--no-header'
$pytestArgs += '-p'; $pytestArgs += 'no:warnings'

if ($VerbosePreference -ne 'SilentlyContinue') {
    $pytestArgs += '-v'
}
else {
    $pytestArgs += '-v'   # always verbose for product tests — results matter
}

if ($FailFast) {
    $pytestArgs += '-x'
}

# ── Print summary ──────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "ControlDesk MCP — Product Tests" -ForegroundColor Cyan
Write-Host "  Suite      : $Suite" -ForegroundColor Cyan
Write-Host "  LLM URL    : $($env:GITHUB_MODELS_BASE_URL)" -ForegroundColor DarkGray
Write-Host "  LLM Model  : $($env:GITHUB_MODELS_MODEL)" -ForegroundColor DarkGray
Write-Host "  Token set  : $( if ($env:GITHUB_TOKEN) { 'yes' } else { 'NO (agentic suite will skip)' } )" -ForegroundColor DarkGray
Write-Host "  Copilot CLI: $($env:COPILOT_CLI_PATH)" -ForegroundColor DarkGray
Write-Host "  Copilot Mdl: $($env:COPILOT_MODEL)" -ForegroundColor DarkGray
Write-Host ""

# ── Run ────────────────────────────────────────────────────────────────────────
python -m pytest @pytestArgs
$exitCode = $LASTEXITCODE

Pop-Location
exit $exitCode
