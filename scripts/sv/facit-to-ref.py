"""Turn a hand-written facit.txt (sections headed [clip_NN]) into ref.tsv and list.txt for whisper-bench.

Usage: python -I scripts/sv/facit-to-ref.py <facit.txt> <out_dir>
Writes <out_dir>/ref.tsv (<clip_NN.wav>\t<text>) and <out_dir>/list.txt (one wav name per line).
Clips with an empty text are skipped. Prints only clip names and word counts, never the text.
"""
import re
import sys


def main():
    src, out = sys.argv[1], sys.argv[2]
    text = open(src, encoding="utf-8").read()
    parts = re.split(r"^\[(clip_\d+)\][^\n]*\n", text, flags=re.M)
    # parts = [preamble, name1, body1, name2, body2, ...]
    refs = []
    for name, body in zip(parts[1::2], parts[2::2]):
        body = " ".join(body.split())
        words = len(body.split())
        print(f"{name}: {words} words" + ("" if words else "  (empty, skipped)"))
        if words:
            refs.append((name + ".wav", body))
    with open(f"{out}/ref.tsv", "w", encoding="utf-8") as f:
        for n, b in refs:
            f.write(f"{n}\t{b}\n")
    with open(f"{out}/list.txt", "w", encoding="utf-8") as f:
        for n, _ in refs:
            f.write(n + "\n")
    print(f"{len(refs)} clips with facit")


if __name__ == "__main__":
    main()
