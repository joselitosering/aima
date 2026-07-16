<#
  run-carousel.ps1 — daily runner for the Instagram carousel poster.

  Preflights (python on PATH, inbox exists, no stale lock), runs
  `python instagram_carousel.py`, logs an outcome line, always releases the
  lock (finally). Mirrors ../linkedin_pipeline conventions.

    powershell -NoProfile -ExecutionPolicy Bypass -File run-carousel.ps1
    powershell -NoProfile -ExecutionPolicy Bypass -File run-carousel.ps1 -DryRun

  -DryRun exercises discovery + caption generation only (no Cloudinary/IG).
#>
param([switch]$DryRun)

$ErrorActionPreference = 'Stop'
$Here   = Split-Path -Parent $MyInvocation.MyCommand.Path
$Script = Join-Path $Here 'instagram_carousel.py'
$Lock   = Join-Path $Here '.carousel.lock'
$Log    = Join-Path $Here 'runner-log.jsonl'

function Write-Outcome($outcome, $notes) {
  $line = @{ ts = (Get-Date).ToString('o'); outcome = $outcome; dryRun = [bool]$DryRun; notes = $notes } | ConvertTo-Json -Compress
  Add-Content -Path $Log -Value $line -Encoding utf8
}

# --- preflight ---
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  Write-Outcome 'halt_preflight' 'python not on PATH'; throw 'python not on PATH'
}
if (Test-Path $Lock) {
  $pidTxt = (Get-Content $Lock -Raw).Trim()
  if ($pidTxt -and (Get-Process -Id $pidTxt -ErrorAction SilentlyContinue)) {
    Write-Outcome 'halt_preflight' "lock present (PID $pidTxt) — run active"
    Write-Host "Another run is active (PID $pidTxt). Exiting."; return
  }
  Remove-Item $Lock -Force   # stale lock, prior run died
}

$global:LASTEXITCODE = 0
Set-Content -Path $Lock -Value $PID -Encoding ascii
try {
  $args = @($Script)
  if ($DryRun) { $args += '--dry-run' }
  Write-Host "Running: python $($args -join ' ')"
  & python @args
  if ($LASTEXITCODE -ne 0) { Write-Outcome 'error' "python exit $LASTEXITCODE"; throw "python exit $LASTEXITCODE" }
  Write-Outcome 'ok' 'run complete'
}
finally {
  Remove-Item $Lock -Force -ErrorAction SilentlyContinue
}
Write-Host 'Done.'
