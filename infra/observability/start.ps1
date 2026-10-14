param(
    [ValidateSet('configure','backend','alloy','benchmark','status','validate','local-start','local-stop')]
    [string]$Target = 'status'
)
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$pythonPath = Join-Path $repoRoot 'backend/.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Run uv sync from backend/ first.' }
& $pythonPath (Join-Path $PSScriptRoot 'manage.py') $Target
exit $LASTEXITCODE
