$ErrorActionPreference = "Stop"

$startupDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
$startupShortcutPath = Join-Path $startupDir "DHRUV AI.cmd"

if (Test-Path $startupShortcutPath) {
    Remove-Item -LiteralPath $startupShortcutPath -Force
    Write-Host "Removed $startupShortcutPath"
} else {
    Write-Host "No startup launcher found."
}
