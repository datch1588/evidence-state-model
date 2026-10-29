# Licence for data and expected outputs

The files in `data/` and `expected/` are licensed under the Creative Commons Attribution 4.0 International licence (CC BY 4.0): https://creativecommons.org/licenses/by/4.0/legalcode

Attribution: D. Lande, V. Kuzminskyi, "Code and data for the evidence-state model of vulnerability exploitation".

`data/ctinexus_candidates.csv` is derived from data of the cti-gate-experiment package, release v7.23 (labels `labels/e2e_labels.json` and the release asset `cti-gate-results-7.23.zip`) (https://github.com/datch1588/cti-gate-experiment, commit 7751fbe), by D. Lande and V. Kuzminskyi. Changes: only the columns needed for Section 6 of the article were kept, the report text was removed, and a flag for mentions containing a CVE identifier (`has_cve`) was added.

`data/test_period.csv.gz` is derived from the stage-early-warning archive, release v1.2 (https://github.com/datch1588/stage-early-warning), file `scores/as_run/v120/out7_stages_test_scores_tau7.csv.gz`, by V. Kuzminskyi and D. Lande, licensed under CC BY 4.0. Changes: the model score columns were removed; the KEV dates come from the CISA KEV catalog, version 2026.10.13.

Mention pairs in `data/ctinexus_candidates.csv` and the file names in `expected/duplicates.txt` refer to the annotated reports of CTINexus (Y. Cheng et al., IEEE EuroS&P 2025; https://github.com/peng-gao-lab/CTINexus, commit 0c688536d85eae72f6055723492b573b0a1ff865), whose repository is released under the MIT License. CVE identifiers and first-publication dates in `data/test_period.csv.gz` come from the CVE List of the CVE Program (https://github.com/CVEProject/cvelistV5) and are subject to the CVE Program Terms of Use (https://www.cve.org/Legal/TermsOfUse). KEV dates come from the CISA Known Exploited Vulnerabilities catalog, released under CC0 (https://github.com/cisagov/kev-data).

The code in `scripts/` is licensed under the MIT licence (`LICENSE`). CTINexus texts and annotations are not included and remain under the terms of the CTINexus repository. Full CVE records and the KEV catalog are not included either: `scripts/vulnrichment_history.py` downloads them from their sources, `expected/vulnrichment_history.txt` holds only counts, and `data/test_period.csv.gz` holds only CVE identifiers, dates and flags.
