param(
    [ValidateSet("status", "validate")]
    [string]$Command = "validate",
    [string]$Episode = "episodes/gas-hwalmyeongsu",
    [switch]$All
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$bundledPython = "C:\Users\7500F\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue

if ($pythonCommand) {
    $pythonExe = $pythonCommand.Source
} elseif (Test-Path -LiteralPath $bundledPython) {
    $pythonExe = $bundledPython
} else {
    throw "Python 3.12+ was not found. Install Python or load Codex workspace dependencies."
}

Push-Location $repoRoot
try {
    if ($Command -eq "status") {
        & $pythonExe scripts/pipeline.py status --episode $Episode
    } elseif ($All) {
        & $pythonExe scripts/pipeline.py validate --all
    } else {
        & $pythonExe scripts/pipeline.py validate --episode $Episode
    }
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
