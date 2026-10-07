param(
    [ValidateRange(1024, 65535)][int]$Port = 8000,
    [switch]$CheckOnly
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$backendRoot = Join-Path $repoRoot 'backend'
$pythonPath = Join-Path $backendRoot '.venv\Scripts\python.exe'
$baseUrl = "http://127.0.0.1:$Port"

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Backend environment missing. Run: cd backend; uv sync --locked'
}
if (-not (Test-Path -LiteralPath (Join-Path $backendRoot '.env'))) {
    throw 'Missing backend/.env. Configure it from the root .env.example first.'
}

Push-Location $backendRoot
try {
    & $pythonPath -c 'import sys, httpx; sys.exit(0 if sys.version_info[:2] == (3,12) else 1)'
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 + httpx required. Run uv sync --locked in backend.' }

    # Read-only migration preflight. Never upgrade/seed on behalf of the owner.
    $migrationCheck = @'
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from app.db.session import engine
import sys
try:
    expected = set(ScriptDirectory.from_config(Config("alembic.ini")).get_heads())
    with engine.connect() as connection:
        actual = set(MigrationContext.configure(connection).get_current_heads())
    sys.exit(0 if actual == expected else 2)
except Exception:
    sys.exit(3)
'@
    Write-Host 'Checking database/migration (no LLM call)...'
    & $pythonPath -c $migrationCheck
    if ($LASTEXITCODE -eq 2) { throw 'Migration behind code. Run in backend: uv run alembic upgrade head' }
    if ($LASTEXITCODE -ne 0) { throw 'Database unavailable. Check Supabase connectivity and backend/.env.' }
    if ($CheckOnly) { Write-Host 'Python, dependencies, database and migrations ready.'; exit 0 }

    $health = $null
    try { $health = Invoke-RestMethod -Uri "$baseUrl/api/health" -TimeoutSec 5 } catch { }
    if ($null -eq $health) {
        $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        if ($listener) { throw "Port $Port is occupied but BE is not ready. Wait, or use -Port 8001. No process was stopped." }
        $runtimeRoot = Join-Path $backendRoot 'storage\terminal'
        New-Item -ItemType Directory -Path $runtimeRoot -Force | Out-Null
        $stdoutPath = Join-Path $runtimeRoot "server-$Port.out.log"
        $stderrPath = Join-Path $runtimeRoot "server-$Port.err.log"
        $serverProcess = Start-Process -FilePath $pythonPath -ArgumentList @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', "$Port", '--no-access-log') -WorkingDirectory $backendRoot -WindowStyle Hidden -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath -PassThru
        Write-Host "Starting BE PID $($serverProcess.Id); first PII load can take a minute."
        $deadline = (Get-Date).AddSeconds(180)
        do {
            if ($serverProcess.HasExited) { throw "BE startup failed. Inspect $stderrPath" }
            Start-Sleep -Seconds 2
            try { $health = Invoke-RestMethod -Uri "$baseUrl/api/health" -TimeoutSec 3 } catch { }
            if ($null -eq $health) { Write-Host 'Waiting for BE / PII sanitizer...' }
        } while ($null -eq $health -and (Get-Date) -lt $deadline)
        if ($null -eq $health) { throw "BE startup timed out. PID $($serverProcess.Id); inspect $stderrPath" }
        Write-Host "BE stays running after the wizard so background jobs can finish. PID $($serverProcess.Id)."
        Write-Host "When no jobs are active, stop its process tree with: taskkill /PID $($serverProcess.Id) /T /F"
    }
    if ($health.db -ne 'ok') { throw 'BE database health is degraded. Fix connectivity before starting the flow.' }
    $contract = Invoke-RestMethod -Uri "$baseUrl/openapi.json" -TimeoutSec 10
    if (-not $contract.paths.PSObject.Properties['/api/impact-checks/run']) {
        throw 'BE is running older code. Restart that BE yourself, or use this launcher with -Port 8001.'
    }
    Write-Host "Connected to $baseUrl. Wizard input is in THIS terminal."
    & $pythonPath scripts/agent_terminal.py --flow --base-url $baseUrl
    $flowExit = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $flowExit
