<#
.SYNOPSIS
    Startet den AI Usage Monitor lokal.

.DESCRIPTION
    Richtet beim ersten Lauf alles selbst ein (venv, npm-Pakete, Frontend-Build)
    und startet danach das Backend, das das gebaute Frontend gleich mit
    ausliefert. Ein Prozess, ein Port.

.PARAMETER Dev
    Startet zusätzlich den Vite-Dev-Server mit Hot-Reload auf Port 5173.

.PARAMETER NoBrowser
    Öffnet den Browser nicht automatisch.

.EXAMPLE
    .\start.ps1
    .\start.ps1 -Dev
#>
[CmdletBinding()]
param(
    [switch]$Dev,
    [switch]$NoBrowser,
    [int]$Port = 8787
)

$ErrorActionPreference = 'Stop'

$root = $PSScriptRoot
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'
$python = Join-Path $backend '.venv\Scripts\python.exe'
$requirements = Join-Path $backend 'requirements.txt'

function Write-Step($text) {
    Write-Host "==> $text" -ForegroundColor Cyan
}

# --- Backend-Umgebung -------------------------------------------------------
if (-not (Test-Path $python)) {
    Write-Step 'Lege die Python-Umgebung an (einmalig)'
    py -m venv (Join-Path $backend '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Python-Umgebung konnte nicht angelegt werden.' }

    & $python -m pip install --upgrade pip --quiet
    if ($LASTEXITCODE -ne 0) { throw 'pip konnte nicht aktualisiert werden.' }
}

# Eine teilweise angelegte oder kopierte venv kann zwar einen Python-Interpreter
# enthalten, aber trotzdem keine Projektpakete. Darum nicht nur die Existenz des
# Interpreters pruefen, sondern die benoetigten Laufzeitmodule wirklich importieren.
& $python -c 'import fastapi, uvicorn, httpx, pydantic, pydantic_settings' 2>$null
$backendReady = $LASTEXITCODE -eq 0

if (-not $backendReady) {
    if (-not (Test-Path $requirements)) {
        throw "Backend-Abhaengigkeiten fehlen und $requirements wurde nicht gefunden."
    }

    Write-Step 'Installiere oder repariere die Backend-Pakete'
    & $python -m pip install -r $requirements --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Backend-Pakete konnten nicht installiert werden.' }

    & $python -c 'import fastapi, uvicorn, httpx, pydantic, pydantic_settings'
    if ($LASTEXITCODE -ne 0) { throw 'Backend-Pakete sind nach der Installation nicht importierbar.' }
}

# --- Frontend ---------------------------------------------------------------
if (-not (Test-Path (Join-Path $frontend 'node_modules'))) {
    Write-Step 'Installiere die npm-Pakete (einmalig)'
    Push-Location $frontend
    try { npm.cmd install } finally { Pop-Location }
}

$indexHtml = Join-Path $frontend 'dist\index.html'

# Neu bauen, wenn der Build fehlt oder aelter als die Quellen ist.
$needsBuild = -not (Test-Path $indexHtml)
if (-not $needsBuild) {
    $built = (Get-Item $indexHtml).LastWriteTime
    $newest = Get-ChildItem (Join-Path $frontend 'src') -Recurse -File |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if ($newest -and $newest.LastWriteTime -gt $built) { $needsBuild = $true }
}

if ($needsBuild) {
    Write-Step 'Baue das Frontend'
    Push-Location $frontend
    try { npm.cmd run build } finally { Pop-Location }
}

# --- Start ------------------------------------------------------------------
# Ein bereits laufender Dienst wuerde sonst nur eine kryptische Socket-Meldung
# aus uvicorn produzieren.
$busy = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($busy) {
    Write-Host "Port $Port ist bereits belegt (PID $($busy[0].OwningProcess))." -ForegroundColor Yellow
    Write-Host "Laeuft der Dienst schon? -> http://127.0.0.1:$Port/" -ForegroundColor Yellow
    Write-Host "Sonst beenden mit: Stop-Process -Id $($busy[0].OwningProcess)" -ForegroundColor Yellow
    exit 1
}

$url = if ($Dev) { 'http://127.0.0.1:5173/' } else { "http://127.0.0.1:$Port/" }
$vite = $null

if ($Dev) {
    Write-Step 'Starte den Vite-Dev-Server auf Port 5173'
    $vite = Start-Process -FilePath 'npm.cmd' -ArgumentList 'run', 'dev' `
        -WorkingDirectory $frontend -PassThru
}

if (-not $NoBrowser) {
    # Erst oeffnen, wenn das Backend antwortet - sonst zeigt der Browser einen Fehler.
    Start-Job -ScriptBlock {
        param($target, $probe)
        for ($i = 0; $i -lt 40; $i++) {
            try {
                Invoke-WebRequest -Uri $probe -UseBasicParsing -TimeoutSec 2 | Out-Null
                Start-Process $target
                return
            } catch { Start-Sleep -Milliseconds 500 }
        }
    } -ArgumentList $url, "http://127.0.0.1:$Port/api/health" | Out-Null
}

Write-Step "Backend laeuft auf http://127.0.0.1:$Port - Beenden mit Strg+C"
Write-Host ""

$env:PYTHONPATH = $backend
Push-Location $backend
try {
    & $python -m uvicorn app.main:app --host 127.0.0.1 --port $Port
} finally {
    Pop-Location
    # Den Dev-Server nicht verwaist zuruecklassen.
    if ($vite -and -not $vite.HasExited) {
        Stop-Process -Id $vite.Id -Force -ErrorAction SilentlyContinue
    }
    Get-Job | Remove-Job -Force -ErrorAction SilentlyContinue
}
