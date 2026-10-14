<#
  register-ga4-task.ps1 - Register (or refresh) the daily GA4 traffic refresh as
  a Windows scheduled task.

  Runs `python ga4_collector.py` from this folder. The collector writes
  ga4_traffic.csv, then commits and pushes it to origin/main (dashboard reads it).

  ENCODING NOTE: keep this file pure ASCII (Windows PowerShell 5.1 decodes a
  BOM-less file as ANSI).

  Run ONCE from an elevated PowerShell:

    powershell -NoProfile -ExecutionPolicy Bypass -File register-ga4-task.ps1

  Schedule: daily 06:00 local time. StartWhenAvailable runs a missed fire at next
  wake/logon. Runs as the CURRENT user, only when logged on (git push uses that
  user's stored credentials).

  Unregister:  Unregister-ScheduledTask -TaskName 'AIMA_GA4_Refresh' -Confirm:$false
#>

$ErrorActionPreference = 'Stop'

$TaskName = 'AIMA_GA4_Refresh'
$Dir      = 'D:\Apps\DevOps\Github\aima\linkedin_pipeline'
$Script   = Join-Path $Dir 'ga4_collector.py'

if (-not (Test-Path $Script)) { throw "Collector not found: $Script" }

$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { throw "python not found on PATH" }

$Action = New-ScheduledTaskAction `
  -Execute $py.Source `
  -Argument 'ga4_collector.py' `
  -WorkingDirectory $Dir

$Trigger = New-ScheduledTaskTrigger -Daily -At 6:00AM

$Settings = New-ScheduledTaskSettingsSet `
  -StartWhenAvailable `
  -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
  -MultipleInstances IgnoreNew

Register-ScheduledTask `
  -TaskName $TaskName `
  -Action $Action `
  -Trigger $Trigger `
  -Settings $Settings `
  -RunLevel Limited `
  -Description 'AIMA: python ga4_collector.py - refresh ga4_traffic.csv from GA4 and push to origin/main. Daily 06:00.' `
  -Force

Write-Host "Registered '$TaskName' - daily 06:00. Runs as $env:USERNAME when logged on."
Write-Host "Test now:  Start-ScheduledTask -TaskName '$TaskName'"
