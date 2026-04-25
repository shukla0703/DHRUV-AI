$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$startupDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
$launcherPath = Join-Path $projectRoot "launch_dhruv_startup.cmd"
$startupShortcutPath = Join-Path $startupDir "DHRUV AI.cmd"

if (-not (Test-Path $startupDir)) {
    New-Item -ItemType Directory -Path $startupDir | Out-Null
}

$launcherContent = @"
@echo off
cd /d "$projectRoot"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py --startup
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        py -3.11 main.py --startup
    ) else (
        python main.py --startup
    )
)
"@

Set-Content -Path $launcherPath -Value $launcherContent -Encoding ASCII
Copy-Item -Path $launcherPath -Destination $startupShortcutPath -Force

Write-Host "DHRUV AI startup launcher installed at $startupShortcutPath"
