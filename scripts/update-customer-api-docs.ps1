<#
.SYNOPSIS
    Regenerate MCP customer API artifacts under docs/customer-api.

.DESCRIPTION
    Exports tools, resources, resource templates, and prompts from the
    ControlDesk MCP server using the MCP Inspector CLI over stdio transport.
    The script prefers a cached local inspector install to avoid network
    downloads, then falls back to npx when needed.

    After exporting the JSON files, it validates them and regenerates the
    README.md summary in the output folder.

.EXAMPLE
    ./scripts/update-customer-api-docs.ps1

.EXAMPLE
    ./scripts/update-customer-api-docs.ps1 -OutputDir .\docs\customer-api
#>
param(
    [string]$OutputDir = ".\docs\customer-api",
    [string]$PythonCommand = "python"
)

$ErrorActionPreference = 'Stop'

# Force UTF-8 for external process stdout/stderr decoding to avoid mojibake in exported JSON.
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = $utf8NoBom
[Console]::InputEncoding = $utf8NoBom
[Console]::OutputEncoding = $utf8NoBom

Set-Location (Join-Path $PSScriptRoot '..')

function Get-CachedInspectorPath {
    $cacheRoot = Join-Path $env:LOCALAPPDATA 'npm-cache\_npx'
    if (-not (Test-Path $cacheRoot)) {
        return $null
    }

    $candidate = Get-ChildItem -Path $cacheRoot -Recurse -Filter 'mcp-inspector.ps1' -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -like '*node_modules\.bin\mcp-inspector.ps1' } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

    if ($candidate) {
        return $candidate.FullName
    }

    return $null
}

function Get-InspectorInvocation {
    $cachedInspector = Get-CachedInspectorPath
    if ($cachedInspector) {
        return @{
            Kind       = 'cached'
            FilePath   = $cachedInspector
            PrefixArgs = @()
        }
    }

    $npxCommand = Get-Command npx.ps1 -ErrorAction SilentlyContinue
    if (-not $npxCommand) {
        $npxCommand = Get-Command npx -ErrorAction SilentlyContinue
    }

    if (-not $npxCommand) {
        throw 'npx is not available and no cached MCP Inspector install was found.'
    }

    return @{
        Kind       = 'npx'
        FilePath   = $npxCommand.Source
        PrefixArgs = @('-y', '@modelcontextprotocol/inspector')
    }
}

function Invoke-InspectorExport {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$Inspector,

        [Parameter(Mandatory = $true)]
        [string]$Method,

        [Parameter(Mandatory = $true)]
        [string]$DestinationPath,

        [Parameter(Mandatory = $true)]
        [string]$PythonCommand
    )

    $arguments = @()
    $arguments += $Inspector.PrefixArgs
    $arguments += @('--cli', "$PythonCommand -m sources", '--transport', 'stdio', '--method', $Method)

    Write-Host "Exporting $Method ..." -ForegroundColor Cyan
    $output = & $Inspector.FilePath @arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Inspector export failed for '$Method'. Output:`n$output"
    }

    $outputText = ($output | Out-String).Trim()
    if ([string]::IsNullOrWhiteSpace($outputText)) {
        throw "Inspector export for '$Method' returned empty output."
    }

    try {
        $null = $outputText | ConvertFrom-Json -ErrorAction Stop
    }
    catch {
        throw "Inspector export for '$Method' did not produce valid JSON."
    }

    Set-Content -Path $DestinationPath -Value $outputText -Encoding utf8
}

function Get-JsonArrayCount {
    param(
        [Parameter(Mandatory = $true)]
        [pscustomobject]$Document,

        [Parameter(Mandatory = $true)]
        [string]$PropertyName
    )

    $property = $Document.PSObject.Properties[$PropertyName]
    if (-not $property) {
        return 0
    }

    $value = $property.Value
    if ($null -eq $value) {
        return 0
    }

    if ($value -is [System.Array]) {
        return $value.Count
    }

    return @($value).Count
}

function Update-CustomerApiReadme {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ReadmePath,

        [Parameter(Mandatory = $true)]
        [hashtable]$Summaries,

        [Parameter(Mandatory = $true)]
        [hashtable]$Inspector,

        [Parameter(Mandatory = $true)]
        [string]$PythonCommand
    )

    $generatedAt = (Get-Date).ToString('yyyy-MM-dd HH:mm:ssK')
    $inspectorSource = if ($Inspector.Kind -eq 'cached') { $Inspector.FilePath } else { 'npx @modelcontextprotocol/inspector' }

    $codeFence = '```'
    $content = @"
# Customer API Artifacts

This folder contains generated MCP API artifacts for the ControlDesk MCP server.

## Update

Run the updater from the repository root:

$codeFence powershell
./scripts/update-customer-api-docs.ps1
$codeFence

The script exports the MCP schema surfaces over stdio transport using:

$codeFence powershell
$PythonCommand -m sources
$codeFence

## Generated Files

| File | Top-level field | Item count |
| --- | --- | ---: |
| tools_list.json | tools | $($Summaries['tools_list.json'].Count) |
| resources_list.json | resources | $($Summaries['resources_list.json'].Count) |
| resources_templates_list.json | resourceTemplates | $($Summaries['resources_templates_list.json'].Count) |
| prompts_list.json | prompts | $($Summaries['prompts_list.json'].Count) |

## Notes

- Generated at: $generatedAt
- Inspector source: $inspectorSource
- Transport: stdio
- Server command: $PythonCommand -m sources
"@

    Set-Content -Path $ReadmePath -Value $content.TrimStart() -Encoding utf8
}

$resolvedOutputDir = [System.IO.Path]::GetFullPath($OutputDir)
New-Item -ItemType Directory -Force -Path $resolvedOutputDir | Out-Null

$inspector = Get-InspectorInvocation
Write-Host "Inspector : $($inspector.Kind)" -ForegroundColor Green
Write-Host "Output    : $resolvedOutputDir" -ForegroundColor Green

$exports = @(
    @{ Method = 'tools/list'; FileName = 'tools_list.json'; Property = 'tools' },
    @{ Method = 'resources/list'; FileName = 'resources_list.json'; Property = 'resources' },
    @{ Method = 'resources/templates/list'; FileName = 'resources_templates_list.json'; Property = 'resourceTemplates' },
    @{ Method = 'prompts/list'; FileName = 'prompts_list.json'; Property = 'prompts' }
)

$summaries = @{}

foreach ($export in $exports) {
    $destinationPath = Join-Path $resolvedOutputDir $export.FileName
    Invoke-InspectorExport -Inspector $inspector -Method $export.Method -DestinationPath $destinationPath -PythonCommand $PythonCommand

    $document = Get-Content -Path $destinationPath -Raw | ConvertFrom-Json -ErrorAction Stop
    $count = Get-JsonArrayCount -Document $document -PropertyName $export.Property
    $summaries[$export.FileName] = @{
        Property = $export.Property
        Count    = $count
    }
}

$readmePath = Join-Path $resolvedOutputDir 'README.md'
Update-CustomerApiReadme -ReadmePath $readmePath -Summaries $summaries -Inspector $inspector -PythonCommand $PythonCommand

Write-Host ''
Write-Host 'Customer API artifacts updated successfully.' -ForegroundColor Green
foreach ($fileName in @('tools_list.json', 'resources_list.json', 'resources_templates_list.json', 'prompts_list.json', 'README.md')) {
    Write-Host "  $fileName" -ForegroundColor White
}