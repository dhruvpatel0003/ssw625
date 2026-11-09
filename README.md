# SpecMine Empirical Study — Reproduction Guide (Phase 1–3)

> **Reproduction status:** This README documents the team's intended execution workflow. Commands and output filenames must be checked against the submitted scripts and actual generated files. There is **no verified one-command runner**: run each script separately. Items labeled **pending verification** must not be represented as completed experiments.

## 1. Study scope and research questions

**Study title:** *Do Complete and Verifiable Software Specifications Lead to Smoother Spec-to-Code Implementation? An Empirical Study Using SpecMine*

This observational study examines 14 automatically extracted specification-content indicators and their association with pull-request (PR) code co-change. The title asks a broader question than the available measurements: whether code changes occur, and how many code files are changed, **do not directly measure implementation smoothness, quality, productivity, or causation**.

- **RQ1:** How frequently do completeness, verifiability, and unresolved-information signals occur in distinct matched specifications?
- **RQ2:** How are those signals associated with whether matched PRs change code and with the number of code files changed?

**Units of analysis:** RQ1 deduplicates by matched specification identifier; RQ2 groups by `(tool, repo_name, pr_number)` and marks a signal present if **any** matched specification for that PR contains it.

## 2. Dataset and provenance

Download the SpecMine dataset from the team's recorded Zenodo source: <https://zenodo.org/records/22102780>. Confirm the precise dataset version, record, licensing, and checksums against the actual files before final submission. Store the following **five** files under `data/` with these exact names:

| File | Purpose | Previously observed rows (verify locally) |
|---|---|---:|
| `spec_files.parquet` | Specification records and file identifiers | 470,795 |
| `spec_content_features.parquet` | Extracted content features | 468,307 |
| `spec_file_commits.parquet` | Recorded specification commit history | 780,335 |
| `pull_requests.parquet` | PR metadata and outcomes | 5,992 |
| `pr_files.parquet` | PR-file records | 348,141 |

Do not commit large datasets or private credentials unless redistribution is permitted. Historical content retrieval uses GitHub and is optional for the **core** RQ1/RQ2 analysis.

## 3. Repository layout

```text
ssw625-SpecMine-Study/
├── README.md
├── requirements.txt                 # Create and verify pinned dependencies
├── data/                            # Five input Parquet files (local)
├── scripts/
│   ├── 01_inspect_dataset.py
│   ├── 02_match_spec_pr.py
│   ├── 03_timing_audit.py
│   ├── 04_rq1_analysis.py
│   ├── 05_rq2_analysis.py
│   ├── 06_validate_results.py
│   ├── 07_generate_figures.py
│   ├── 08_historical_version_audit.py
│   ├── 09_retrieve_historical_specs.py
│   ├── 10_historical_features.py
│   ├── 11_statistical_robustness.py
│   ├── 12_prepare_manual_audit.py       # Phase 3; verify filename
│   ├── 13_analyze_manual_audit.py       # Phase 3; verify filename
│   ├── 14_timing_sensitivity.py
│   ├── 15_matching_coverage.py          # Phase 3; verify presence
│   └── 16_interpretation_review.py      # Phase 3; verify presence
└── results/
    ├── tables/                    # Core analysis and audit outputs
    ├── figures/                   # Generated plots
    ├── manual_audit/              # Manual-review worksheet and analysis
    └── phase3/                    # Sensitivity and interpretation outputs
```

The structure lists expected artifacts, **not a verified inventory**. Some Phase 3 scripts were prepared separately; ensure they are actually included before publishing this layout.

## 4. Environment setup (Windows PowerShell)

