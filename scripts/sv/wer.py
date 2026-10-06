"""Word error rate for whisper-bench output.

Usage: python -I scripts/sv/wer.py <ref.tsv> <hyp.tsv> [<hyp2.tsv> ...]
ref.tsv: <name>\t<reference text>      hyp.tsv: <name>\t<seconds>\t<text>

Both sides are normalised like FLEURS' `transcription` column: lower-case, punctuation removed
(Swedish letters and digits kept), whitespace collapsed. Corpus WER = total edits / total reference words.
"""
import re
import sys


def norm(s: str) -> list[str]:
    s = s.lower()
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE).replace("_", " ")
    return s.split()


def edits(ref: list[str], hyp: list[str]) -> int:
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i] + [0] * len(hyp)
        for j, h in enumerate(hyp, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h))
        prev = cur
    return prev[-1]


def load_ref(path):
    out = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            name, _, text = line.rstrip("\n").partition("\t")
            out[name] = norm(text)
    return out


def main():
    ref = load_ref(sys.argv[1])
    for hyp_path in sys.argv[2:]:
        total_edits = total_words = 0
        secs = 0.0
        with open(hyp_path, encoding="utf-8") as f:
            for line in f:
                name, s, text = (line.rstrip("\n").split("\t") + ["", "", ""])[:3]
                if name not in ref:
                    continue
                r, h = ref[name], norm(text)
                total_edits += edits(r, h)
                total_words += len(r)
                secs += float(s)
        print(f"{hyp_path}: WER {100 * total_edits / total_words:.2f}%  ({total_edits}/{total_words} words)  compute {secs:.2f}s")


if __name__ == "__main__":
    main()
