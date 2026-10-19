
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "results" / "tables"
TABLES.mkdir(parents=True, exist_ok=True)

PR_KEY = ["tool", "repo_name", "pr_number"]

SIGNALS = {
    "Completeness": [
        "has_requirements",
        "has_purpose",
        "has_dependencies",
        "has_non_goals",
        "has_out_of_scope",
        "has_edge_cases",
    ],
    "Verifiability": [
        "has_acceptance_criteria",
        "has_success_criteria",
        "has_gherkin",
        "n_scenario_blocks",
    ],
    "Unresolved information": [
        "n_todo",
        "has_open_questions",
        "n_needs_clarification",
        "has_unfilled_placeholder",
    ],
}

N_BOOTSTRAP = 100 
SEED = 625

INPUT = TABLES / "rq2_pr_level_data.csv"

if not INPUT.exists():
    raise FileNotFoundError(
        "Run Step 5 before Step 12."
    )

study = pd.read_csv(INPUT)

required = (
    PR_KEY
    + ["code_changed", "code_file_count"]
    + [s for group in SIGNALS.values() for s in group]
)

missing = set(required) - set(study.columns)

if missing:
    raise ValueError(
        f"Missing columns in RQ2 data: {sorted(missing)}"
    )

if study.duplicated(PR_KEY).any():
    raise ValueError("Duplicate PR-level records detected.")

# Only use valid binary outcomes.
study["code_changed"] = pd.to_numeric(
    study["code_changed"], errors="coerce"
)

study["code_file_count"] = pd.to_numeric(
    study["code_file_count"], errors="coerce"
)

study = study.loc[
    study["code_changed"].isin([0, 1])
].copy()

# --------------------------------------------------
# 1. Load timing-evidence subset
# --------------------------------------------------
timing_path = TABLES / "historical_version_audit.csv"

timing_prs = None

if timing_path.exists():
    timing = pd.read_csv(timing_path)

    required_timing = PR_KEY + ["historical_status"]

    if not set(required_timing).issubset(timing.columns):
        raise ValueError(
            "Historical audit missing required columns."
        )

    # Strict PR-level rule:
    # Every matched spec-PR record must have
    # a recorded pre-PR specification commit.
    timing["eligible"] = (
        timing["historical_status"]
        == "pre_pr_commit_identified"
    )

    timing_prs = (
        timing.groupby(PR_KEY)["eligible"]
        .all()
        .reset_index()
    )

# --------------------------------------------------
# 2. Calculate group differences
# --------------------------------------------------
def calculate_effect(df, signal):
    valid = df.loc[
        df[signal].isin([0, 1])
    ].copy()

    present = valid.loc[valid[signal] == 1]
    absent = valid.loc[valid[signal] == 0]

    if present.empty or absent.empty:
        return None

    rate_present = present["code_changed"].mean()
    rate_absent = absent["code_changed"].mean()

    # Percentage-point difference.
    rate_difference = (
        rate_present - rate_absent
    ) * 100

    # Conditional on the PR changing code.
    present_counts = present.loc[
        present["code_changed"] == 1,
        "code_file_count",
    ].dropna()

    absent_counts = absent.loc[
        absent["code_changed"] == 1,
        "code_file_count",
    ].dropna()

    median_difference = np.nan

    if len(present_counts) and len(absent_counts):
        median_difference = (
            present_counts.median()
            - absent_counts.median()
        )

    return {
        "n_present": len(present),
        "n_absent": len(absent),
        "rate_present_pct": rate_present * 100,
        "rate_absent_pct": rate_absent * 100,
        "rate_difference_pp": rate_difference,
        "median_code_file_difference": median_difference,
        "n_present_code_changed": len(present_counts),
        "n_absent_code_changed": len(absent_counts),
    }

