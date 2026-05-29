# Clean restart of the VAD daemon task. Stop-ScheduledTask can orphan the detached
# python child, after which Start no-ops because it thinks an instance is still up.
# So we stop the task, kill any lingering vad-daemon python (matched by command
# line, so unrelated python is left alone), then start fresh.
$ErrorActionPreference = "SilentlyContinue"
Stop-ScheduledTask -TaskName vad-daemon
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like '*vad-daemon.py*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Start-Sleep -Milliseconds 500
Start-ScheduledTask -TaskName vad-daemon
Write-Host "vad-daemon restarted"
