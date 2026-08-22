<#
.SYNOPSIS
    Startet NEXRON-TokenScope lokal.

.DESCRIPTION
    Richtet beim ersten Lauf alles selbst ein (venv, npm-Pakete, Frontend-Build)
    und startet danach das Backend, das das gebaute Frontend gleich mit
    ausliefert. Ein Prozess, ein Port.

.PARAMETER Dev
    Startet zusätzlich den Vite-Dev-Server mit Hot-Reload auf Port 5173.

.PARAMETER NoBrowser
    Öffnet den Browser nicht automatisch.

.PARAMETER Desktop
    Zeigt die Oberfläche statt im Browser in der Tauri-Hülle an – im Vollbild
    und auf Wunsch auf einem bestimmten Bildschirm.

.PARAMETER Monitor
    Bildschirm für -Desktop: "smallest" oder "largest" nach Flaeche, die
    1-basierte Nummer, oder ein Stueck des Geraetenamens wie DISPLAY4. Die
    Nummer verschiebt sich beim An- und Abstecken, die anderen beiden nicht.
    Alle drei Angaben zeigt -ListMonitors.

.PARAMETER ListMonitors
    Zeigt nur die erkannten Bildschirme mit ihrer Nummer an.

.EXAMPLE
    .\start.ps1
    .\start.ps1 -Dev
    .\start.ps1 -Desktop -Monitor smallest
    .\start.ps1 -ListMonitors
#>
[CmdletBinding()]
param(
    [switch]$Dev,
    [switch]$NoBrowser,
    [switch]$Desktop,
    [string]$Monitor = '',
    [switch]$ListMonitors,
    [int]$Port = 8787
)

$ErrorActionPreference = 'Stop'

$root = $PSScriptRoot
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'
$python = Join-Path $backend '.venv\Scripts\python.exe'
$requirements = Join-Path $backend 'requirements.txt'

$desktopSrc = Join-Path $root 'desktop\src-tauri'
$desktopExe = Join-Path $desktopSrc 'target\release\nexron-tokenscope-desktop.exe'

function Write-Step($text) {
    Write-Host "==> $text" -ForegroundColor Cyan
}

# Die Huelle wird nur bei Bedarf gebaut - der erste cargo-Lauf dauert Minuten.
function Confirm-DesktopApp {
    if (Test-Path $desktopExe) { return }

    if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
        throw 'Fuer die Desktop-Huelle wird Rust benoetigt: https://rustup.rs'
    }

    Write-Step 'Baue die Desktop-Huelle (einmalig, dauert einige Minuten)'
    Push-Location $desktopSrc
    try {
        cargo build --release
        if ($LASTEXITCODE -ne 0) { throw 'Die Desktop-Huelle konnte nicht gebaut werden.' }
    } finally { Pop-Location }
}

function Get-DesktopArgs([int]$TargetPort) {
    $list = @('--port', "$TargetPort")
    if ($Monitor) { $list += @('--monitor', $Monitor) }
    # Das Backend startet dieses Skript selbst; die Huelle wartet nur darauf.
    $list + '--no-backend'
}

