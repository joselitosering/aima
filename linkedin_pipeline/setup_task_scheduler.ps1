# =============================================================================
# AIMA LinkedIn Pipeline — Windows Task Scheduler Setup
# Run once as Administrator:
#   Right-click PowerShell → "Run as Administrator"
#   cd D:\Apps\DevOps\Github\aima\linkedin_pipeline
#   .\setup_task_scheduler.ps1
# =============================================================================

$PipelineDir = "D:\Apps\DevOps\Github\aima\linkedin_pipeline"
$PythonExe   = (Get-Command python -ErrorAction SilentlyContinue).Source

if (-not $PythonExe) {
    Write-Host "ERROR: Python not found in PATH. Install Python and try again." -ForegroundColor Red
    exit 1
}

Write-Host "Python: $PythonExe" -ForegroundColor Cyan
Write-Host "Pipeline directory: $PipelineDir" -ForegroundColor Cyan
Write-Host ""

# =============================================================================
# Task 1 — AIMA-LinkedIn-Post
# Posts new articles on Tue/Wed/Thu at 10:30 AM (peak LinkedIn engagement window)
# Safe to run even with no new articles — pipeline.py deduplicates via posted_articles.json
# =============================================================================

$postAction = New-ScheduledTaskAction `
    -Execute    $PythonExe `
    -Argument   "pipeline.py" `
    -WorkingDirectory $PipelineDir

$postTriggers = @(
    New-ScheduledTaskTrigger -Weekly -DaysOfWeek Tuesday   -At "10:30AM"
    New-ScheduledTaskTrigger -Weekly -DaysOfWeek Wednesday -At "10:30AM"
    New-ScheduledTaskTrigger -Weekly -DaysOfWeek Thursday  -At "10:30AM"
)

$postSettings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 15) `
    -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName    "AIMA-LinkedIn-Post" `
    -Action      $postAction `
    -Trigger     $postTriggers `
    -Settings    $postSettings `
    -Description "Posts new AIMA articles to LinkedIn Tue/Wed/Thu at 10:30 AM. Deduplicates automatically." `
    -RunLevel    Highest `
    -Force | Out-Null

Write-Host "✓ AIMA-LinkedIn-Post registered" -ForegroundColor Green
Write-Host "  Schedule: Tuesday, Wednesday, Thursday at 10:30 AM" -ForegroundColor Gray

# =============================================================================
# Task 2 — AIMA-LinkedIn-Analytics
# Collects post engagement data daily at 9:00 AM for posts that are 48h+ old
# Writes results to post_analytics.csv
# =============================================================================

$analyticsAction = New-ScheduledTaskAction `
    -Execute    $PythonExe `
    -Argument   "analytics_collector.py" `
    -WorkingDirectory $PipelineDir

$analyticsTrigger = New-ScheduledTaskTrigger -Daily -At "9:00AM"

$analyticsSettings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
    -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName    "AIMA-LinkedIn-Analytics" `
    -Action      $analyticsAction `
    -Trigger     $analyticsTrigger `
    -Settings    $analyticsSettings `
    -Description "Collects LinkedIn post engagement stats 48h after posting. Logs to post_analytics.csv." `
    -RunLevel    Highest `
    -Force | Out-Null

Write-Host "✓ AIMA-LinkedIn-Analytics registered" -ForegroundColor Green
Write-Host "  Schedule: Daily at 9:00 AM" -ForegroundColor Gray

# =============================================================================
# Summary
# =============================================================================

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Both tasks registered successfully." -ForegroundColor Cyan
Write-Host "  View them in: Task Scheduler > Task Scheduler Library" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "IMPORTANT: The machine must be ON and awake at post time." -ForegroundColor Yellow
Write-Host "If this is a laptop: Control Panel > Power Options > disable sleep" -ForegroundColor Yellow
Write-Host "   OR migrate the pipeline to a cloud VPS for true 24/7 reliability." -ForegroundColor Yellow
Write-Host ""
Write-Host "Token expiry reminder:" -ForegroundColor Yellow
Write-Host "  LinkedIn access tokens expire in ~60 days." -ForegroundColor Yellow
Write-Host "  Re-run linkedin_auth.py before that and update .env." -ForegroundColor Yellow