# --------------------------------------------------
# 3. Repository-cluster bootstrap
# --------------------------------------------------
def cluster_bootstrap(df, signal, n_bootstrap, seed):
    rng = np.random.default_rng(seed)

    # One cluster per repository.
    # Preserve all PRs within sampled repositories.
    groups = [
        group
        for _, group in df.groupby("repo_name", sort=True)
    ]

    n_clusters = len(groups)

    if n_clusters < 2:
        return {
            "rate_ci_low": np.nan,
            "rate_ci_high": np.nan,
            "median_ci_low": np.nan,
            "median_ci_high": np.nan,
            "valid_rate_replicates": 0,
            "valid_median_replicates": 0,
        }

    rate_effects = []
    median_effects = []

    for _ in range(n_bootstrap):
        indices = rng.integers(
            0, n_clusters, size=n_clusters
        )

        sample = pd.concat(
            [groups[i] for i in indices],
            ignore_index=True,
        )

        effect = calculate_effect(sample, signal)

        if effect is None:
            continue

        rate_effects.append(
            effect["rate_difference_pp"]
        )

        if np.isfinite(
            effect["median_code_file_difference"]
        ):
            median_effects.append(
                effect["median_code_file_difference"]
            )

    def interval(values):
        if not values:
            return np.nan, np.nan

        return tuple(
            np.percentile(values, [2.5, 97.5])
        )

    rate_low, rate_high = interval(rate_effects)
    median_low, median_high = interval(median_effects)

    return {
        "rate_ci_low": rate_low,
        "rate_ci_high": rate_high,
        "median_ci_low": median_low,
        "median_ci_high": median_high,
        "valid_rate_replicates": len(rate_effects),
        "valid_median_replicates": len(median_effects),
    }

# --------------------------------------------------
# 4. Analyze full and timing-evidence samples
# --------------------------------------------------
samples = {"full_matched": study}

if timing_prs is not None:
    restricted = study.merge(
        timing_prs,
        on=PR_KEY,
        how="inner",
        validate="one_to_one",
    )

    restricted = restricted.loc[
        restricted["eligible"]
    ].copy()

    samples["recorded_pre_pr_commit"] = restricted

rows = []

for sample_name, sample_df in samples.items():
    print(
        f"\n=== {sample_name}: "
        f"{len(sample_df):,} PRs ==="
    )

    for dimension, signals in SIGNALS.items():
        for signal in signals:
            effect = calculate_effect(
                sample_df, signal
            )

            if effect is None:
                print(
                    f"[SKIP] {signal}: "
                    "one comparison group is empty."
                )
                continue

            bootstrap = cluster_bootstrap(
                sample_df,
                signal,
                N_BOOTSTRAP,
                SEED,
            )

            rows.append({
                "sample": sample_name,
                "dimension": dimension,
                "signal": signal,
                "n_prs": len(sample_df),
                "n_repositories": (
                    sample_df["repo_name"].nunique()
                ),
                **effect,
                **bootstrap,
            })

results = pd.DataFrame(rows)

if results.empty:
    raise RuntimeError(
        "No valid comparisons could be calculated."
    )

results.to_csv(
    TABLES / "rq2_robustness_results.csv",
    index=False,
)

# --------------------------------------------------
# 5. Compare full vs restricted estimates
# --------------------------------------------------
comparison = results.pivot(
    index=["dimension", "signal"],
    columns="sample",
    values="rate_difference_pp",
).reset_index()

comparison.to_csv(
    TABLES / "rq2_timing_sensitivity.csv",
    index=False,
)

print("\n=== ROBUSTNESS RESULTS ===")

display_columns = [
    "sample",
    "signal",
    "n_present",
    "n_absent",
    "rate_difference_pp",
    "rate_ci_low",
    "rate_ci_high",
    "median_code_file_difference",
]

print(
    results[display_columns]
    .round(2)
    .to_string(index=False)
)

print("\nSaved:")
print("results/tables/rq2_robustness_results.csv")
print("results/tables/rq2_timing_sensitivity.csv")

print(
    "\nCAUTION: These are descriptive associations. "
    "Confidence intervals do not resolve timing, "
    "selection bias, or confounding."
)