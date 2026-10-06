"""Write a human-readable review file of every difference between a hand-written facit and a whisper-bench run.

Usage: python -I scripts/sv/review-diff.py <ref.tsv> <hyp.tsv> <out.txt> [--content]
Each difference is shown with a few words of context on both sides so you can decide who is right
(listen to the clip) and fix facit.txt when the facit was wrong. Differences that look like plain
spelling/inflection (character edit distance <= 2) are tagged [stavning?].
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wer  # noqa: E402


def char_dist(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, y in enumerate(b, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y))
        prev = cur
    return prev[-1]


def ctx(words, pos, mark, width=5):
    lo, hi = max(0, pos - width), min(len(words), pos + width + 1)
    out = []
    for k in range(lo, hi):
        out.append(f"[{words[k]}]" if (k == pos and mark) else words[k])
    return " ".join(out)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    wer.MODE["content"] = "--content" in sys.argv
    ref = wer.load_ref(args[0], True)
    lines = [
        "GRANSKNING. Varje avvikelse mellan ditt facit och modellen, med några ord omkring.\n",
        "Lyssna på klippet och avgör vem som har rätt. Hade DU fel: rätta i facit.txt (inte här).\n",
        "[stavning?] = nästan samma ord, troligen stavning eller böjning.\n\n",
    ]
    n_total = 0
    with open(args[1], encoding="utf-8") as f:
        for line in f:
            name, _, text = (line.rstrip("\n").split("\t") + ["", "", ""])[:3]
            if name not in ref:
                continue
            r, h = ref[name], wer.norm(text, True)
            _, ops = wer.align(r, h)
            lines.append(f"=== {name}: {len(ops)} avvikelser ===\n")
            for k, (kind, rw, hw, i, j) in enumerate(ops, 1):
                n_total += 1
                tag = ""
                if kind == "sub" and char_dist(rw, hw) <= 2:
                    tag = "  [stavning?]"
                what = {"sub": f"facit '{rw}' / modell '{hw}'", "del": f"modellen saknar '{rw}'", "ins": f"modellen har extra '{hw}'"}[kind]
                lines.append(f"{k:>3}. {what}{tag}\n")
                lines.append(f"       facit : ...{ctx(r, i, kind != 'ins')}...\n")
                lines.append(f"       modell: ...{ctx(h, j, kind != 'del')}...\n")
            lines.append("\n")
    with open(args[2], "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"{n_total} differences written to {args[2]}")


if __name__ == "__main__":
    main()
