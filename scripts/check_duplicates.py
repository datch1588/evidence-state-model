"""Find repeated texts among CTINexus reports 15-148 by shared word 8-grams.

Usage: python3 scripts/check_duplicates.py <CTINexus repo>/ctinexus/data/annotation
Report number = position of the file in the sorted list of *.json files (0-based), as in the candidate ids.
"""
import itertools, json, os, re, sys

D = sys.argv[1]
fs = sorted(f for f in os.listdir(D) if f.endswith(".json"))
T = [json.load(open(os.path.join(D, f), encoding="utf-8"))["text"] for f in fs]


def grams(t, n=8):
    w = re.findall(r"\w+", t.lower())
    return {tuple(w[i:i + n]) for i in range(len(w) - n + 1)}


G = {r: grams(T[r]) for r in range(15, 149)}
pairs = []
for a, b in itertools.combinations(range(15, 149), 2):
    if G[a] and G[b]:
        inter = len(G[a] & G[b])
        if inter:
            pairs.append((inter / min(len(G[a]), len(G[b])), a, b))
pairs.sort(reverse=True)
print("files", len(fs), "pairs sharing an 8-gram", len(pairs))
for share, a, b in pairs:
    print(f"{share:.3f}  {a} {fs[a]}  |  {b} {fs[b]}  identical={T[a] == T[b]}")
