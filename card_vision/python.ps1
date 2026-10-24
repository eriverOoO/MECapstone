# Forward arguments to the project Python. No system Python is modified.
$projectRoot = $PSScriptRoot
$localPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
$bundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$localDependencies = Join-Path (Split-Path $projectRoot -Parent) '.deps'
$previousPythonPath = $env:PYTHONPATH
try {
    if (Test-Path -LiteralPath $localPython) {
        & $localPython @args
    } elseif ((Test-Path -LiteralPath $bundledPython) -and (Test-Path -LiteralPath $localDependencies)) {
        $env:PYTHONPATH = $localDependencies
        & $bundledPython @args
    } else {
        & python @args
    }
    $resultCode = $LASTEXITCODE
} finally {
    $env:PYTHONPATH = $previousPythonPath
}
exit $resultCode