From the project root:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install pandas numpy pyarrow matplotlib requests
```

These are the packages identified in the existing workflow; additional imports may require packages not listed here. Create a tested, pinned `requirements.txt` for a reproducible release. To capture your environment for review:

```powershell
python -m pip freeze > environment_snapshot.txt
python -m compileall -q scripts
```

If activation is blocked, invoke `.venv\Scripts\python.exe` instead of `python`. Never commit `.env`, `GITHUB_TOKEN`, or secrets.

## 5. Run scripts individually — core study

Run from the **project root**, in order; later scripts may depend on earlier output files. No `run_all.py` or `run_pipeline.py` is provided.

```powershell
python scripts/01_inspect_dataset.py
python scripts/02_match_spec_pr.py
python scripts/03_timing_audit.py
python scripts/04_rq1_analysis.py
python scripts/05_rq2_analysis.py
python scripts/06_validate_results.py
python scripts/07_generate_figures.py
```

Expected core artifacts (confirm actual filenames against the code):

| Artifact | Purpose |
|---|---|
| `results/tables/dataset_schema.txt` | Input schema inspection |
| `results/tables/spec_pr_match_audit.csv` | Matching counts and exclusions |
| `results/tables/spec_pr_analysis_sample.csv` | Matched spec–PR records |
| `results/tables/spec_pr_timing_audit.csv` | File-level and historical timing audit |
| `results/tables/timing_summary.csv` | Timing classification counts |
| `results/tables/rq1_signal_frequencies.csv` | RQ1 signal frequencies |
| `results/tables/rq2_associations.csv` | RQ2 signal comparisons |
| `results/tables/rq2_pr_level_data.csv` | One row per matched PR; input to Phase 3 sensitivity |
| `results/figures/` | Plots; inspect actual names |

**Previously recorded matching audit:** 30,107 PR specification-file entries; 22,756 matched; 7,351 unmatched; 16,150 distinct matched specs; 5,725 distinct matched PRs. These figures come from prior runs and must be reproduced and checked. An additional ambiguous-mapping census was recorded; distinguish its counting unit from PR spec-file entries rather than adding the numbers together.

## 6. Signals and outcome definitions

| Category | Signal columns |
|---|---|
| Completeness | `has_requirements`, `has_purpose`, `has_dependencies`, `has_non_goals`, `has_out_of_scope`, `has_edge_cases` |
| Verifiability | `has_acceptance_criteria`, `has_success_criteria`, `has_gherkin`, `n_scenario_blocks` |
| Unresolved information | `n_todo`, `has_open_questions`, `n_needs_clarification`, `has_unfilled_placeholder` |

For `has_*` columns, presence is a positive flag; for `n_*` columns, presence means count > 0. Validate missing-value treatment in the scripts before interpreting counts.

- `touches_code` / `code_changed`: binary code-change outcome.
- `n_code_outside` / `code_file_count`: number of code files outside the specification directory in the implemented RQ2 analysis.
- `n_code_files`: a separate dataset field; **do not substitute** it for `n_code_outside` in reporting.
- PR additions/deletions are descriptive PR metrics, not proof of specification quality.

## 7. Historical and robustness analyses (Scripts 08–11)

```powershell
python scripts/08_historical_version_audit.py
python scripts/09_retrieve_historical_specs.py
python scripts/10_historical_features.py
python scripts/11_statistical_robustness.py
```

- Script 09 retrieves a **pilot sample** of historical GitHub file versions (earlier configuration: `MAX_RECORDS = 50`); it does **not** reconstruct the complete dataset. Internet access and GitHub availability/rate limits can affect results. Where supported by the script, provide `GITHUB_TOKEN` as an environment variable.
- Script 10 uses exploratory historical feature rules; they are **not validated as equivalent** to SpecMine's original feature extractor. Differences are not automatically detector errors.
- Script 11's bootstrap count was originally 100; a later suggested configuration was 200. **Check the actual `N_BOOTSTRAP`, random seed, and resampling unit in the submitted source and record the configuration used for each output.** A larger repetition count alone does not make resampling repository-aware.
- Previously named outputs include `historical_version_audit.csv`, `historical_retrieval_results.csv`, `historical_feature_agreement.csv`, `rq2_robustness_results.csv`, and `rq2_timing_sensitivity.csv` under `results/tables/`; verify their actual paths.

### Historical timing caveat

Earlier timing audit counts among 22,756 matched entries: 7,408 captured-last-commit-before-PR, 6,451 existed-before-PR-with-later-edits, 8,895 first-recorded-after-PR, and 2 inconsistent dates. Recorded historical pre-PR commits existed for 13,519 entries. A separate check flagged 341 discrepancies between file-level pre-PR classifications and recorded historical first commits. These are **timing-definition discrepancies**, not proven dataset errors. Pre-PR file existence does **not** show that today's extracted signal was present before coding began.

## 8. Phase 3: Manual audit (Scripts 12–13)

```powershell
python scripts/12_prepare_manual_audit.py
# Inspect actual specification content and historical versions manually.
# Record reviewer judgments and evidence in the generated CSV.
python scripts/13_analyze_manual_audit.py
```

Previously prepared worksheet: `results/manual_audit/manual_audit_template.csv` with **40 candidate records**. Earlier review covered only five preliminary judgments: three provisional true positives, one provisional false negative, one unresolved case; the remaining 35 were pending. **No complete 40-case validation or confirmed detector accuracy may be claimed.**

For each reviewed case, record PR URL/ID, file path, inspected commit or SHA, extracted signal, manual classification, quoted evidence location, reviewer notes, and whether the inspected version matches the feature extraction target. True/false positive/negative labels require comparable versions and definitions. Report unresolved examples transparently.

## 9. Phase 3: Timing sensitivity (Script 14)

Required inputs in `results/tables/`:

```text
rq2_pr_level_data.csv
spec_pr_timing_audit.csv
historical_version_audit.csv
```

Run:

```powershell
python scripts/14_timing_sensitivity.py
```

Expected outputs:

```text
results/phase3/timing_sensitivity_populations.csv
results/phase3/timing_sensitivity_rq2.csv
```

The **submitted Scripts 14 and 16 (verified together on the bundled data)** use population labels `all_matched`, `all_specs_pre_pr_history`, and `all_specs_consistent_pre_pr_history`. Script 14 emits `rate_present`, `rate_absent`, `rate_difference`, `median_files_present_code_changing`, and `median_files_absent_code_changing`. Script 16 expects these exact names. An older `results/tables/timing_sensitivity_rq2.csv` uses a different schema (`rate_difference_present_minus_absent` and population labels without `_history`); do not substitute that older file for the regenerated `results/phase3/timing_sensitivity_rq2.csv`.

The conservative restrictions require **all matched specs for a PR** to satisfy the historical criterion. Earlier results reported 5,725 PRs in the full population, 2,234 in the pre-PR-history subset, and 1,906 in the consistent-history subset; recheck against your own generated summary. These are **sensitivity subsets**, not proof of historical feature availability or causal ordering.

## 10. Phase 3: Matching coverage (Script 15)

Run after the core matching output exists:

```powershell
python scripts/15_matching_coverage.py
```

Intended output: `results/phase3/matching_coverage_by_pr.csv`.

The supplied draft categorizes PRs as `complete_match`, `partial_match`, or `no_match` using `pr_files.parquet` and `results/tables/spec_pr_analysis_sample.csv`. **Verify that the actual file schemas contain the expected `is_spec`, `file_path`, and PR-key columns** before running. The first coverage table is diagnostic only; to establish RQ2 matching sensitivity, recompute the signal comparisons on complete-match PRs and compare with the original population. **That final comparison remains pending verification.**

## 11. Phase 3: Interpretation review (Script 16)

Run after Script 14:

```powershell
python scripts/16_interpretation_review.py
```

Expected output: `results/phase3/interpretation_review.csv`.

**Verified compatibility:** The uploaded Script 16 correctly expects the schema emitted by uploaded Script 14. Its configuration is:

```python
metric = "rate_difference"
population_order = [
    "all_matched",
    "all_specs_pre_pr_history",
    "all_specs_consistent_pre_pr_history",
]
```

Script 16 flags directional changes and small groups; its group-size threshold is an exploratory warning, **not** a statistical significance test. The uploaded Scripts 14 and 16 were executed together successfully on the ZIP-bundled tables, producing 42 timing comparisons and 14 interpretation rows. This verifies this downstream pair, not the complete 01–16 pipeline.

## 12. White-box diagrams and figures

The Phase 3 report should include **implementation-grounded** diagrams explaining:

1. **Matching:** PR specification-file selection → repository/path matching → ambiguous/unmatched exclusions → feature join by `file_url_sha16` → PR join by `(tool, repo_name, pr_number)`.
2. **RQ1/RQ2:** matched records → distinct-spec deduplication for RQ1 versus PR aggregation for RQ2 → signal prevalence and code-change comparisons.
3. **Timing sensitivity:** historical commit comparison → conservative PR population filters → recomputed RQ2 associations → full-versus-restricted comparisons.

The diagrams are maintained as separate figure artifacts or embedded in the Phase 3 document. **Check each arrow and exclusion rule against actual code**; do not present a proposed diagram as verified implementation. Export diagrams to `results/figures/` or another clearly documented folder, and label them consistently in the report.

## 13. Related work, validity, and interpretation boundaries

The report's Related Work comparison should record for each cited study: bibliographic reference, objective, dataset, method, principal findings, limitations, and difference from this study. **Verify claims against the original papers**; an unverified thematic summary is not a literature review.

Four required validity categories:

| Category | Study-specific concern |
|---|---|
| Conclusion validity | Small signal groups, multiple comparisons, repository-correlated PRs, bootstrap uncertainty |
| Internal validity | PR/spec temporal ordering, project/PR confounding, unmatched specification entries |
| Construct validity | Automated signal semantics; code-file counts are not implementation smoothness; historical extractor mismatch |
| External validity | SpecMine repository selection, format and workflow differences, limited transfer to other projects |

Report associations, denominators, uncertainty, and sensitivity checks. **Do not assert causation, lower defect rates, faster delivery, or smoother implementation without measuring those outcomes.**

## 14. Reproducibility and quality checks

```powershell
# Check syntax only; this does not execute experiments.
python -m compileall -q scripts

