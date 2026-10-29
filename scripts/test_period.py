"""Test period of the stage-early-warning archive v1.2: the numbers in Sections 1 and 5.4 of the article.

Usage: python3 scripts/test_period.py data/test_period.csv.gz [--kev known_exploited_vulnerabilities.json]

data/test_period.csv.gz holds the 76 754 candidates of the test period: CVE records first published
2025-01-01..2026-06-13 that were not in the KEV catalog at the forecast time t = publication + 7 days.
It is copied from stage-early-warning v1.2 (https://github.com/datch1588/stage-early-warning, release v1.2),
file scores/as_run/v120/out7_stages_test_scores_tau7.csv.gz, columns cve, d0, t, kev, y, O, any_poc
(the model scores are left out). Columns:
  cve      CVE identifier
  d0       publication date of the first version of the record
  t        forecast time, d0 + 7 days
  kev      date the CVE was added to KEV (catalog version 2026.10.13), empty if it is not there
  y        KEV-90 label: 1 if added to KEV in (t, t + 90 days]
  O        1 if the first published description reports exploitation (structured S3)
  any_poc  1 if a public PoC repository was created before t (structured S2)
Stage at t: S3 if O = 1, otherwise S2 if any_poc = 1, otherwise S1.

The script checks the dates, recomputes y from the KEV date and prints the counts. With --kev it also
compares the KEV dates with a KEV catalog file (field dateAdded); any later catalog version will do,
because every window (t, t + 90 days] closes before 2026-10-13.
Standard library only.
"""
import csv
import gzip
import json
import sys
from collections import Counter
from datetime import date, timedelta

args = [a for a in sys.argv[1:] if not a.startswith("--")]
kev_file = sys.argv[sys.argv.index("--kev") + 1] if "--kev" in sys.argv else None
if kev_file:
    args.remove(kev_file)
rows = list(csv.DictReader(gzip.open(args[0], "rt", encoding="utf-8")))

D = lambda s: date.fromisoformat(s[:10])
d0 = [D(r["d0"]) for r in rows]
bad_t = sum(D(r["t"]) != d + timedelta(days=7) for r, d in zip(rows, d0))
prior = bad_y = 0
for r in rows:
    t = D(r["t"])
    k = D(r["kev"]) if r["kev"] else None
    prior += k is not None and k <= t
    bad_y += int(k is not None and t < k <= t + timedelta(days=90)) != int(r["y"])
stage = ["S3" if r["O"] == "1" else "S2" if r["any_poc"] == "1" else "S1" for r in rows]
st = Counter(stage)
pos = Counter(s for s, r in zip(stage, rows) if r["y"] == "1")

print(f"candidates {len(rows)}; publication dates {min(d0)}..{max(d0)}; t = d0 + 7 days: mismatches {bad_t}")
print(f"in KEV already at t: {prior}")
print(f"KEV-90 (added to KEV in (t, t + 90 days]): {sum(r['y'] == '1' for r in rows)}; "
      f"label recomputed from the KEV date: mismatches {bad_y}")
print(f"stage at t: S1 {st['S1']}, S2 {st['S2']}, S3 {st['S3']}")
print(f"KEV-90 by stage: S1 {pos['S1']}, S2 {pos['S2']}, S3 {pos['S3']}")
print(f"below S3 at t (Section 5.4): {len(rows) - st['S3']}")

if kev_file:
    cat = json.load(open(kev_file, encoding="utf-8"))
    added = {v["cveID"].upper(): D(v["dateAdded"]) for v in cat["vulnerabilities"]}
    same = diff = later = missing = 0
    for r in rows:
        c = added.get(r["cve"].upper())
        if r["kev"]:
            if c is None:
                missing += 1
            elif c == D(r["kev"]):
                same += 1
            else:
                diff += 1
        elif c is not None:
            later += c > D(r["t"]) + timedelta(days=90)
            diff += c <= D(r["t"]) + timedelta(days=90)
    print(f"KEV catalog {cat.get('catalogVersion', '?')}: same date {same}, different date {diff}, "
          f"missing from the catalog {missing}, added after the window {later}")
