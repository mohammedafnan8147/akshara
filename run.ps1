param(
    [int]$Port = 8765,
    [switch]$Reset
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$python = $null

# Prefer a real Python 3 launcher. The Windows store `python` alias may be 2.x.
if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>$null
    if ($LASTEXITCODE -eq 0) { $python = @('py', '-3') }
}

if (-not $python -and (Get-Command python -ErrorAction SilentlyContinue)) {
    & python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>$null
    if ($LASTEXITCODE -eq 0) { $python = @('python') }
}

if (-not $python) {
    $bundled = Join-Path $env:USERPROFILE '.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
    if (Test-Path $bundled) { $python = @($bundled) }
}

if (-not $python) {
    Write-Error 'Python 3.10+ was not found. Install Python 3 and run this script again.'
    exit 1
}

$serverArgs = @('-m', 'akshara.server', '--port', $Port)
if ($Reset) { $serverArgs += '--reset' }

$allArgs = @()
if ($python.Count -gt 1) { $allArgs += $python[1..($python.Count - 1)] }
$allArgs += $serverArgs
& $python[0] @allArgs