# Review outputs and file sizes.
Get-ChildItem .\results -Recurse -File | Select-Object FullName, Length

# Record the working environment.
python -m pip freeze > environment_snapshot.txt
```

Before submission, independently verify:

- All scripts referenced here exist, and their filenames and execution order are correct.
- Each documented command runs from a clean environment with the specified five Parquet inputs.
- Required intermediate outputs are generated and downstream scripts read the correct columns.
- Dataset provenance, dependencies, random seeds, bootstrap count, and GitHub retrieval limits are recorded.
- Matching/timing denominators and RQ1/RQ2 figures agree with regenerated outputs.
- Historical and manual audit caveats are accurately disclosed.
- The report includes inspected evidence, three white-box diagrams, Related Work comparison, four validity categories, conclusions, and future work.
- Source-code reproduction is **tested**, not inferred from syntax checks alone.

## 15. Troubleshooting

| Symptom | Check |
|---|---|
| `FileNotFoundError` | Run from project root; confirm `data/` and `results/tables/` filenames. |
| `ModuleNotFoundError` | Activate the correct virtual environment and install the missing package. |
| Script 16 reports missing `rate_difference` | Run the uploaded Script 14 first; do not use the older `results/tables/timing_sensitivity_rq2.csv` with a different schema. |
| Script 16 reports missing population | Use the regenerated `results/phase3/timing_sensitivity_rq2.csv`, whose labels end in `_history`. |
| Script 14 fails a uniqueness or coverage assertion | Inspect duplicate PR/spec keys and unmatched history records; do not suppress the assertion without auditing. |
| GitHub retrieval fails or returns incomplete results | Check network access, rate limits, token permissions, and pilot sample size. |
| Output differs from reported numbers | Record dataset version, input hashes, code revision, parameters, and any filtering changes before interpreting differences. |

## 16. Known limitations and outstanding work

- Full manual validation remains incomplete; preliminary labels are not established accuracy estimates.
- Historical feature extraction is a pilot and not demonstrated equivalent to the source extractor.
- Timing restrictions do not establish that signals preceded implementation.
- The complete-match RQ2 sensitivity comparison remains pending. The repository-bootstrap configuration and generated robustness output should be checked together before final reporting.
- Reproduction must be tested on the actual repository; this README alone does not prove it works.
- Final report and README narrative must comply with the course's original-writing requirements; the team should review, revise, and take responsibility for all submitted text.