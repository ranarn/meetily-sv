# Builds the Windows NSIS installer of the fork (Vulkan), release profile, no updater artifacts.
# Prerequisites: scripts/sv/build-llama-helper.ps1 has been run (sidecar in $TargetDir\release); the app is closed.
# Fork overrides (scripts/sv/tauri.fork.conf.json): NSIS only, no updater artifacts (we have no upstream signing key),
# and the updater endpoint points at this fork instead of upstream's releases, so upstream can never replace the fork build.
# Output: $TargetDir\release\bundle\nsis\*.exe
param([string]$TargetDir = 'D:\t')

$ErrorActionPreference = 'Stop'
$root = Resolve-Path "$PSScriptRoot\..\.."
$vcvars = 'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
$conf = Join-Path $PSScriptRoot 'tauri.fork.conf.json'

$busy = Get-Process meetily, llama-helper, ffmpeg -ErrorAction SilentlyContinue
if ($busy) { Write-Output "STATUS release blocked: close the app first ($($busy.ProcessName -join ', '))"; exit 2 }

$binDir = Join-Path $root 'frontend\src-tauri\binaries'
New-Item -ItemType Directory -Force $binDir | Out-Null
Copy-Item "$TargetDir\release\llama-helper.exe" "$binDir\llama-helper-x86_64-pc-windows-msvc.exe" -Force

$cmd = "`"$vcvars`" >nul && set `"CARGO_TARGET_DIR=$TargetDir`" && set `"CMAKE_GENERATOR=Ninja`" && set `"LIBCLANG_PATH=C:\Program Files\LLVM\bin`" && cd /d `"$root\frontend`" && pnpm tauri build --config `"$conf`" -- --features vulkan"
cmd /c $cmd
$code = $LASTEXITCODE
Write-Output "STATUS release-build exit=$code"
if ($code -eq 0) { Get-ChildItem "$TargetDir\release\bundle" -Recurse -Include *.exe, *.msi | Select-Object FullName, @{n = 'MB'; e = { [math]::Round($_.Length / 1MB, 1) } } | Format-Table -AutoSize | Out-String -Width 200 }
exit $code
