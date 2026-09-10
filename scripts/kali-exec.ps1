param(
    [string]$ConfigPath = "",
    [int]$Timeout = 120,
    [switch]$Quiet,
    [Parameter(Position = 0)]
    [string]$RemoteCommand
)

$ErrorActionPreference = "Stop"

# Default config: config/kali.ps1 next to this script's directory
if ([string]::IsNullOrWhiteSpace($ConfigPath)) {
    $ConfigPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\config\kali.ps1"
}

if ([string]::IsNullOrWhiteSpace($RemoteCommand)) {
    throw 'Usage: .\kali-exec.ps1 -RemoteCommand "nmap --version"'
}

if (-not $env:KALI_PASSWORD -and -not $env:KALI_KEY) {
    Write-Warning "KALI_PASSWORD not set. Set it via: `$env:KALI_PASSWORD='<your-password>'"
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonArgs = @(
    (Join-Path $scriptDir "kali_exec.py"),
    "--config", $ConfigPath,
    "--timeout", "$Timeout"
)

if ($Quiet) {
    $pythonArgs += "--quiet"
}

$pythonArgs += "--"
$pythonArgs += $RemoteCommand

& python @pythonArgs
exit $LASTEXITCODE
