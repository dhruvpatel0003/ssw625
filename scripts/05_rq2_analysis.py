from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
TABLES = ROOT / "results" / "tables"
FIGURES = ROOT / "results" / "figures"

TABLES.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)

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

signal_names = [
    name
    for names in SIGNALS.values()
    for name in names
]

# --------------------------------------------------
# 1. Load matched spec-PR pairs and content features
# --------------------------------------------------
matches = pd.read_csv(
    TABLES / "spec_pr_analysis_sample.csv",
    dtype={"file_url_sha16": "string"},
)

features = pd.read_parquet(
    DATA / "spec_content_features.parquet",
    columns=["file_url_sha16"] + signal_names,
)

if features["file_url_sha16"].duplicated().any():
    raise ValueError("Duplicate specification feature IDs.")

# Each spec-PR pair should be counted once.
matches = matches.drop_duplicates(
    PR_KEY + ["file_url_sha16"]
)

study = matches.merge(
    features,
    on="file_url_sha16",
    how="inner",
    validate="many_to_one",
)

# --------------------------------------------------
# 2. Convert specification signals to binary values
# --------------------------------------------------
for name in signal_names:
    values = pd.to_numeric(study[name], errors="coerce")
    study[name] = np.where(
        values.isna(),
        np.nan,
        (values > 0).astype(float),
    )

# --------------------------------------------------
# 3. Aggregate specifications to PR level
# --------------------------------------------------
# PR has a signal if at least one matched spec has it.
# min_count=1 preserves missing values where appropriate.
pr_signals = (
    study.groupby(PR_KEY)[signal_names]
    .max()
    .reset_index()
)

prs = pd.read_parquet(
    DATA / "pull_requests.parquet",
    columns=PR_KEY + [
        "touches_code",
        "n_code_files",
        "n_code_outside",
    ],
)

if prs.duplicated(PR_KEY).any():
    raise ValueError(
        "Duplicate PR keys detected; investigate before analysis."
    )

pr_study = pr_signals.merge(
    prs,
    on=PR_KEY,
    how="inner",
    validate="one_to_one",
)

# Outcome A: code changed outside the specification directory.
pr_study["code_changed"] = pd.to_numeric(
    pr_study["touches_code"], errors="coerce"
)

# Outcome B: count of code files changed outside spec directory.
pr_study["code_file_count"] = pd.to_numeric(
    pr_study["n_code_outside"], errors="coerce"
)

# --------------------------------------------------
# 4. Calculate descriptive associations
# --------------------------------------------------
rows = []

for dimension, names in SIGNALS.items():
    for signal in names:
        for group_value, group_label in [
            (0.0, "Absent"),
            (1.0, "Present"),
        ]:
            group = pr_study.loc[
                pr_study[signal] == group_value
            ]

            valid_outcome = group["code_changed"].isin([0, 1])
            eligible = group.loc[valid_outcome]

            n = len(eligible)
            changed = int(
                (eligible["code_changed"] == 1).sum()
            )

            code_only = eligible.loc[
                eligible["code_changed"] == 1,
                "code_file_count",
            ].dropna()

            rows.append({
                "dimension": dimension,
                "signal": signal,
                "group": group_label,
                "n_prs": n,
                "n_code_changed": changed,
                "code_change_rate_pct": (
                    round(100 * changed / n, 2)
                    if n else np.nan
                ),
                "n_code_change_prs_with_count": len(code_only),
                "median_code_files": (
                    code_only.median()
                    if len(code_only) else np.nan
                ),
                "mean_code_files": (
                    round(code_only.mean(), 2)
                    if len(code_only) else np.nan
                ),
            })

results = pd.DataFrame(rows)

results.to_csv(
    TABLES / "rq2_associations.csv",
    index=False,
)

pr_study.to_csv(
    TABLES / "rq2_pr_level_data.csv",
    index=False,
)

print("\n=== RQ2 SAMPLE ===")
print(f"Matched specification-PR pairs: {len(study):,}")
print(f"Unique PRs: {len(pr_study):,}")
print("\n=== RQ2 RESULTS ===")
print(results.to_string(index=False))

# --------------------------------------------------
# 5. Visualize code-change rates
# --------------------------------------------------
for dimension, names in SIGNALS.items():
    subset = results.loc[
        results["dimension"] == dimension
    ]

    pivot = subset.pivot(
        index="signal",
        columns="group",
        values="code_change_rate_pct",
    ).reindex(names)

    ax = pivot.plot.barh(
        figsize=(11, max(5, len(names) * 0.8)),
    )

    ax.set_xlim(0, 100)
    ax.set_xlabel("PRs with code changes (%)")
    ax.set_ylabel("")
    ax.set_title(f"RQ2A — {dimension}")
    ax.legend(title="Signal")
    ax.grid(axis="x", alpha=0.2)

    plt.tight_layout()
    plt.savefig(
        FIGURES / (
            "rq2a_"
            + dimension.lower().replace(" ", "_")
            + ".png"
        ),
        dpi=200,
    )
    plt.close()

print("\nSaved:")
print("results/tables/rq2_associations.csv")
print("results/tables/rq2_pr_level_data.csv")
print("results/figures/rq2a_*.png")