"""Merge per-chunk whisper-bench output back to one line per clip.

Usage: python -I scripts/sv/merge-chunks.py <hyp_chunks.tsv> <chunks.tsv> <out_hyp.tsv>
hyp_chunks.tsv: <chunk>\t<seconds>\t<text>; chunks.tsv: <chunk>\t<clip.wav>. Text is joined in chunk order.
"""
import sys


def main():
    owner = {}
    order = []
    with open(sys.argv[2], encoding="utf-8") as f:
        for line in f:
            if line.strip():
                chunk, clip = line.rstrip("\n").split("\t")
                owner[chunk] = clip
                if clip not in order:
                    order.append(clip)
    text = {c: [] for c in order}
    secs = {c: 0.0 for c in order}
    with open(sys.argv[1], encoding="utf-8") as f:
        for line in f:
            chunk, s, t = (line.rstrip("\n").split("\t") + ["", "", ""])[:3]
            if chunk in owner:
                text[owner[chunk]].append(t.strip())
                secs[owner[chunk]] += float(s)
    with open(sys.argv[3], "w", encoding="utf-8") as f:
        for c in order:
            f.write(f"{c}\t{secs[c]:.3f}\t{' '.join(x for x in text[c] if x)}\n")


if __name__ == "__main__":
    main()
