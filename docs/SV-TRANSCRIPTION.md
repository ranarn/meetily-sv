# Swedish transcription: experiments and findings

Fork-specific. Date: 2026-10-06. Model: KB-Whisper large q5_0 via whisper-rs 0.16 on Vulkan (RX 9070 XT).
Tools: `scripts/sv/whisper-bench` (same whisper-rs calls/parameters as the app), `wer.py`, `review-diff.py`,
`split-meeting.py`, `facit-to-ref.py`, `live-to-hyp.py`, `live-chunks.py`, `merge-chunks.py`.
No meeting audio or text is stored in the repo.

## Test material

| Set | What | Size | Notes |
|---|---|---|---|
| FLEURS sv_se **dev** | Read single-speaker speech, public (CC-BY-4.0) | 40 clips, 453 s, 843 words | Dev, not test, to avoid tuning on the split KB reports |
| Real meeting | Jonas's own meeting, 5 clips cut at pauses from the most speech-dense 4 min, facit written by hand | 222 s, 691 words (650 in content mode) | Hard audio (mixed mono, overlapping speech, hesitations). Facit is itself imperfect (spelling mistakes, unclear passages) |

Metrics: **strict** = WER with hesitation sounds (eh, ehm, mm ...) dropped on both sides. **content** = additionally drops
discourse particles (liksom, ju, ja, nej ...) and maps common spoken spellings (dom, dethär ...) on both sides.
Both are reported; content is not a replacement for strict.

## Baselines

- FLEURS: 6.29 % WER (53/843).
- Real meeting, app's own live transcript (`transcripts.json`): **27.35 % strict (189/691), 21.08 % content (137/650)**.
- The app feeds Whisper short chunks (median 3.6 s, p90 9.6 s, max 24.2 s, none > 30 s). Replaying the same chunk boundaries offline
  reproduces the live result closely (193 vs 189 errors), so offline experiments use `live-chunks.py` chunks.
  Testing on whole 45 s clips is NOT representative (see "Lessons").

## Results on the real meeting (app-like chunks, strict / content errors)

| Change | Strict | Content | Verdict |
|---|---|---|---|
| none (replay of app) | 193 | 140 | baseline |
| full precision f16 instead of q5_0 | 190 | 138 | noise |
| beam 5 | 193 | 140 | no effect |
| dynaudnorm on audio | 184 | 132 | small, consistent gain (-9) |
| f16 + dynaudnorm | 179 | 128 | small gain |
| **initial prompt, spoken-style Swedish** | **156** | **112** | **-19 %, better in all 5 clips** |
| same, other wording with filler words | 160 / 159 | 114 / 115 | robust to wording |
| prompt without filler words (plain description) | 203 | 150 | does not help |
| prompt with participant names only | 193 | 141 | no help (names taken from this very meeting) |
| names + style prompt | 165 | 118 | worse than style alone |
| f16 + dynaudnorm + style prompt | 155 | 110 | no extra gain over prompt alone |

Checks on the winning prompt: FLEURS 6.41 % vs 6.29 % (no harm); prompt phrases are not copied into the output (0 occurrences);
no hesitation tokens appear in the output (0 vs 0). The gain comes from keeping spoken-language words the model otherwise
deletes (deletions were the largest error class: 74 of 180 in the first baseline).

## Implemented

`whisper_engine.rs`: for language `sv`, `set_initial_prompt(SWEDISH_STYLE_PROMPT)` in both transcription functions.
Not yet verified in the running app (the numbers above are offline replays).

## Lessons / refuted hypotheses

- Decoding thresholds (no_speech 0.55 -> 1.0, logprob -1.0 -> -3.0): identical output in all 12 conditions. Not the cause of dropped text.
- Whole-clip tests (42-46 s) showed fragile dropouts of ~27 words that depend on tiny numeric changes (f16, prompt, loudnorm).
  The app never feeds >30 s chunks, so this is a test artefact, but it shows that no_timestamps(true) + >30 s windows can lose text.
- Beam size and flash attention: no gain (also on FLEURS, see `SV-GPU-AUDIT.md`).
- Audio filters: loudnorm and denoise (afftdn) made things worse; dynaudnorm helped slightly.
- With 5 clips and ~690 words, differences below ~10 errors are noise. Only effects that are consistent per clip are trusted.

## Open ideas (not done)

- Carry the end of the previous chunk's text into the prompt (context continuity) - untested.
- Dynamic level normalisation (dynaudnorm) in the capture pipeline: small gain, needs a streaming implementation.
- KB-Whisper "strict" variant (more verbatim): the ggml files on its HF revision are copies of the standard model (identical sha256),
  the safetensors differ; would need conversion with whisper.cpp's convert script. The prompt may already capture most of the gain.
- More facit (other meetings/speakers) before trusting small effects. `review-diff.py` lists every difference for fixing the facit.
