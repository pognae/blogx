param(
  [string]$ProjectDir = (Resolve-Path "$PSScriptRoot\..").Path,
  [string]$TaskName = "TistoryAutoPublisher",
  [string]$Time = "14:00"
)

$ProjectDir = (Resolve-Path $ProjectDir).Path
$Runner = Join-Path $ProjectDir "scripts\run_publish_once.bat"

$Action = New-ScheduledTaskAction `
  -Execute "cmd.exe" `
  -Argument "/c `"$Runner`"" `
  -WorkingDirectory $ProjectDir

$Trigger = New-ScheduledTaskTrigger -Daily -At $Time
$Settings = New-ScheduledTaskSettingsSet `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -StartWhenAvailable `
  -ExecutionTimeLimit (New-TimeSpan -Hours 1)

Register-ScheduledTask `
  -TaskName $TaskName `
  -Action $Action `
  -Trigger $Trigger `
  -Settings $Settings `
  -Description "Publish queued Tistory posts from local files every day at $Time." `
  -Force

Write-Host "Registered task '$TaskName' at $Time"
Write-Host "Command: $Runner"
