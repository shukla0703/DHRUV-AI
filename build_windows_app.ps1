$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$tempRoot = Join-Path $env:TEMP "dhruv_ai_build_$stamp"
$workPath = Join-Path $tempRoot "work"
$distPath = Join-Path $tempRoot "dist"
$workspaceOutput = Join-Path $projectRoot "dist_builds\$stamp"
$workspaceLatest = Join-Path $projectRoot "dist_builds\latest"

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    throw "Project virtual environment not found at .venv\Scripts\python.exe"
}

& .\.venv\Scripts\python.exe -m pip install pyinstaller
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install or verify PyInstaller."
}

& .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --workpath $workPath --distpath $distPath DHRUV.spec
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed."
}

New-Item -ItemType Directory -Force $workspaceOutput | Out-Null
New-Item -ItemType Directory -Force $workspaceLatest | Out-Null
Copy-Item -Path (Join-Path $distPath "DHRUV AI") -Destination $workspaceOutput -Recurse -Force
Copy-Item -Path (Join-Path $distPath "DHRUV AI") -Destination $workspaceLatest -Recurse -Force

Write-Host ""
Write-Host "DHRUV AI desktop application built successfully." -ForegroundColor Green
Write-Host "Temporary build folder: $distPath\DHRUV AI" -ForegroundColor Cyan
Write-Host "Workspace copy: $workspaceOutput\DHRUV AI" -ForegroundColor Cyan
