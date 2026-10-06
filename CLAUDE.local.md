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

## Language/quality plan (in progress)

1. Verify the language preference is actually `sv` in the running app (`get_language_preference_internal`; `"auto"` / `"auto-translate"` / language code handled in `frontend/src-tauri/src/whisper_engine/whisper_engine.rs` ~l.567-692). Auto-detect alone may explain part of the poor Swedish.
2. Transcription: evaluate **KB-Whisper** (Swedish fine-tune of Whisper by KBLab) as a ggml model; find where models are listed/downloaded in `whisper_engine` and add it. Parakeet **v3** is multilingual and lists Swedish among its 25 languages (HF model card, Fleurs WER 15.08%); the app's default `parakeet-tdt-0.6b-v3-int8` is therefore a Swedish candidate to benchmark against Whisper/KB-Whisper (the v2 model is English-only). (Model quality and ggml availability are NOT yet verified — check before relying on it.)
3. Summaries: providers already exist under `frontend/src-tauri/src/` (`ollama`, `openai`, `groq`, `anthropic`, `openrouter`, `summary`). Plan is a larger multilingual model via Ollama + Swedish summary prompt — mostly config/prompt work. Ollama on the RX 9070 XT is independent of the app's own llama.cpp build.

## Swedish transcription findings (2026-10-06)

