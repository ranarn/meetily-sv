// Offline Whisper benchmark: same whisper-rs calls and parameters as the app
// (frontend/src-tauri/src/whisper_engine/whisper_engine.rs, transcribe_audio_with_confidence),
// but with beam size and flash attention controllable from the command line.
//
// Usage:
//   whisper-bench --model <ggml.bin> --dir <wav dir> --list <names.txt> --out <hyp.tsv>
//                 [--lang sv] [--beam 2] [--flash 0|1] [--temp 0.2] [--prompt-file <utf8 text file>]
//                 [--carry N]  (last N words of the previous chunk of the same clip are added to the prompt)
//                 [--no-speech-thold 0.55] [--logprob-thold -1.0] [--entropy-thold 2.4]
// --beam 0 = greedy. The first clip of the list is transcribed once as a warm-up and not timed.
// Output TSV: <wav name> \t <seconds> \t <text>

use anyhow::{anyhow, bail, Context, Result};
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;
use std::time::Instant;
use whisper_rs::{FullParams, SamplingStrategy, WhisperContext, WhisperContextParameters};

fn read_wav_16k_mono(path: &PathBuf) -> Result<Vec<f32>> {
    let mut reader = hound::WavReader::open(path).with_context(|| format!("open {}", path.display()))?;
    let spec = reader.spec();
    if spec.sample_rate != 16000 || spec.channels != 1 {
        bail!("{}: expected 16 kHz mono, got {} Hz, {} ch", path.display(), spec.sample_rate, spec.channels);
    }
    match spec.sample_format {
        hound::SampleFormat::Int => Ok(reader
            .samples::<i16>()
            .map(|s| s.map(|v| v as f32 / 32768.0))
            .collect::<std::result::Result<Vec<_>, _>>()?),
        hound::SampleFormat::Float => Ok(reader.samples::<f32>().collect::<std::result::Result<Vec<_>, _>>()?),
    }
}

