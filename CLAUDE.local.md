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

## Build status (as of 2026-10-06) — app BUILDS (Vulkan); GPU use and runtime NOT yet verified

Toolchain (latest where possible): CMake 4.4.4, Vulkan SDK 1.4.363 (`VULKAN_SDK=C:\VulkanSDK\1.4.363.0`), LLVM 23.1.2, VS 2022 17.14 (a newer 17.14.41 exists, not installed), Rust 1.99, Node 24, **Ninja 1.13.2**, **pnpm 12.9.1 (Jonas needs latest pnpm globally — never downgrade it)**.

Working recipe — `scripts/sv/build-llama-helper.ps1` then `scripts/sv/build-app.ps1` (both run inside `vcvars64.bat`, set `CMAKE_GENERATOR=Ninja`, use `CARGO_TARGET_DIR=D:\t`). Result: `D:\t\release\meetily.exe` (built, `exit=0`; not yet launched).

Root causes found (all verified):
1. VS generator runs `vulkan-shaders-gen` ExternalProject steps out of order → **fixed by Ninja generator**.
2. Under Ninja the nested try-compile fails with `LNK1104 ... intermediate.manifest` because the path is exactly 260 chars (MAX_PATH) → **fixed by short `CARGO_TARGET_DIR=D:\t`**.
3. `whisper-rs-sys 0.11.1` uses bindgen 0.69.5, which produces an *opaque* `whisper_full_params` (only `_address`) with libclang 23 → 71 E0609 errors in `whisper-rs`. **Fixed by pointing `LIBCLANG_PATH` at libclang 18.1.1** (`D:\libclang18\libclang.dll`, extracted from the PyPI wheel `libclang==18.1.1`; pass `-LibclangPath D:\libclang18` to `build-app.ps1`). `llama-cpp-sys-2` (bindgen 0.72) is fine with either.
4. `cmd` `set VAR=x && ...` keeps the trailing space in the value → always quote: `set "VAR=x"`.

Mind: `D:\libclang18` is not tracked; recreate it (see SV-BUILD.md) on a fresh machine. Unverified: that the Vulkan sidecar/app actually run on the GPU.

Next: launch the app, verify Whisper uses the RX 9070 XT, then the language/KB-Whisper/summary plan above.
## Rules for working here

- Don't claim a build/fix works without running it and showing the result.
- Ask before system-level installs (winget etc.) and before pushing/force-pushing.
- Never edit `main`. Keep fork-specific files clearly separate from upstream files (`scripts/sv/`, `docs/SV-*.md`, this file).
