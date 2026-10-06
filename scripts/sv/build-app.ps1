# Builds the Tauri app (no bundle) inside a vcvars64 environment with Ninja and a short target dir.
# Short CARGO_TARGET_DIR is required: nested CMake try-compile paths in llama-cpp-sys-2 hit MAX_PATH (260).
# Usage: pwsh scripts/sv/build-app.ps1   (run scripts/sv/build-llama-helper.ps1 first)
param([string]$TargetDir = 'D:\t', [string]$LibclangPath = 'C:\Program Files\LLVM\bin')

$ErrorActionPreference = 'Stop'
$root = Resolve-Path "$PSScriptRoot\..\.."
$vcvars = 'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'

$binDir = Join-Path $root 'frontend\src-tauri\binaries'
New-Item -ItemType Directory -Force $binDir | Out-Null
Copy-Item "$TargetDir\release\llama-helper.exe" "$binDir\llama-helper-x86_64-pc-windows-msvc.exe" -Force

$cmd = "`"$vcvars`" >nul && set `"CARGO_TARGET_DIR=$TargetDir`" && set `"CMAKE_GENERATOR=Ninja`" && set `"LIBCLANG_PATH=$LibclangPath`" && cd /d `"$root\frontend`" && pnpm tauri build --no-bundle -- --features vulkan"
cmd /c $cmd
$code = $LASTEXITCODE
Write-Output "STATUS app-build exit=$code"
exit $code
