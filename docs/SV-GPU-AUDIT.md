# GPU support audit: NVIDIA/Apple vs AMD/Intel (Vulkan)

Fork-specific. Date: 2026-10-06. Trigger: `llama-helper` had VRAM detection for Metal and CUDA but only a
`TODO: Vulkan VRAM detection`, so on an RX 9070 XT it assumed 4 GB and offloaded 8/33 layers (fixed, commit e3727a3).

Scope searched: `frontend/src-tauri/**/*.rs`, `frontend/src-tauri/Cargo.toml`, `build.rs`, `llama-helper/**`,
`frontend/src/**/*.{ts,tsx}` (no GPU-vendor code there). The archived `backend/` was not searched.
All findings are from reading the code; "Measured" marks what was verified by running the app.

| # | Where | Finding | Affects Windows+Vulkan today? | Status |
|---|---|---|---|---|
| 1 | `llama-helper/src/main.rs` `detect_vram_gb` | No Vulkan branch, fell back to 4 GB | Yes (8/33 layers, ~5x slower summaries) | **Fixed**, measured: 15.06 GB detected, 33/33 layers, 18-22 s -> 3.9 s |
| 2 | `llama-helper/src/main.rs` `calculate_gpu_layers` (~l.207-211) | KV cache is estimated from file size only (0.25 GB/1k ctx). Hybrid Qwen3.5 has KV on 8 of 32 layers: estimated 8.19 GB, actual 1024 MiB (measured). Vendor-neutral, but on smaller GPUs it limits offload needlessly | Not on 16 GB, yes on ~10-12 GB cards | Open |
| 3 | `audio/hardware_detector.rs` `detect_memory_gb` (l.109-118) | Stub: always 8 unless env `MEMORY_GB` is set (real machine: 62 GB). Tier rule gives Metal/CUDA `High` regardless of RAM but Vulkan needs `memory_gb >= 12`, so every Vulkan machine is stuck at `Medium` | No (Windows override, see 5); yes on Linux (beam 2 instead of 3) | Open |
| 4 | `audio/hardware_detector.rs` `calculate_performance_tier` | Only Metal/CUDA can reach `Ultra`; Vulkan caps at `High`. A correct fix needs discrete-vs-integrated GPU detection (Vulkan also covers weak iGPUs) | No | Open (design decision) |
| 5 | `audio/hardware_detector.rs` `get_whisper_config` (l.205-215) | On Windows the tier is ignored: beam_size is always 2 ("for stability"). Vendor-neutral, upstream decision | Yes, accuracy ceiling for everyone on Windows | Experiment candidate |
| 6 | `whisper_engine/acceleration.rs` (l.67-71) | `flash_attn` only for Metal/CUDA in fast tiers; Vulkan always `false`. whisper.cpp has a Vulkan flash-attention path (device reports `KHR_coopmat`) but stability/benefit is unverified | Yes (possible speed-up) | Experiment candidate: measure, do not just enable |
| 7 | `parakeet_engine/model.rs` l.97 | ONNX session hard-coded to `CPUExecutionProvider`: no GPU for any vendor (DirectML would serve AMD on Windows) | Only if Parakeet is used | Open, low priority (KB-Whisper is the Swedish choice) |
| 8 | `build.rs` l.52-55 vs l.81 | Windows prints an NVIDIA hint (`nvidia-smi`) but no AMD hint; AMD hint exists on Linux only. Cosmetic | No | Open, cosmetic |
| 9 | `audio/hardware_detector.rs` l.254, l.264 | `get_recommended_chunk_duration_ms` and `can_handle_realtime` have no callers (dead code) | No | Note |
| 10 | Device selection (`gpu_device = 0` in whisper) | Default device index 0. Fine here (0 = RX 9070 XT, 1 = iGPU) but machines where the iGPU enumerates first would pick it. llama.cpp skipped the iGPU on this machine | Not here | Unverified risk |

Not vendor-specific gaps (checked, no action): `whisper_engine.rs` only logs per feature; `_stderr_suppressor.rs`
mentions Metal logs only; the frontend has no GPU-vendor logic.

## Suggested order

1. Fix #3 with real RAM (small, makes the log truthful) and decide #4 separately.
2. Measure #6 (flash attention on Vulkan) and #5 (beam 5 for Swedish) with the same recording: speed and text.
3. Improve #2 only if a smaller-GPU user matters.
