"""Cut meeting clips at the app's own live chunk boundaries, so offline experiments mimic the live pipeline.

Usage: python -I scripts/sv/live-chunks.py <transcripts.json> <manifest.tsv> <audio.mp4> <out_dir>
                                           [--ffmpeg <path>] [--af "<ffmpeg audio filter>"]
Writes <out_dir>/clip_NN__MMM.wav (16 kHz mono), <out_dir>/list.txt and <out_dir>/chunks.tsv (chunk -> clip).
Chunks are clipped to their clip window. Prints counts only, never text.
"""
import argparse
import json
import os
import subprocess
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("transcripts")
    ap.add_argument("manifest")
    ap.add_argument("audio")
    ap.add_argument("out_dir")
    ap.add_argument("--ffmpeg", default="ffmpeg")
    ap.add_argument("--af", default="")
    a = ap.parse_args()
    if os.path.isdir(a.out_dir) and os.listdir(a.out_dir):
        sys.exit("out_dir is not empty")
    os.makedirs(a.out_dir, exist_ok=True)

    tr = json.load(open(a.transcripts, encoding="utf-8"))
    items = sorted(next(v for v in tr.values() if isinstance(v, list)), key=lambda i: float(i["audio_start_time"]))
    clips = []
    with open(a.manifest, encoding="utf-8") as f:
        next(f)
        for line in f:
            name, s, e, _ = line.rstrip("\n").split("\t")
            clips.append((name, float(s), float(e)))

    names, rows = [], []
    for cname, cs, ce in clips:
        n = 0
        for it in items:
            s, e = float(it["audio_start_time"]), float(it["audio_end_time"])
            if not (cs <= (s + e) / 2 < ce):
                continue
            s, e = max(s, cs), min(e, ce)
            if e - s < 0.3:
                continue
            n += 1
            fn = f"{cname}__{n:03d}.wav"
            cmd = [a.ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{s:.3f}", "-t", f"{e - s:.3f}", "-i", a.audio, "-vn"]
            if a.af:
                cmd += ["-af", a.af]
            cmd += ["-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", os.path.join(a.out_dir, fn)]
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode != 0:
                sys.exit(f"ffmpeg failed: {r.stderr}")
            names.append(fn)
            rows.append(f"{fn}\t{cname}.wav")
        print(f"{cname}: {n} chunks")
    with open(os.path.join(a.out_dir, "list.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(names) + "\n")
    with open(os.path.join(a.out_dir, "chunks.tsv"), "w", encoding="utf-8") as f:
        f.write("\n".join(rows) + "\n")
    print(f"{len(names)} chunks written")


if __name__ == "__main__":
    main()
