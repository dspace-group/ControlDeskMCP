param()

$ErrorActionPreference = 'Stop'

$pattern = 'from\s+sources\.com_bridge\.(connection|domains|error_mapper|sta_thread)'
$layerDirs = @('sources/server', 'sources/tools')
$files = Get-ChildItem -Path $layerDirs -Recurse -Filter '*.py' -ErrorAction SilentlyContinue
$violations = $files | Select-String -Pattern $pattern

if ($violations) {
    Write-Host 'LAYER VIOLATION - server/tools code imports COM bridge internals directly.' -ForegroundColor Red
    $violations | ForEach-Object {
        Write-Host "  $($_.Filename):$($_.LineNumber)  $($_.Line.Trim())" -ForegroundColor Red
    }
    Write-Host 'Rule: only sources.com_bridge.dispatch may be imported outside com_bridge/.' -ForegroundColor Red
    exit 1
}

Write-Host 'Layer check passed.' -ForegroundColor Green
