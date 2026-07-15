#Requires -RunAsAdministrator
# Calm Windows Defender real-time scanning during package installs (npm, pnpm,
# uv, cargo, go) by excluding the package caches that exist on this host, plus
# any dev roots passed in. Rerun with -Remove and the same arguments to undo.
# Tradeoff: Defender stops scanning writes under the excluded paths and files
# touched by node.exe, so keep the dev roots deliberate.
param(
    [string[]]$DevRoots = @(),
    [switch]$Remove
)

$ErrorActionPreference = 'Stop'

$caches = @(
    (Join-Path $env:LOCALAPPDATA 'npm-cache'),
    (Join-Path $env:APPDATA 'npm'),
    (Join-Path $env:LOCALAPPDATA 'pnpm'),
    (Join-Path $env:LOCALAPPDATA 'Yarn'),
    (Join-Path $env:LOCALAPPDATA 'uv'),
    (Join-Path $env:USERPROFILE '.cargo'),
    (Join-Path $env:USERPROFILE '.bun'),
    (Join-Path $env:USERPROFILE 'go')
)

$paths = @($DevRoots) + @($caches | Where-Object { Test-Path $_ })
$processes = @('node.exe')

if ($Remove) {
    Remove-MpPreference -ExclusionPath $paths -ExclusionProcess $processes
} else {
    Add-MpPreference -ExclusionPath $paths -ExclusionProcess $processes
}

$prefs = Get-MpPreference
'ExclusionPath:'
$prefs.ExclusionPath | ForEach-Object { "  $_" }
'ExclusionProcess:'
$prefs.ExclusionProcess | ForEach-Object { "  $_" }