fn main() -> Result<()> {
    let mut args: HashMap<String, String> = HashMap::new();
    let mut it = std::env::args().skip(1);
    while let Some(k) = it.next() {
        let v = it.next().ok_or_else(|| anyhow!("missing value for {}", k))?;
        args.insert(k.trim_start_matches("--").to_string(), v);
    }
    let get = |k: &str| args.get(k).cloned().ok_or_else(|| anyhow!("missing --{}", k));
    let model = get("model")?;
    let dir = PathBuf::from(get("dir")?);
    let list = get("list")?;
    let out = get("out")?;
    let lang = args.get("lang").cloned().unwrap_or_else(|| "sv".into());
    let beam: i32 = args.get("beam").map(|s| s.parse()).transpose()?.unwrap_or(2);
    let flash: bool = args.get("flash").map(|s| s == "1").unwrap_or(false);
    let temp: f32 = args.get("temp").map(|s| s.parse()).transpose()?.unwrap_or(0.2);
    // Decoding thresholds (app defaults: no_speech 0.55, logprob -1.0, entropy 2.4).
    let no_speech: f32 = args.get("no-speech-thold").map(|s| s.parse()).transpose()?.unwrap_or(0.55);
    let logprob: f32 = args.get("logprob-thold").map(|s| s.parse()).transpose()?.unwrap_or(-1.0);
    let entropy: f32 = args.get("entropy-thold").map(|s| s.parse()).transpose()?.unwrap_or(2.4);
    // App default is no_timestamps(true); --timestamps 1 lets whisper.cpp track where text ended in each 30 s window.
    let timestamps: bool = args.get("timestamps").map(|s| s == "1").unwrap_or(false);
    // Optional initial prompt (vocabulary / style hint), read from a UTF-8 file so quoting is not an issue.
    let prompt: Option<String> = match args.get("prompt-file") {
        Some(p) => Some(fs::read_to_string(p)?.trim().to_string()),
        None => None,
    };

    let names: Vec<String> = fs::read_to_string(&list)?
        .lines()
        .map(|l| l.trim().to_string())
        .filter(|l| !l.is_empty())
        .collect();
    if names.is_empty() {
        bail!("empty list");
    }

    // Same context parameters as the app: GPU on, device 0, flash attention configurable.
    let ctx_params = WhisperContextParameters {
        use_gpu: true,
        gpu_device: 0,
        flash_attn: flash,
        ..Default::default()
    };
    let t_load = Instant::now();
    let ctx = WhisperContext::new_with_params(&model, ctx_params)
        .map_err(|e| anyhow!("load model: {e}"))?;
    eprintln!("model loaded in {:.2}s (beam={}, flash={}, lang={}, temp={})", t_load.elapsed().as_secs_f64(), beam, flash, lang, temp);

    // --carry N: append the last N words of the previous chunk's output (same parent clip, split on "__") to the prompt.
    let carry: usize = args.get("carry").map(|s| s.parse()).transpose()?.unwrap_or(0);

    let transcribe = |audio: &[f32], tail: &str| -> Result<String> {
        let strategy = if beam <= 0 {
            SamplingStrategy::Greedy { best_of: 1 }
        } else {
            SamplingStrategy::BeamSearch { beam_size: beam, patience: 1.0 }
        };
        let mut params = FullParams::new(strategy);
        params.set_language(Some(&lang));
        params.set_translate(false);
        params.set_no_timestamps(!timestamps);
        params.set_token_timestamps(true);
        params.set_print_special(false);
        params.set_print_progress(false);
        params.set_print_realtime(false);
        params.set_print_timestamps(false);
        params.set_suppress_blank(true);
        params.set_suppress_nst(true);
        params.set_temperature(temp);
        params.set_max_initial_ts(1.0);
        params.set_entropy_thold(entropy);
        params.set_logprob_thold(logprob);
        params.set_no_speech_thold(no_speech);
        params.set_max_len(200);
        params.set_single_segment(false);
        let full_prompt: Option<String> = match (&prompt, tail.is_empty()) {
            (Some(p), true) => Some(p.clone()),
            (Some(p), false) => Some(format!("{} {}", p, tail)),
            (None, false) => Some(tail.to_string()),
            (None, true) => None,
        };
        if let Some(p) = &full_prompt {
            params.set_initial_prompt(p);
        }

        let mut state = ctx.create_state().map_err(|e| anyhow!("create_state: {e}"))?;
        state.full(params, audio).map_err(|e| anyhow!("full: {e}"))?;
        let mut text = String::new();
        for i in 0..state.full_n_segments() {
            if let Some(seg) = state.get_segment(i) {
                if let Ok(t) = seg.to_str_lossy() {
                    let t = t.trim();
                    if !t.is_empty() {
                        if !text.is_empty() {
                            text.push(' ');
                        }
                        text.push_str(t);
                    }
                }
            }
        }
        Ok(text)
    };

    // Warm-up (shader compilation, allocations) on the first clip, not timed.
    let warm = read_wav_16k_mono(&dir.join(&names[0]))?;
    let _ = transcribe(&warm, "")?;
    let mut prev_parent = String::new();
    let mut prev_tail = String::new();

    let mut tsv = String::new();
    let mut audio_total = 0.0f64;
    let mut compute_total = 0.0f64;
    for name in &names {
        let audio = read_wav_16k_mono(&dir.join(name))?;
        let secs_audio = audio.len() as f64 / 16000.0;
        let parent = name.split("__").next().unwrap_or(name).to_string();
        if parent != prev_parent {
            prev_parent = parent;
            prev_tail.clear();
        }
        let t = Instant::now();
        let text = transcribe(&audio, if carry > 0 { &prev_tail } else { "" })?;
        let secs = t.elapsed().as_secs_f64();
        if carry > 0 {
            let words: Vec<&str> = text.split_whitespace().collect();
            let start = words.len().saturating_sub(carry);
            prev_tail = words[start..].join(" ");
        }
        audio_total += secs_audio;
        compute_total += secs;
        tsv.push_str(&format!("{}\t{:.3}\t{}\n", name, secs, text.replace(['\t', '\n'], " ")));
    }
    fs::write(&out, tsv)?;
    println!(
        "RESULT beam={} flash={} clips={} audio={:.1}s compute={:.2}s rtf={:.4}",
        beam, flash, names.len(), audio_total, compute_total, compute_total / audio_total
    );
    Ok(())
}
