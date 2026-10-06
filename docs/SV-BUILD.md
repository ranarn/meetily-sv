# Building meetily-sv on Windows (AMD GPU / Vulkan)

Fork-specific notes. Upstream's general guide is `docs/BUILDING.md`.

## Prerequisites (installed via winget unless noted)

| Tool | Version used | Notes |
|---|---|---|
| Visual Studio 2022 | Community | "Desktop development with C++" workload |
| CMake | 4.4.4 | `Kitware.CMake` |
| Vulkan SDK | 1.4.363.0 | `KhronosGroup.VulkanSDK`; sets `VULKAN_SDK` (machine env) |
| LLVM | 23.1.2 | `LLVM.LLVM`; needed for libclang (bindgen in `whisper-rs-sys`) |
| Rust | 1.98 | `rustfmt` missing → harmless "Internal rustfmt error (non-fatal)" |
| Node / pnpm | 24 / **12.9.1** | Latest pnpm required; project adapted (see below) |

New terminals pick up PATH/`VULKAN_SDK` automatically; an already-open shell does not. Refresh with:

```powershell
$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
$env:VULKAN_SDK = [Environment]::GetEnvironmentVariable('VULKAN_SDK','Machine')
$env:LIBCLANG_PATH = 'C:\Program Files\LLVM\bin'
```

## pnpm 12

Upstream pins pnpm 9.15.9 and keeps `pnpm.overrides` in `frontend/package.json`. pnpm 10+ ignores that field. This fork keeps the same overrides in `frontend/pnpm-workspace.yaml` instead; `pnpm install --frozen-lockfile` works with the unchanged `pnpm-lock.yaml`. (Good candidate for an upstream PR.)

## Build steps

```powershell
cd frontend
pnpm install --frozen-lockfile

# 1. Sidecar (builtin-summary engine) — must exist before the app builds
cd ..
cargo build --release -p llama-helper --features vulkan
New-Item -ItemType Directory -Force frontend\src-tauri\binaries | Out-Null
Copy-Item target\release\llama-helper.exe frontend\src-tauri\binaries\llama-helper-x86_64-pc-windows-msvc.exe -Force

# 2. App (no installer bundling)
cd frontend
pnpm tauri build --no-bundle -- --features vulkan
```

`frontend/build-gpu.bat` does the same plus a full bundle, but hardcodes LLVM at `C:\Program Files\LLVM\bin`.

## Known issue: llama-helper + Vulkan fails

See "Build status" in `CLAUDE.local.md` for symptoms, refuted hypotheses and next candidates. Short version: `vulkan-shaders-gen` ExternalProject steps run out of order under the Visual Studio generator.