- **Done:** KB-Whisper large q5_0 added to the Whisper catalog as `kb-large-q5_0` (`config.rs`, `whisper_engine.rs`, `whisper.ts`, `WhisperModelManager.tsx`; commit 2d54f9e). Source `KBLab/kb-whisper-large` `ggml-model-q5_0.bin` (1.08 GB, Apache-2.0) — file existence verified on HF.
- **UI:** Transcript Model dropdown has only *Parakeet* and *Local Whisper*; models are listed *below* it. The language button ("Language", globe icon) is in the transcript panel on the main page and is shown **only for `localWhisper`**. Parakeet's language dialog only offers auto/auto-translate (`LanguageSelection.tsx:133`), so Parakeet cannot be forced to Swedish. Parakeet "Compact" is v2 = English-only.
- **Defaults are still upstream's:** provider Parakeet v3 ("Lightning"), language `auto` (localStorage `primaryLanguage`, synced to Rust; Rust-side initial value is `auto-translate`, see `lib.rs:126`).
- **Defaults changed (commit 48baee9):** `DEFAULT_WHISPER_MODEL` = `kb-large-q5_0` (Rust + TS), language default `sv` (`lib.rs`, `ConfigContext.tsx`). Provider default is still Parakeet — it is hardcoded in ~10 places (engine.rs x4, api.rs, onboarding.rs, setting.rs, commands.rs, ConfigContext, Sidebar, useTranscriptionModels), changing it all is conflict-prone and was deliberately skipped.
- **GPU verified (2026-10-06, app log):** `use gpu = 1`, `gpu_device = 0`, `ggml_vulkan: 0 = AMD Radeon RX 9070 XT`, `Vulkan0 total size = 1080.47 MB` for `kb-large-q5_0`; the iGPU is device 1. Log how: start `D:\t\release\meetily.exe` with `RUST_LOG=info` and redirect stderr to a file (there is no app log file otherwise). Upstream calls `create_state()` per transcription, so the Vulkan backend/compute buffers are re-initialised for every chunk — possible performance improvement.
- **Jonas's first impression (not measured):** KB-Whisper with `sv` is better than the default setup. Test sentence transcribed correctly ("Okej, tjena nu kör vi här ett test för att se hur allting funkar."). Not yet measured: WER vs. reference text, latency.
- **Research (secondary sources, not independently verified):** KBLab reports Swedish WER 5.4 (FLEURS) vs 7.8 for whisper-large-v3; Parakeet v3 15.08 (FLEURS). KB-small reportedly beats large-v3. Klang Pianissimo claims 4.5 but is vendor marketing. No source found on real multi-speaker Swedish meetings.
- **Summaries (built-in AI, 2026-10-06):** NOT Ollama — appen kör sidecaren `llama-helper` (llama.cpp) med GGUF i `%APPDATA%\com.meetily.ai\models\summary`. Added `qwen3.5:9b` (Q4_K_M), `gemma4:12b` (Q4_K_M) and `gemma4:12b-qat` (never run; Q6 9B was added and removed again) in `summary_engine/models.rs` (+ priority in `commands.rs`, size label in `onboarding-summary-model.ts`; commit f6c4095). Jonas: 9B Q4 summarises Swedish "very well", a bit slow. Cause found in log: `llama-helper/src/main.rs` had `TODO: Vulkan VRAM detection` → assumed 4 GB → `Offloading 8/33 layers`. Fixed with `detect_vulkan_vram()` (ggml device query; commit e3727a3) — **verified in app log:** `Vulkan VRAM detected: 15.06 GB free`, `offloaded 33/33 layers`, Total time 18.4/21.9 s → 3.9 s (87 tok/s) for ~950-char summaries. KV-cache heuristic in `calculate_gpu_layers` also overestimates for hybrid Qwen3.5 (8.19 GB estimated vs ~1 GB actual) — not fixed yet. llama-cpp-2/sys upgraded to 0.1.158 (commit 9c5609b; llama-helper adapted to the vocab API; Gemma 4 summary verified by Jonas, Qwen not re-run on it; 0.1.146 already knew the `gemma4` arch). Gemma 4 uses its own template (`<|turn>…<turn|>`, empty `<|channel>thought` block) in `models.rs`. Jonas's verdict: Qwen 9B and Gemma 4 12B give similar, good Swedish summaries (Gemma resolved a name better); Gemma was slow only because WoW occupied the GPU (unmeasured). Qwen3.8 exists only as 27B (17.1 GB Q4_K_M, does not fit 16 GB). Onboarding still recommends Qwen 4B (RAM rule in `commands.rs`, upstream tests assert it) — left alone on purpose. Jonas decided to stop testing summaries; the model list is considered done. `llama-helper` GPU-layer heuristic (KV estimate, assumed 33 layers) still ignores `layer_count`; llama.cpp's own fit API is an option if it ever matters.
- **ffmpeg (2026-10-06):** upgraded 8.0.1 -> **9.0.2** on Windows. `build/ffmpeg.rs` now downloads the version-pinned gyan.dev release `GyanD/codexffmpeg/releases/download/9.0.2/ffmpeg-9.0.2-essentials_build.zip` (sha256 `60f46726…47ba` verified against the GitHub digest; upstream used its own mirror of 8.0.1; mac/Linux URLs untouched). The build caches the binary in `frontend/src-tauri/binaries/` (gitignored) — delete that file to force a re-download after changing the URL. Verified: app's AAC-LC 192k mp4 encode command gives identical result on 8.0.1 and 9.0.2 (synthetic 2 s audio) and decodes cleanly. Not tested: import/retranscription of other formats (mp3/flac/mkv via `audio/ffmpeg.rs`).
- **TODO audit (Jonas's request): find every place where GPU/VRAM support exists for NVIDIA (CUDA) or Apple (Metal) but not for AMD/Intel (Vulkan)** — same class of bug as the `detect_vram_gb` hole. Check `cfg(feature = "cuda")` / `"metal"` sites in `llama-helper`, `frontend/src-tauri` (hardware_detector, whisper_engine acceleration decision, system_monitor, GPU layer/threads heuristics, UI texts) and `build.rs`/Cargo features.
- **Ideas not done:** KB-medium/small entries (faster); Gemma 4 12B for summaries (after llama-cpp 0.1.158 upgrade, "step 2b"); Swedish summary prompt review; remove the Q6 9B entry if unused; WER measurement against a reference text; npm minor/major upgrades (plan above).

## Build status (as of 2026-10-06) — app builds and RUNS (Vulkan build, GPU use verified)

Toolchain (latest where possible): CMake 4.4.4, Vulkan SDK 1.4.363 (`VULKAN_SDK=C:\VulkanSDK\1.4.363.0`), LLVM 23.1.2, VS 2022 17.14 (a newer 17.14.41 exists, not installed), Rust 1.99, Node 24, **Ninja 1.13.2**, **pnpm 12.9.1 (Jonas needs latest pnpm globally — never downgrade it)**.

Working recipe — `scripts/sv/build-llama-helper.ps1` then `scripts/sv/build-app.ps1` (both run inside `vcvars64.bat`, set `CMAKE_GENERATOR=Ninja`, use `CARGO_TARGET_DIR=D:\t`). Result: `D:\t\release\meetily.exe` (built, `exit=0`; launched by Jonas, records and transcribes OK). Close the app before rebuilding — a running `meetily.exe` locks files in `D:\t\release` (os error 32).

Root causes found (all verified):
1. VS generator runs `vulkan-shaders-gen` ExternalProject steps out of order → **fixed by Ninja generator**.
2. Under Ninja the nested try-compile fails with `LNK1104 ... intermediate.manifest` because the path is exactly 260 chars (MAX_PATH) → **fixed by short `CARGO_TARGET_DIR=D:\t`**.
3. `whisper-rs-sys 0.11.1` uses bindgen 0.69.5, which produces an *opaque* `whisper_full_params` (only `_address`) with libclang 23 → 71 E0609 errors in `whisper-rs`. **Fixed by upgrading to `whisper-rs 0.16.0` / `whisper-rs-sys 0.15.0`** (verified: builds with LLVM 23; needed 6 small API adaptations in `whisper_engine.rs`). A libclang 18 workaround was used briefly and is no longer needed.
4. `cmd` `set VAR=x && ...` keeps the trailing space in the value → always quote: `set "VAR=x"`.

Verified on the GPU (app log): whisper (whisper-rs 0.16, `Vulkan0`) and the `llama-helper` sidecar (33/33 layers on Vulkan0).

Dependency upgrade plan (one step per commit, build after each): 1) whisper-rs 0.16 ✅ 2) Rust deps within semver (~270) 3) Tauri crates + npm packages in sync 4) low/medium-risk npm (radix, blocknote, tiptap …) 5) major jumps one at a time, Jonas decides (React 19, Next 16, Tailwind 4, TS 7, Zod 4, lucide 1.x) 6) Visual Studio 17.14.41.

Next: launch the app, verify Whisper uses the RX 9070 XT, then the language/KB-Whisper/summary plan above.
## Rules for working here

- Don't claim a build/fix works without running it and showing the result.
- Ask before system-level installs (winget etc.) and before pushing/force-pushing.
- Never edit `main`. Keep fork-specific files clearly separate from upstream files (`scripts/sv/`, `docs/SV-*.md`, this file).
