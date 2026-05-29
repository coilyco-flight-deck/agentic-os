# Registers a Windows login task that starts the VAD daemon hidden in Kai's
# interactive session. It must run as the logged-on user (not SYSTEM): the daemon
# opens the mic and synthesizes keystrokes into the active desktop, neither of
# which works from a non-interactive service account.
#
# Run once: powershell -ExecutionPolicy Bypass -File register-task.ps1
# Then start without rebooting: Start-ScheduledTask -TaskName vad-daemon
$ErrorActionPreference = "Stop"
$taskName = "vad-daemon"
$launcher = Join-Path $PSScriptRoot "run-vad-daemon.ps1"

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$launcher`""
$trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -StartWhenAvailable `
    -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Force
Write-Host "Registered task '$taskName' (AtLogOn). Start now: Start-ScheduledTask -TaskName $taskName"
