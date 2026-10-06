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

## Build steps (working recipe, verified 2026-10-06)

```powershell
# 1. Sidecar (builtin-summary engine) — Ninja + vcvars64 + short target dir
pwsh scripts/sv/build-llama-helper.ps1            # needs CARGO_TARGET_DIR=D:\t in the calling shell
# 2. App (copies the sidecar, then `pnpm tauri build --no-bundle -- --features vulkan`)
pwsh scripts/sv/build-app.ps1
```

Why each piece is needed (all verified, see `CLAUDE.local.md` for the history):

- **Ninja** (`winget install Ninja-build.Ninja`): the Visual Studio generator runs the `vulkan-shaders-gen` ExternalProject steps out of order.
- **Short `CARGO_TARGET_DIR=D:\t`**: nested CMake try-compile paths hit MAX_PATH (260) → `LNK1104 intermediate.manifest`.
- **`vcvars64.bat` environment**: Ninja needs `cl.exe` on PATH.
- **`whisper-rs` >= 0.16** (`whisper-rs-sys` 0.15): the older 0.13.2 pulled bindgen 0.69.5, which yields an opaque `whisper_full_params` with libclang 23 (needed a libclang 18 workaround until upgraded).
- In `cmd`, write `set "VAR=x"` — an unquoted `set VAR=x && ...` keeps the trailing space.