# --- Nur die Bildschirme auflisten ------------------------------------------
if ($ListMonitors) {
    Confirm-DesktopApp
    Start-Process -FilePath $desktopExe -ArgumentList '--list-monitors' -Wait
    exit 0
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
# Mit -Dev zeigen Browser und Huelle den Vite-Server; das dist/ wird dann gar
# nicht ausgeliefert, ein Build waere nur Wartezeit vor dem Hot-Reload.
$needsBuild = $false
if (-not $Dev) {
    $needsBuild = -not (Test-Path $indexHtml)
    if (-not $needsBuild) {
        $built = (Get-Item $indexHtml).LastWriteTime
        $newest = Get-ChildItem (Join-Path $frontend 'src') -Recurse -File |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1
        if ($newest -and $newest.LastWriteTime -gt $built) { $needsBuild = $true }
    }
}

if ($needsBuild) {
    Write-Step 'Baue das Frontend'
    Push-Location $frontend
    try { npm.cmd run build } finally { Pop-Location }
}

if ($Desktop) { Confirm-DesktopApp }

# --- Start ------------------------------------------------------------------
# Ein bereits laufender Dienst wuerde sonst nur eine kryptische Socket-Meldung
# aus uvicorn produzieren.
$busy = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
$backendRuns = [bool]$busy

# Mit -Dev ist ein laufendes Backend kein Abbruchgrund: Gebraucht wird hier der
# Vite-Server, das Backend liefert nur noch /api. Ohne diesen Zweig endete
# `-Dev` bei laufendem Dienst vor dem Start von Vite - und der Browser zeigte
# den statischen Build auf Port $Port, also ohne Hot-Reload.
if ($busy -and $Dev) {
    Write-Step "Backend laeuft bereits auf Port $Port - starte nur den Dev-Server"
}
if ($busy -and -not $Dev -and $Desktop) {
    # Kein Grund abzubrechen: Das Fenster haengt sich einfach an den laufenden Dienst.
    Write-Step "Backend laeuft bereits auf Port $Port - oeffne nur das Fenster"
    Start-Process -FilePath $desktopExe -ArgumentList (Get-DesktopArgs $Port)
    exit 0
}
if ($busy -and -not $Dev) {
    Write-Host "Port $Port ist bereits belegt (PID $($busy[0].OwningProcess))." -ForegroundColor Yellow
    Write-Host "Laeuft der Dienst schon? -> http://127.0.0.1:$Port/" -ForegroundColor Yellow
    Write-Host "Sonst beenden mit: Stop-Process -Id $($busy[0].OwningProcess)" -ForegroundColor Yellow
    exit 1
}

$url = if ($Dev) { 'http://127.0.0.1:5173/' } else { "http://127.0.0.1:$Port/" }
$vite = $null

if ($Dev) {
    # Ein verwaister Vite aus einem frueheren Lauf wuerde den Port halten; der
    # neue Server wiche stillschweigend auf 5174 aus, waehrend Browser und
    # Huelle weiter auf 5173 schauen. Darum vorher pruefen.
    $viteBusy = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
    if ($viteBusy) {
        Write-Host "Port 5173 ist belegt (PID $($viteBusy[0].OwningProcess)) - vermutlich ein alter Dev-Server." -ForegroundColor Yellow
        Write-Host "Beenden mit: Stop-Process -Id $($viteBusy[0].OwningProcess) -Force" -ForegroundColor Yellow
        exit 1
    }

    Write-Step 'Starte den Vite-Dev-Server auf Port 5173'
    # --strictPort: lieber ein sichtbarer Fehler als ein Server auf einem Port,
    # den niemand aufruft.
    $vite = Start-Process -FilePath 'npm.cmd' -ArgumentList 'run', 'dev', '--', '--strictPort' `
        -WorkingDirectory $frontend -PassThru
}

$desktopApp = $null
if ($Desktop) {
    Write-Step 'Starte das Desktop-Fenster'
    # Mit -Dev zeigt das Fenster den Vite-Server, damit auch dort neu geladen wird.
    # Bis der Port antwortet, zeigt die Huelle einen Splash.
    $desktopPort = if ($Dev) { 5173 } else { $Port }
    $desktopApp = Start-Process -FilePath $desktopExe -ArgumentList (Get-DesktopArgs $desktopPort) -PassThru
}

# Im Dev-Betrieb muss Vite antworten, nicht das Backend - sonst oeffnet sich der
# Browser bei laufendem Backend sofort und laeuft in einen leeren Port.
$probe = if ($Dev) { $url } else { "http://127.0.0.1:$Port/api/health" }

if (-not $NoBrowser -and -not $Desktop) {
    # Erst oeffnen, wenn die Adresse antwortet - sonst zeigt der Browser einen Fehler.
    Start-Job -ScriptBlock {
        param($target, $probe)
        for ($i = 0; $i -lt 40; $i++) {
            try {
                Invoke-WebRequest -Uri $probe -UseBasicParsing -TimeoutSec 2 | Out-Null
                Start-Process $target
                return
            } catch { Start-Sleep -Milliseconds 500 }
        }
    } -ArgumentList $url, $probe | Out-Null
}

if ($Dev) { Write-Step "Oberflaeche mit Hot-Reload auf $url" }
if ($backendRuns) {
    Write-Step "Backend laeuft bereits auf http://127.0.0.1:$Port - Beenden mit Strg+C"
} else {
    Write-Step "Backend laeuft auf http://127.0.0.1:$Port - Beenden mit Strg+C"
}
Write-Host ""

$env:PYTHONPATH = $backend
Push-Location $backend
try {
    if ($backendRuns) {
        # Das Backend haelt ein anderes Fenster offen; hier bleibt nur der
        # Dev-Server im Vordergrund, damit Strg+C weiterhin alles beendet.
        if ($vite) { Wait-Process -Id $vite.Id }
    } else {
        & $python -m uvicorn app.main:app --host 127.0.0.1 --port $Port
    }
} finally {
    Pop-Location
    # Weder Dev-Server noch Fenster verwaist zuruecklassen.
    if ($vite -and -not $vite.HasExited) {
        # npm.cmd startet node als Kindprozess; ohne /T bliebe der Dev-Server
        # auf 5173 als Waise zurueck und blockierte den naechsten Start.
        taskkill /PID $vite.Id /T /F *> $null
    }
    if ($desktopApp -and -not $desktopApp.HasExited) {
        Stop-Process -Id $desktopApp.Id -Force -ErrorAction SilentlyContinue
    }
    Get-Job | Remove-Job -Force -ErrorAction SilentlyContinue
}
