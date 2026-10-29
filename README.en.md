# Evidence state model of vulnerability exploitation: code and data

Materials for the article by D. Lande and V. Kuzminskyi, "Evidence state model for vulnerability exploitation and bounds on false stage elevation" (manuscript, in Ukrainian, 2026). Repository version 2.1.0, 29 October 2026: https://github.com/datch1588/evidence-state-model (release v2.1.0). Ukrainian: [README.md](README.md).

The evidence state model determines the exploitation stage of a vulnerability: only a description (S1), a public proof-of-concept exploit (S2) or a report of exploitation (S3). The stage is determined only by accepted actual affirmative claims from open texts that were available to the system before the forecast time, and confirmations are counted by provenance groups. The article proves that this stage has no leakage from the future, does not decrease over time, is invariant to copies and modally correct, and obtains a sharp bound on the ratio of the expected numbers of vulnerabilities falsely and correctly elevated to S3. Data: historical SSVC records from CISA Vulnrichment, the test period of the stage-early-warning archive and 134 CTINexus reports.

This repository holds the code and data behind the numbers in Sections 1, 5.2–5.4 and 6 and the numerical checks of the theorems in Section 5. Every piece of data needed to check these numbers is either here or in the public sources named below.

## Contents

| Path | Article section | What it holds |
|---|---|---|
| `scripts/vulnrichment_history.py` | 6, first experiment | SSVC Exploitation from CISA Vulnrichment at forecast time vs now. Standard library only. |
| `scripts/test_period.py` | 1, 5.4 | Test period of the stage-early-warning archive v1.2: 76,754 candidates, 92 of them added to KEV within 90 days after the forecast time, 40 with structured stage S3 at the forecast time. Standard library only. |
| `scripts/sensitivity_6_2.py` | 5.4 | Numerical scenarios from Theorem 3 and the exact binomial formula. Standard library only. |
| `scripts/ctinexus_exploits.py` | 5.2, 6, CTINexus | 300 random splits of CTINexus reports (seed 7), threshold selection with the procedure from the proof of Theorem 1(b) with the per-text share of false accepted pairs as the loss, errors among accepted pairs typed "exploits", and the mean number of accepted pairs per test text. |
| `scripts/check_duplicates.py` | 6, CTINexus | Near-duplicate CTINexus reports by shared word 8-grams. |
| `scripts/make_inputs.py` | 6, CTINexus | Rebuilds `data/ctinexus_candidates.csv` from the raw files. |
| `scripts/theorem_checks.py` | 5 | Numerical checks of Theorems 1–3, Remark 2, Corollary 1, Lemma 1, Properties 1, 2, 4 and 5 and the numbers of Sections 5.2–5.4 on synthetic data. Not described in the article. Comments and output are in Ukrainian and use the numbering of an earlier draft of the manuscript (T4 = Remark 2 and Corollary 1; P1–P4 = Properties 1, 2, 4 and 5; Tables 3–4, Example 2 and App. A = the numbers in Sections 5.3–5.4 and the proofs of Theorems 1(b) and 2; L in the line "T2 А.2" = the number of vulnerabilities n_V in the proof of Theorem 2). |
| `data/test_period.csv.gz` | 1, 5.4 | The 76,754 candidates of the test period: publication and forecast dates, KEV date added, KEV-90 label, S2 and S3 flags. |
| `data/ctinexus_candidates.csv` | 5.2, 6, CTINexus | 16,072 mention pairs from reports 15–148. No report text. |
| `expected/` | — | Expected output of every script. |

Not included:

- **CTINexus texts and annotations**: `check_duplicates.py` reads them from a clone of the CTINexus repository (see "Data sources");
- **full CVE records and the KEV catalog**: `vulnrichment_history.py` downloads them from their sources, and `expected/vulnrichment_history.txt` holds only counts;
- **model scores of the stage-early-warning archive**: `data/test_period.csv.gz` holds only CVE identifiers, dates and flags.

## Reproducing the article

Python 3, NumPy and SciPy (SciPy only for `theorem_checks.py`). Tested with Python 3.13, NumPy 2.5.3 and SciPy 1.18.1.

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

| What | Command | Compare with |
|---|---|---|
| 6, Vulnrichment | `python3 scripts/vulnrichment_history.py fetch vr_data`, then `python3 scripts/vulnrichment_history.py check vr_data > out_vr.txt` | `expected/vulnrichment_history.txt` |
| 1, 5.4, test period | `python3 scripts/test_period.py data/test_period.csv.gz > out_tp.txt` | `expected/test_period.txt` |
| 5.4 | `python3 scripts/sensitivity_6_2.py > out_62.txt` | `expected/sensitivity_6_2.txt` |
| 5.2, 6, CTINexus, all pairs | `.venv/bin/python scripts/ctinexus_exploits.py data/ctinexus_candidates.csv > out.txt` | `expected/ctinexus_exploits.txt` |
| 6, CTINexus, duplicates removed | same call with second argument `108` or `108,130` | `expected/ctinexus_exploits_drop108.txt`, `expected/ctinexus_exploits_drop108_130.txt` |
| 6, CTINexus, pairs with / without CVE | same call with `--cve` or `--no-cve` | `expected/ctinexus_exploits_cve.txt`, `expected/ctinexus_exploits_no_cve.txt` |
| theorems | `.venv/bin/python scripts/theorem_checks.py --out results.json > out_theorems.txt` (a few minutes) | `expected/theorem_checks.txt` |

Monte Carlo numbers in `theorem_checks.py` depend on the NumPy random generator; with another NumPy version they may differ slightly, but the last line ("Усе гаразд: True", all checks passed) should not change.

### Section 6: Vulnrichment check

