// Offline Whisper benchmark: same whisper-rs calls and parameters as the app
// (frontend/src-tauri/src/whisper_engine/whisper_engine.rs, transcribe_audio_with_confidence),
// but with beam size and flash attention controllable from the command line.
//
// Usage:
//   whisper-bench --model <ggml.bin> --dir <wav dir> --list <names.txt> --out <hyp.tsv>
//                 [--lang sv] [--beam 2] [--flash 0|1] [--temp 0.2]
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

    let transcribe = |audio: &[f32]| -> Result<String> {
        let strategy = if beam <= 0 {
            SamplingStrategy::Greedy { best_of: 1 }
        } else {
            SamplingStrategy::BeamSearch { beam_size: beam, patience: 1.0 }
        };
        let mut params = FullParams::new(strategy);
        params.set_language(Some(&lang));
        params.set_translate(false);
        params.set_no_timestamps(true);
        params.set_token_timestamps(true);
        params.set_print_special(false);
        params.set_print_progress(false);
        params.set_print_realtime(false);
        params.set_print_timestamps(false);
        params.set_suppress_blank(true);
        params.set_suppress_nst(true);
        params.set_temperature(temp);
        params.set_max_initial_ts(1.0);
        params.set_entropy_thold(2.4);
        params.set_logprob_thold(-1.0);
        params.set_no_speech_thold(0.55);
        params.set_max_len(200);
        params.set_single_segment(false);

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
    let _ = transcribe(&warm)?;

    let mut tsv = String::new();
    let mut audio_total = 0.0f64;
    let mut compute_total = 0.0f64;
    for name in &names {
        let audio = read_wav_16k_mono(&dir.join(name))?;
        let secs_audio = audio.len() as f64 / 16000.0;
        let t = Instant::now();
        let text = transcribe(&audio)?;
        let secs = t.elapsed().as_secs_f64();
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
