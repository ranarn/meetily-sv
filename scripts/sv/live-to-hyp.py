"""Build a whisper-bench-style hyp.tsv from the app's own live transcript (transcripts.json).

Usage: python -I scripts/sv/live-to-hyp.py <transcripts.json> <manifest.tsv> <out_hyp.tsv>
manifest.tsv (from split-meeting.py): clip, start_s, end_s, duration_s  (positions in the original recording).
Each live chunk is assigned to the clip whose window contains the chunk's midpoint
(audio_start_time / audio_end_time). Prints counts only, never the text.
"""
import json
import sys


def main():
    tr = json.load(open(sys.argv[1], encoding="utf-8"))
    items = next(v for v in tr.values() if isinstance(v, list))
    clips = []
    with open(sys.argv[2], encoding="utf-8") as f:
        next(f)
        for line in f:
            name, s, e, _ = line.rstrip("\n").split("\t")
            clips.append((name, float(s), float(e)))
    buckets = {c[0]: [] for c in clips}
    for it in sorted(items, key=lambda i: float(i["audio_start_time"])):
        mid = (float(it["audio_start_time"]) + float(it["audio_end_time"])) / 2
        for name, s, e in clips:
            if s <= mid < e:
                buckets[name].append(it["text"].strip())
                break
    with open(sys.argv[3], "w", encoding="utf-8") as f:
        for name, _, _ in clips:
            text = " ".join(buckets[name]).replace("\t", " ").replace("\n", " ")
            f.write(f"{name}.wav\t0.0\t{text}\n")
            print(f"{name}: {len(buckets[name])} live chunks, {len(text.split())} words")


if __name__ == "__main__":
    main()
