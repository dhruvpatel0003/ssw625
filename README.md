# SpecMine Empirical Study — Reproduction Guide

## Study scope

The analysis examines 14 specification-content indicators (completeness, verifiability, and unresolved-information indicators) and their associations with pull-request code changes. RQ1 uses distinct matched specification IDs; RQ2 uses matched pull requests. The analyses are observational; code-file counts are not measures of implementation quality or causal effects.

## Repository layout

```text
project-root/
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
│   └── 11_statistical_robustness.py
├── data/                      # Local input Parquet files (not committed)
└── results/
    ├── tables/                # Generated tables and audit files
    └── figures/               # Generated plots
```

## Input data

Place these **five** SpecMine Parquet files in `data/`, retaining their exact filenames:

```text
data/spec_files.parquet
data/spec_content_features.parquet
data/spec_file_commits.parquet
data/pull_requests.parquet
data/pr_files.parquet
```

Dataset version and official download location: Downloaded from the zenodo : https://zenodo.org/records/22102780.

The historical retrieval step also uses GitHub to fetch a limited set of earlier file versions; it is not required for the core RQ1/RQ2 analysis.

## Environment setup

From the project root, using Python 3 with a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install pandas numpy pyarrow matplotlib requests
```

These are packages imported by the provided scripts; for exact reproducibility, the team should supply and test a pinned `requirements.txt` from its working environment. If PowerShell activation is restricted, use `.venv\Scripts\python.exe` in place of `python` in the commands below.

## Run scripts individually

Run each command **from the project root**. Later steps consume files created by earlier steps. No `run_all.py`, `run_pipeline.py`, or equivalent one-command orchestration is included in the supplied code.

### Core analysis

```powershell
python scripts/01_inspect_dataset.py
python scripts/02_match_spec_pr.py
python scripts/03_timing_audit.py
python scripts/04_rq1_analysis.py
python scripts/05_rq2_analysis.py
python scripts/06_validate_results.py
python scripts/07_generate_figures.py
```

Key outputs include:

- `results/tables/dataset_schema.txt`
- `results/tables/spec_pr_match_audit.csv`
- `results/tables/spec_pr_analysis_sample.csv`
- `results/tables/spec_pr_timing_audit.csv`
- `results/tables/timing_summary.csv`
- `results/tables/rq1_signal_frequencies.csv`
- `results/tables/rq2_associations.csv`
- `results/tables/rq2_pr_level_data.csv`
- Charts under `results/figures/`

### Historical and robustness analyses

```powershell
python scripts/08_historical_version_audit.py
python scripts/09_retrieve_historical_specs.py
python scripts/10_historical_features.py
python scripts/11_statistical_robustness.py
```

Notes:

- `09_retrieve_historical_specs.py` makes GitHub HTTP requests. The script currently sets `MAX_RECORDS = 50`, so this is a **pilot**, not retrieval of the entire matched dataset.
- A GitHub token can be provided through the `GITHUB_TOKEN` environment variable where appropriate. Do not commit tokens or `.env` files.
- `10_historical_features.py` applies exploratory rules to retrieved content. These rules are **not established as equivalent** to the original SpecMine feature extractor.
- `11_statistical_robustness.py` currently sets `N_BOOTSTRAP = 100` in the supplied source. If this value is changed, record the new setting and regenerate the results before reporting them.

Additional outputs include `historical_version_audit.csv`, `historical_retrieval_results.csv`, `historical_feature_agreement.csv`, `rq2_robustness_results.csv`, and `rq2_timing_sensitivity.csv` under `results/tables/`.

## Measurement and interpretation notes

- RQ1 counts each distinct matched specification ID once.
- RQ2 aggregates signal presence across the specifications matched to each PR.
- In the supplied `05_rq2_analysis.py`, the code-file-count analysis uses **`n_code_outside`**. Do not describe that result as `n_code_files` unless the code and results are updated accordingly.
- The specification–PR matching procedure excludes ambiguous repository/path mappings. Report both unmatched and excluded records when discussing coverage.
- Recorded specification commits before PR creation do **not** prove that captured feature values existed before coding began.
- The code-change outcomes measure co-change behavior, not implementation quality or causation.
