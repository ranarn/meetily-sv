# Copies the built app (exe + sidecars + DLLs + templates) from the Cargo target dir to a stable run folder,
# so rebuilds never touch the copy you actually run. Refuses to overwrite while the app is running.
# Usage: pwsh scripts/sv/install-local.ps1 [-TargetDir D:\t] [-RunDir D:\meetily-sv-release\app]
param([string]$TargetDir = 'D:\t', [string]$RunDir = 'D:\meetily-sv-release\app')

$ErrorActionPreference = 'Stop'
$src = Join-Path $TargetDir 'release'
$busy = Get-Process meetily, llama-helper, ffmpeg -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "$RunDir\*" }
if ($busy) { Write-Output "STATUS install blocked: close the app first"; exit 2 }

New-Item -ItemType Directory -Force $RunDir | Out-Null
$files = 'meetily.exe', 'ffmpeg.exe', 'llama-helper.exe', 'onnxruntime.dll', 'onnxruntime_providers_shared.dll', 'DirectML.dll'
foreach ($f in $files) {
    if (-not (Test-Path "$src\$f")) { Write-Output "STATUS install failed: missing $src\$f"; exit 1 }
    Copy-Item "$src\$f" "$RunDir\$f" -Force
}
Copy-Item "$src\templates" "$RunDir\templates" -Recurse -Force
Write-Output "STATUS install exit=0 -> $RunDir"
Get-ChildItem $RunDir | Select-Object Name, @{n = 'MB'; e = { [math]::Round($_.Length / 1MB, 1) } } | Format-Table -AutoSize | Out-String
