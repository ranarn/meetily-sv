# Builds the llama-helper sidecar inside a vcvars64 environment with the Ninja generator.
# Usage: pwsh scripts/sv/build-llama-helper.ps1 [-Features vulkan|none]
param([string]$Features = 'vulkan')

$ErrorActionPreference = 'Stop'
$root = Resolve-Path "$PSScriptRoot\..\.."
$vcvars = 'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
$featureArg = if ($Features -eq 'none') { '' } else { "--features $Features" }

$cmd = "`"$vcvars`" >nul && set `"CMAKE_GENERATOR=Ninja`" && set `"LIBCLANG_PATH=C:\Program Files\LLVM\bin`" && cd /d `"$root`" && cargo build --release -p llama-helper $featureArg"
cmd /c $cmd
$code = $LASTEXITCODE
Write-Output "STATUS llama-helper features=$Features exit=$code"
exit $code
