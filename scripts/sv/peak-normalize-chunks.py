"""Peak-normalise every wav in a directory with ONE static gain per file (what a simple per-chunk step in the app would do).

Usage: python -I scripts/sv/peak-normalize-chunks.py <in_dir> <out_dir> [--ffmpeg <path>] [--target-db -1] [--max-gain-db 20]
gain_db = min(max_gain_db, target_db - max_volume_db). list.txt and chunks.tsv are copied if present. Prints only counts/gain stats.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("in_dir")
    ap.add_argument("out_dir")
    ap.add_argument("--ffmpeg", default="ffmpeg")
    ap.add_argument("--target-db", type=float, default=-1.0)
    ap.add_argument("--max-gain-db", type=float, default=20.0)
    a = ap.parse_args()
    if os.path.isdir(a.out_dir) and os.listdir(a.out_dir):
        sys.exit("out_dir is not empty")
    os.makedirs(a.out_dir, exist_ok=True)
    gains = []
    for fn in sorted(os.listdir(a.in_dir)):
        src = os.path.join(a.in_dir, fn)
        if not fn.endswith(".wav"):
            if fn in ("list.txt", "chunks.tsv"):
                shutil.copy(src, os.path.join(a.out_dir, fn))
            continue
        err = subprocess.run([a.ffmpeg, "-hide_banner", "-i", src, "-af", "volumedetect", "-vn", "-f", "null", "-"],
                             capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
        m = re.search(r"max_volume: (-?[\d.]+) dB", err)
        mx = float(m.group(1)) if m else a.target_db
        g = max(0.0, min(a.max_gain_db, a.target_db - mx))
        r = subprocess.run([a.ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", src, "-af", f"volume={g:.2f}dB,alimiter=limit=0.99",
                            "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", os.path.join(a.out_dir, fn)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"ffmpeg failed for {fn}: {r.stderr}")
        gains.append(g)
    gains.sort()
    print(f"{len(gains)} files; gain dB: min {gains[0]:.1f}, median {gains[len(gains) // 2]:.1f}, max {gains[-1]:.1f}")


if __name__ == "__main__":
    main()
