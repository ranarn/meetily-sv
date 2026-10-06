"""Word error rate for whisper-bench output.

Usage: python -I scripts/sv/wer.py [--diff] [--drop-fillers] <ref.tsv> <hyp.tsv> [<hyp2.tsv> ...]
ref.tsv: <name>\t<reference text>      hyp.tsv: <name>\t<seconds>\t<text>

Both sides are normalised like FLEURS' `transcription` column: lower-case, punctuation removed
(Swedish letters and digits kept), whitespace collapsed. Corpus WER = total edits / total reference words.
--drop-fillers  remove hesitation sounds (eh, ehm, öh, mm, hm, äh, åh ...) from BOTH sides, because
                hand-written references usually omit them.
--diff          per clip, print the word-level differences (substitutions, deletions, insertions).
--content       "content WER": additionally drops discourse particles (liksom, ju, ja, nej, ...) and maps common
                spoken spellings (dom, dethär, ...) to the written form on both sides. Implies --drop-fillers.
"""
import re
import sys

FILLERS = {"eh", "ehh", "ehm", "ehmm", "öh", "öhm", "öhh", "mm", "mmm", "mhm", "hm", "hmm", "hmmm",
           "äh", "ähm", "ähh", "åh", "ååh", "aa", "ah", "ahh", "uh", "uhm", "um", "mja"}


# --content: discourse particles that carry no content, and common spoken spellings mapped to the written form.
# Reported next to the strict WER, never instead of it.
DISCOURSE = {"liksom", "ju", "ja", "jo", "nej", "nä", "alltså", "asså", "typ", "jaja", "okej", "ok", "precis"}
SPOKEN_FORMS = {"dom": ["de"], "dethär": ["det", "här"], "litegranna": ["lite", "granna"], "nåt": ["något"],
                "nån": ["någon"], "nåra": ["några"], "sånna": ["sådana"], "sånt": ["sådant"]}
MODE = {"fillers": False, "content": False}


def norm(s: str, drop_fillers: bool = False) -> list[str]:
    s = s.lower()
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE).replace("_", " ")
    words = s.split()
    if MODE["content"]:
        out = []
        for w in words:
            out.extend(SPOKEN_FORMS.get(w, [w]))
        words = [w for w in out if w not in DISCOURSE]
        drop_fillers = True
    return [w for w in words if w not in FILLERS] if drop_fillers else words


def align(ref: list[str], hyp: list[str]):
    """Levenshtein alignment: returns (edit count, list of ops (kind, ref_word, hyp_word))."""
    n, m = len(ref), len(hyp)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (ref[i - 1] != hyp[j - 1]))
    ops, i, j = [], n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and d[i][j] == d[i - 1][j - 1] + (ref[i - 1] != hyp[j - 1]):
            if ref[i - 1] != hyp[j - 1]:
                ops.append(("sub", ref[i - 1], hyp[j - 1], i - 1, j - 1))
            i, j = i - 1, j - 1
        elif i > 0 and d[i][j] == d[i - 1][j] + 1:
            ops.append(("del", ref[i - 1], "", i - 1, j))
            i -= 1
        else:
            ops.append(("ins", "", hyp[j - 1], i, j - 1))
            j -= 1
    return d[n][m], ops[::-1]


def load_ref(path, drop):
    out = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            name, _, text = line.rstrip("\n").partition("\t")
            out[name] = norm(text, drop)
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    show_diff = "--diff" in sys.argv
    drop = "--drop-fillers" in sys.argv
    MODE["content"] = "--content" in sys.argv
    ref = load_ref(args[0], drop)
    for hyp_path in args[1:]:
        total_edits = total_words = 0
        secs = 0.0
        with open(hyp_path, encoding="utf-8") as f:
            for line in f:
                name, s, text = (line.rstrip("\n").split("\t") + ["", "", ""])[:3]
                if name not in ref:
                    continue
                r, h = ref[name], norm(text, drop)
                e, ops = align(r, h)
                total_edits += e
                total_words += len(r)
                secs += float(s)
                if show_diff:
                    print(f"[{name}] {e} edits / {len(r)} words ({100 * e / max(1, len(r)):.1f}%)")
                    for kind, rw, hw, *_ in ops:
                        print({"sub": f"  ~ '{rw}' -> '{hw}'", "del": f"  - missing '{rw}'", "ins": f"  + extra '{hw}'"}[kind])
        print(f"{hyp_path}: WER {100 * total_edits / total_words:.2f}%  ({total_edits}/{total_words} words)  compute {secs:.2f}s")


if __name__ == "__main__":
    main()