`fetch` downloads about 300 small JSON files: the KEV catalog version 2026.10.15 (https://github.com/cisagov/kev-data, commit `7923b5f7040256ca9887d268b4c2a02453a2ff30`), current CVE records (https://github.com/CVEProject/cvelistV5, commit `728adf1c`, 15.10.2026), and the records at forecast time t from the hourly release tags `cve_YYYY-MM-DD_HH00Z` of the same repository: the latest tag strictly earlier than t. For 3 of the 35 events no release was made in that hour, so the previous hour is used (see `tags_used.json`). An event is a vulnerability published 01.01–13.06.2026 that entered KEV within (t, t + 90 days], t = publication + 7 days. Exploitation is read from the SSVC block of the CISA-ADP container. `check --list` prints one row per event.

For one of the 35 events t falls exactly on the hour; that hour's tag is not earlier than t, so the previous hour's tag is used (the value is `none` at both tags).

### Sections 1 and 5.4: test period

`data/test_period.csv.gz` holds the 76,754 candidates of the test period of the stage-early-warning archive, version 1.2 (https://github.com/datch1588/stage-early-warning, release v1.2): CVE records first published 2025-01-01..2026-06-13 that were not in the KEV catalog at the forecast time t = d0 + 7 days. It is copied from the archive file `scores/as_run/v120/out7_stages_test_scores_tau7.csv.gz` without the model score columns, so checking the article numbers does not need the archive itself.

Columns: `cve`; `d0`, publication date of the first version of the record; `t`, forecast time; `kev`, date added to KEV in catalog version 2026.10.13 (empty if never); `y`, 1 if added within (t, t + 90 days]; `O`, 1 if the first published description reports exploitation (structured S3); `any_poc`, 1 if a public PoC repository was created before t (S2). Stage at t: S3 if `O` = 1, else S2 if `any_poc` = 1, else S1.

`test_period.py` checks that t = d0 + 7 days and that no candidate was in KEV by t, recomputes `y` from the KEV date and prints the counts: 76,754 candidates, 92 KEV additions (Section 1), stages S1 75,384, S2 1,330, S3 40, so 76,714 vulnerabilities below S3 (Section 5.4). With `--kev <known_exploited_vulnerabilities.json>` it also compares the dates with a KEV catalog; any later version will do, because every window (t, t + 90 days] closes before 2026-10-13. With catalog version 2026.10.13 all 136 dates match.

How the flags `O` and `any_poc` were obtained is described in the README of the stage-early-warning archive and in its protocol `as_run/protocols/PROTOCOL_7_pre.md`.

### Section 6, CTINexus: reading the output

For each α there are four lines. `per-repeat` gives the spread across repeats (10th and 90th percentiles); repeats reuse the same 134 texts, so this is not a confidence interval. `SUMS` gives the sums over repeats from which the shares are computed. The third line gives the shares reported in the article. The fourth gives the mean number of accepted pairs per test text, over texts with at least one accepted pair and over all test texts. The largest number of accepted claims in a text, n_max, is at least this mean, so at α = 0.2 (mean 15.98) n_max ≥ 16 and the bound of Theorem 1(a) equals one (Section 5.2).

A pair typed "exploits" counts as wrong if, by the labels, there is no relation or its type is not exploits. The labels do not check modality, polarity or the link to a specific CVE, so these are error rates among pairs, not the rate of false stage elevation of vulnerabilities.

With `--cve` or `--no-cve` the threshold is chosen and certified on all pairs exactly as without the flag; only accepted pairs typed exploits with or without a CVE identifier are counted. `has_cve` is 1 if either mention of the pair contains an identifier of the form `CVE-YYYY-NNNN`; 140 of the 522 pairs typed exploits have one.

## Data sources

`data/ctinexus_candidates.csv` is a derived file, rebuilt byte for byte by `scripts/make_inputs.py` from the cti-gate-experiment v7.23 package and its release asset `cti-gate-results-7.23.zip` (https://github.com/datch1588/cti-gate-experiment, release v7.23, commit 7751fbe); file hashes are listed in `README.md`. Columns: `id`, `report`, `p_yes` (LLM relation probability, Ministral 3 8B), `llm_type_exp`, `related` and `related_exp` (from the machine labels in `labels/e2e_labels.json`), `has_cve`.

`scripts/check_duplicates.py` needs the CTINexus repository (https://github.com/peng-gao-lab/CTINexus, commit `0c688536d85eae72f6055723492b573b0a1ff865`); report number = 0-based position of the file in the sorted list of `ctinexus/data/annotation/*.json`. Compare the output with `expected/duplicates.txt`, which lists the numbers and CTINexus file names of report pairs sharing 8-grams.

## Checksums

`SHA256SUMS` lists the SHA-256 hashes of the data, expected outputs and scripts. Check with `sha256sum -c SHA256SUMS` (Linux) or `shasum -a 256 -c SHA256SUMS` (macOS).

## Licence

Code in `scripts/`: MIT (`LICENSE`). Data in `data/` and expected outputs in `expected/`: CC BY 4.0 (`LICENSE-DATA.md`), with attribution to cti-gate-experiment release v7.23 and stage-early-warning release v1.2, from which they are derived. Third-party data keep their own terms: CVE identifiers and first-publication dates in `data/test_period.csv.gz` are subject to the CVE Program Terms of Use (https://www.cve.org/Legal/TermsOfUse), KEV dates come from the CISA KEV catalog, released under CC0 (https://github.com/cisagov/kev-data), and the CTINexus repository (Y. Cheng et al., IEEE EuroS&P 2025) is MIT-licensed. Details: `LICENSE-DATA.md`.

## How to cite

See `CITATION.cff` (the "Cite this repository" button on the repository page).
