Set-Location 'D:\Apps\DevOps\Github\aima\instagram_pipeline'
$env:IG_CLI_DEBUG = "1"
python instagram_carousel.py --dry-run 2>&1 | Out-File -FilePath '_debug_out.txt' -Encoding utf8
Write-Output "WROTE_DEBUG_OUT"
