# One-time setup: build the daemon's dedicated 3.12 venv and install deps.
# torch has no wheels for the system 3.14, hence a pinned interpreter. Routed
# through coily because the repo lockdown denies bare uv.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
coily pkg uv venv --python 3.12 .venv
coily pkg uv pip install --python .venv\Scripts\python.exe -r requirements.txt
Write-Host "venv ready. Next: .venv\Scripts\python.exe vad-daemon.py --list-devices"
