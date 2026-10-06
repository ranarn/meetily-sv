# meetily-sv — fork context (read this first)

Upstream's own `CLAUDE.md` (architecture, commands, conventions) still applies and is deliberately **untouched** so rebases stay conflict-free. This file holds only what is specific to *our fork*. Build setup details: `docs/SV-BUILD.md`.

## What this project is

Jonas's hard fork of Meetily (https://github.com/Zackriya-Solutions/meetily, MIT) with one goal: **good Swedish meeting transcription and summaries**. The released Meetily works acceptably for English but is useless for Swedish. We build from source, change what is needed, and keep tracking upstream continuously.

- Workspace language with Jonas: Swedish. Code, commits, docs in this repo: English.
- Jonas's machine: Windows 11, PowerShell (pwsh), **AMD Radeon RX 9070 XT** → GPU path is **Vulkan** (not CUDA). Use the PowerShell tool for all commands.

## Git model (hard fork with upstream tracking)

- `origin` = https://github.com/ranarn/meetily-sv (personal account `ranarn`), `upstream` = Zackriya-Solutions/meetily.
- `main` = pristine mirror of `upstream/main`. **Never commit on `main`.**
- `custom` = our work. Keep it up to date by **rebasing onto `main`** (force-push to `origin/custom` is expected and fine).
- Keep our changes small and isolated (new files, config, adapters) so upstream changes rarely conflict. Prefer adding over editing upstream files.
- Run `pwsh scripts/sv/sync-upstream.ps1` regularly: fetches upstream, fast-forwards `main`, lists new upstream commits and flags those touching files we changed. Add `-Rebase` to rebase `custom`.
- Submodule `backend/whisper.cpp` points to Zackriya's *own* whisper.cpp fork — watch it too.
- Upstream sells "Meetily PRO" (better accuracy, diarization). Community edition may be intentionally weaker; do not expect upstream to fix Swedish.

## Language/quality plan (not started)

1. Verify the language preference is actually `sv` in the running app (`get_language_preference_internal`; `"auto"` / `"auto-translate"` / language code handled in `frontend/src-tauri/src/whisper_engine/whisper_engine.rs` ~l.567-692). Auto-detect alone may explain part of the poor Swedish.
2. Transcription: evaluate **KB-Whisper** (Swedish fine-tune of Whisper by KBLab) as a ggml model; find where models are listed/downloaded in `whisper_engine` and add it. Parakeet is English-oriented — not for Swedish. (Model quality and ggml availability are NOT yet verified — check before relying on it.)
3. Summaries: providers already exist under `frontend/src-tauri/src/` (`ollama`, `openai`, `groq`, `anthropic`, `openrouter`, `summary`). Plan is a larger multilingual model via Ollama + Swedish summary prompt — mostly config/prompt work. Ollama on the RX 9070 XT is independent of the app's own llama.cpp build.

## Build status (as of 2026-10-06) — NOT yet built successfully

Toolchain installed this session: CMake 4.4.4, Vulkan SDK 1.4.363 (`VULKAN_SDK=C:\VulkanSDK\1.4.363.0`), LLVM 23.1.2 (`LIBCLANG_PATH=C:\Program Files\LLVM\bin`), VS 2022 Community (C++), Rust 1.98, Node 24, **pnpm 12.9.1 (Jonas needs latest pnpm globally — never downgrade it)**. Our one tracked change so far: pnpm 12 compatibility (`pnpm.overrides` moved from `package.json` to `frontend/pnpm-workspace.yaml`).

Progress: pnpm install OK; `whisper-rs-sys` with `--features vulkan` compiles OK; **`llama-helper` (sidecar, builtin-summary llama.cpp) fails** in `llama-cpp-sys-2` with `--features vulkan`.

Failure: sub-project `vulkan-shaders-gen` (CMake ExternalProject, Visual Studio generator) runs its install/build steps before configure → `Not a file: .../cmake_install.cmake`, `missing CMakeCache.txt`, `The system cannot find the batch label specified - VCEnd`.

Hypotheses already tested and **refuted** (don't repeat): long path / MAX_PATH (short `CARGO_TARGET_DIR=D:\t` → same error); `NUM_JOBS=1` (cargo overrides it for build scripts); `cargo build -j 1` (cmake got `--parallel 1`, same error). Ordering is broken regardless of parallelism, likely VS generator + CMake 4.x.

Next candidates, in order:
1. **Ninja generator**: `CMAKE_GENERATOR=Ninja`. Ninja is NOT bundled in this VS install (checked) → needs `winget install Ninja-build.Ninja` (ask Jonas first), and the build must run inside a `vcvars64.bat` environment so `cl.exe` is on PATH.
2. Build `llama-helper` **without** vulkan (CPU) to get a working baseline app; summaries can use Ollama anyway.
3. Try a different CMake (e.g. 3.31) if Ninja does not help.

Build procedure that reached the llama-helper step: see `docs/SV-BUILD.md`. Use `pnpm tauri build --no-bundle` (a full bundle may need updater signing keys). Run long builds in the background and verify with explicit exit-code output — a background task "completed" can still mean the script bailed out.

## Rules for working here

- Don't claim a build/fix works without running it and showing the result.
- Ask before system-level installs (winget etc.) and before pushing/force-pushing.
- Never edit `main`. Keep fork-specific files clearly separate from upstream files (`scripts/sv/`, `docs/SV-*.md`, this file).
