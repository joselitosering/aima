<#
  register-task.ps1 — register (or refresh) the Instagram poster as a Windows
  scheduled task. Run ONCE from an elevated PowerShell.

    powershell -NoProfile -ExecutionPolicy Bypass -File register-task.ps1

  Schedule: every 6 hours, starting now, indefinitely (~4 runs/day — "a few
  times a day"). Each run scans all three drop folders (inbox/posts,
  inbox/carousels, inbox/reels) and, with IG_AUTO_PUBLISH=true (the configured
  default), publishes any new item fully unattended — review happens on
  Instagram itself after the fact. Flip IG_AUTO_PUBLISH=false in .env to switch
  to a PENDING/--approve review gate instead.

  To change the interval, edit -Hours below and re-run this script (Register-
  ScheduledTask with -Force overwrites the existing task).

  Runs as the CURRENT user, only when logged on: the run reads this module's own
  .env, which resolves for the logged-on user.

  Unregister:  Unregister-ScheduledTask -TaskName 'IG_Carousel' -Confirm:$false
#>
$ErrorActionPreference = 'Stop'

$TaskName = 'IG_Carousel'
$Runner   = 'D:\Apps\DevOps\Github\aima\instagram_pipeline\run-carousel.ps1'

if (-not (Test-Path $Runner)) { throw "Runner not found: $Runner" }

$Action = New-ScheduledTaskAction `
  -Execute 'powershell.exe' `
  -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$Runner`""

$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
  -RepetitionInterval (New-TimeSpan -Hours 6) `
  -RepetitionDuration ([TimeSpan]::MaxValue)

$Settings = New-ScheduledTaskSettingsSet `
  -StartWhenAvailable `
  -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
  -MultipleInstances IgnoreNew `
  -DontStopOnIdleEnd

Register-ScheduledTask `
  -TaskName $TaskName `
  -Action $Action `
  -Trigger $Trigger `
  -Settings $Settings `
  -RunLevel Limited `
  -Description 'Instagram poster: scans inbox/posts (single images), inbox/carousels (subfolders), inbox/reels (videos) for new items, uploads to Cloudinary, generates caption+hashtags via OpenRouter, and publishes fully unattended (IG_AUTO_PUBLISH=true). Every 6 hours.' `
  -Force

Write-Host "Registered '$TaskName' — every 6 hours. Runs as $env:USERNAME when logged on."
Write-Host "Dry test:  powershell -NoProfile -ExecutionPolicy Bypass -File run-carousel.ps1 -DryRun"
Write-Host "Fire now:  Start-ScheduledTask -TaskName '$TaskName'"
