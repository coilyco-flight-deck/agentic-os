# Launcher for vad-daemon.py. Used by the Task Scheduler login task (register-task.ps1)
# and runnable by hand for testing. Set the VAD_DEVICE user env var to your raw
# hardware mic index/name (see README; `setx VAD_DEVICE "<index>"`); if unset the
# daemon uses the system default input device.
$here = $PSScriptRoot
$log = Join-Path $here "vad-daemon.log"
$launcherLog = Join-Path $here "launcher.log"
# Launcher-level errors (missing venv, bad path) go here; the daemon writes its
# own runtime log to $log via --log-file. Two files so a silent start is never
# ambiguous: launcher.log proves the wrapper ran, vad-daemon.log proves Python did.
"$(Get-Date -Format o) launcher start (VAD_DEVICE=$env:VAD_DEVICE)" | Out-File -FilePath $launcherLog -Encoding utf8
try {
    $py = Join-Path $here ".venv\Scripts\python.exe"
    if (-not (Test-Path $py)) { throw "venv missing at $py - run setup-venv.ps1 first" }
    $daemon = Join-Path $here "vad-daemon.py"
    # Threshold 0.3 (not the daemon's 0.5 default) is tuned to Kai's raw Razer mic:
    # silero reads the ambient hum at ~0.0, and her speech dips to 0.3-0.4 on soft
    # syllables, so 0.5 commits ~2s early mid-sentence. Override via env to retune.
    $threshold = if ($env:VAD_THRESHOLD) { $env:VAD_THRESHOLD } else { "0.3" }
    $cmdArgs = @($daemon, "--log-file", $log, "--vad-threshold", $threshold)
    if ($env:VAD_DEVICE) { $cmdArgs += @("--device", $env:VAD_DEVICE) }
    if ($env:VAD_SILENCE) { $cmdArgs += @("--silence-timeout", $env:VAD_SILENCE) }
    & $py @cmdArgs
    "$(Get-Date -Format o) daemon exited with code $LASTEXITCODE" | Out-File -FilePath $launcherLog -Append -Encoding utf8
} catch {
    "$(Get-Date -Format o) launcher error: $_" | Out-File -FilePath $launcherLog -Append -Encoding utf8
    throw
}
