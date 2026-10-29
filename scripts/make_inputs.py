"""Build data/ctinexus_candidates.csv from the raw files of the cti-gate-experiment v7.23 run.

Usage: python3 scripts/make_inputs.py <cti-gate-experiment 7.23 dir> <dir containing results/e2e_full> data/ctinexus_candidates.csv

The CSV holds no report text: only candidate id, report number, the LLM relation probability,
the LLM relation type flag, the two labels used by ctinexus_exploits.py and has_cve:
1 if either mention of the pair contains a CVE identifier (CVE-YYYY-NNNN...).
"""
import csv, json, re, sys

CVE = re.compile(r"CVE-\d{4}-\d{4,}", re.I)

pkg, run, out = sys.argv[1], sys.argv[2], sys.argv[3]
E2E = f"{run}/results/e2e_full"
lab = json.load(open(f"{pkg}/labels/e2e_labels.json", encoding="utf-8"))
ty = {}
for l in open(f"{E2E}/type_mlx-community_Ministral-3-8B-Instruct-2512-4bit_t2w.jsonl", encoding="utf-8"):
    d = json.loads(l); ty[d["id"]] = d["top"]
py = {}
for l in open(f"{E2E}/tier2_mlx-community_Ministral-3-8B-Instruct-2512-4bit_p3.jsonl", encoding="utf-8"):
    d = json.loads(l); py[d["id"]] = d.get("p_yes")
rows = []
for l in open(f"{E2E}/candidates.jsonl", encoding="utf-8"):
    c = json.loads(l); r = int(c["report"])
    if r < 15 or c["id"] not in lab:
        continue
    L = lab[c["id"]]
    rows.append({
        "id": c["id"],
        "report": r,
        "p_yes": repr(float(py.get(c["id"]) or 0)),
        "llm_type_exp": int(ty.get(c["id"]) == "EXP"),
        "related": int(L["y"] == 1),
        "related_exp": int(L["y"] == 1 and L.get("type") == "EXP"),
        "has_cve": int(bool(CVE.search(c.get("name_first") or "") or CVE.search(c.get("name_second") or ""))),
    })
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader(); w.writerows(rows)
print("rows", len(rows))
