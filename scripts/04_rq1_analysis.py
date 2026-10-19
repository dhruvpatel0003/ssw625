from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
TABLES = ROOT / "results" / "tables"
FIGURES = ROOT / "results" / "figures"

TABLES.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------
# 1. Define signals before examining results
# --------------------------------------------------
SIGNALS = {
    "Completeness": {
        "has_requirements": "flag",
        "has_purpose": "flag",
        "has_dependencies": "flag",
        "has_non_goals": "flag",
        "has_out_of_scope": "flag",
        "has_edge_cases": "flag",
    },
    "Verifiability": {
        "has_acceptance_criteria": "flag",
        "has_success_criteria": "flag",
        "has_gherkin": "flag",
        "n_scenario_blocks": "count",
    },
    "Unresolved information": {
        "n_todo": "count",
        "has_open_questions": "flag",
        "n_needs_clarification": "count",
        "has_unfilled_placeholder": "flag",
    },
}

columns = [
    "file_url_sha16",
    *[
        name
        for group in SIGNALS.values()
        for name in group
    ],
]

# --------------------------------------------------
# 2. Load Step 2 candidate analysis sample
# --------------------------------------------------
matches = pd.read_csv(
    TABLES / "spec_pr_analysis_sample.csv",
    dtype={"file_url_sha16": "string"},
)

# RQ1 is specification-level:
# A spec linked to several PRs should be counted once.
spec_ids = matches[["file_url_sha16"]].dropna().drop_duplicates()

features = pd.read_parquet(
    DATA / "spec_content_features.parquet",
    columns=columns,
)

if features["file_url_sha16"].duplicated().any():
    raise ValueError("Duplicate feature IDs detected.")

study = spec_ids.merge(
    features,
    on="file_url_sha16",
    how="left",
    validate="one_to_one",
    indicator=True,
)

print("=== RQ1 SAMPLE ===")
print(f"Unique candidate specifications: {len(spec_ids):,}")
print(f"Specifications with features: "
      f"{(study['_merge'] == 'both').sum():,}")
print(f"Specifications missing features: "
      f"{(study['_merge'] == 'left_only').sum():,}")

study = study.loc[study["_merge"] == "both"].copy()

# --------------------------------------------------
# 3. Calculate frequencies
# --------------------------------------------------
results = []

for dimension, signals in SIGNALS.items():
    for column, kind in signals.items():

        values = pd.to_numeric(study[column], errors="coerce")
        valid = values.notna()
        present = values.gt(0) if kind == "count" else values.eq(1)

        n_valid = int(valid.sum())
        n_present = int((present & valid).sum())

        percentage = (
            100 * n_present / n_valid
            if n_valid else float("nan")
        )

        results.append({
            "dimension": dimension,
            "signal": column,
            "total_specs": len(study),
            "valid_values": n_valid,
            "missing_values": int((~valid).sum()),
            "specs_with_signal": n_present,
            "percentage": round(percentage, 2),
        })

result_df = pd.DataFrame(results)

result_df.to_csv(
    TABLES / "rq1_signal_frequencies.csv",
    index=False,
)

print("\n=== RQ1 RESULTS ===")
print(result_df.to_string(index=False))

# --------------------------------------------------
# 4. Generate a chart for each dimension
# --------------------------------------------------
for dimension, group in result_df.groupby(
    "dimension", sort=False
):
    group = group.sort_values("percentage")

    fig, ax = plt.subplots(figsize=(10, 5))

    ax.barh(
        group["signal"],
        group["percentage"],
    )

    ax.set_xlim(0, 100)
    ax.set_xlabel("Specifications with signal (%)")
    ax.set_title(f"RQ1 — {dimension}")
    ax.grid(axis="x", alpha=0.2)

    fig.tight_layout()

    filename = (
        dimension.lower().replace(" ", "_")
        + ".png"
    )

    fig.savefig(
        FIGURES / f"rq1_{filename}",
        dpi=200,
        bbox_inches="tight",
    )

    plt.close(fig)

print("\nSaved:")
print("results/tables/rq1_signal_frequencies.csv")
print("results/figures/rq1_*.png")
