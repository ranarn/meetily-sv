"""Cut a speech-dense window of a meeting recording into ~45 s clips at pauses, for manual transcription.

Usage: python -I scripts/sv/split-meeting.py <audio.mp4> <out_dir> [--ffmpeg <path>] [--minutes 4]

Only audio LEVELS are analysed (volumedetect/silencedetect); the speech itself is never decoded to text.
Outputs in <out_dir> (must be empty or missing):
  clip_01.wav ...   16 kHz mono PCM, one per clip
  facit.txt         template: a [clip_NN] header per clip; write what is said under each header
  manifest.tsv      clip, start_s, end_s, duration_s (positions in the original recording)
"""
import argparse
import os
import re
import subprocess
import sys


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def duration(ffmpeg, src):
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", run([ffmpeg, "-hide_banner", "-i", src]).stderr)
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)


def mean_volume(ffmpeg, src):
    err = run([ffmpeg, "-hide_banner", "-i", src, "-af", "volumedetect", "-vn", "-f", "null", "-"]).stderr
    return float(re.search(r"mean_volume: (-?[\d.]+) dB", err).group(1))


def silences(ffmpeg, src, noise_db, min_dur):
    err = run([ffmpeg, "-hide_banner", "-i", src, "-af", f"silencedetect=noise={noise_db}dB:d={min_dur}", "-vn", "-f", "null", "-"]).stderr
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end: (-?[\d.]+)", err)]
    return list(zip(starts, ends[: len(starts)]))


def speech_seconds(sil, a, b):
    """Seconds of non-silence inside [a, b)."""
    quiet = sum(max(0.0, min(e, b) - max(s, a)) for s, e in sil)
    return (b - a) - quiet


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out_dir")
    ap.add_argument("--ffmpeg", default="ffmpeg")
    ap.add_argument("--minutes", type=float, default=4.0)
    a = ap.parse_args()

    if os.path.isdir(a.out_dir) and os.listdir(a.out_dir):
        sys.exit("out_dir is not empty")
    os.makedirs(a.out_dir, exist_ok=True)

    total = duration(a.ffmpeg, a.src)
    mean = mean_volume(a.ffmpeg, a.src)
    noise = round(mean - 12)
    sil = silences(a.ffmpeg, a.src, noise, 0.5)
    print(f"duration {total:.1f}s, mean volume {mean} dB, silence threshold {noise} dB, {len(sil)} pauses")

    # Window with the most speech; skip the first 2 min and last 1 min (setup/teardown chatter).
    win = a.minutes * 60
    best = None
    t = 120.0
    while t + win <= total - 60:
        sp = speech_seconds(sil, t, t + win)
        if best is None or sp > best[1]:
            best = (t, sp)
        t += 5.0
    if best is None:
        sys.exit("recording too short for the requested window")
    w0, sp = best
    w1 = w0 + win
    print(f"window {w0:.0f}s-{w1:.0f}s, speech {100 * sp / win:.0f}% of window")

    # Cut points at pause midpoints, aiming for ~45 s clips (30-60 s allowed).
    mids = [(s + e) / 2 for s, e in sil if w0 < (s + e) / 2 < w1]
    cuts, cur = [w0], w0
    while w1 - cur > 60:
        cands = [m for m in mids if cur + 30 <= m <= cur + 60]
        nxt = min(cands, key=lambda m: abs(m - (cur + 45))) if cands else cur + 45
        cuts.append(nxt)
        cur = nxt
    cuts.append(w1)

    manifest, facit = [], []
    for i, (s, e) in enumerate(zip(cuts, cuts[1:]), 1):
        name = f"clip_{i:02d}"
        out = os.path.join(a.out_dir, name + ".wav")
        r = run([a.ffmpeg, "-hide_banner", "-loglevel", "error", "-ss", f"{s:.3f}", "-t", f"{e - s:.3f}",
                 "-i", a.src, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", out])
        if r.returncode != 0:
            sys.exit(f"ffmpeg failed for {name}: {r.stderr}")
        manifest.append(f"{name}\t{s:.1f}\t{e:.1f}\t{e - s:.1f}")
        facit.append(f"[{name}]  ({e - s:.0f} s)\n\n")

    with open(os.path.join(a.out_dir, "manifest.tsv"), "w", encoding="utf-8") as f:
        f.write("clip\tstart_s\tend_s\tduration_s\n" + "\n".join(manifest) + "\n")
    header = (
        "FACIT. Lyssna på varje clip_NN.wav och skriv under rubriken exakt vad som sägs.\n"
        "- Skriv som det sägs (även 'ehm' kan utelämnas); stavning och namn som de ska vara.\n"
        "- Skiljetecken och versaler spelar ingen roll, orden gör det.\n"
        "- Osäker på ett ord: skriv ditt bästa gissning, eller [?].\n"
        "- Rör inte rubrikerna i hakparenteser.\n\n"
    )
    with open(os.path.join(a.out_dir, "facit.txt"), "w", encoding="utf-8") as f:
        f.write(header + "".join(facit))
    print(f"{len(manifest)} clips written to {a.out_dir}")
    for line in manifest:
        print("  " + line.replace("\t", "  "))


if __name__ == "__main__":
    main()
