$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$connectionFile = Join-Path $projectRoot "runtime/netconf/connection.env"
if (-not (Test-Path $connectionFile)) {
    throw "Run scripts/wsl-netconf-install.sh first; missing $connectionFile"
}

& (Join-Path $projectRoot ".venv/Scripts/python.exe") -m pytest -v (Join-Path $projectRoot "tests/netconf")
exit $LASTEXITCODE