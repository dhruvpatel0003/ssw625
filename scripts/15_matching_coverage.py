from pathlib import Path
import pandas as pd

DATA = Path("data")
TABLES = Path("results/tables")
OUTPUT = Path("results/phase3")
OUTPUT.mkdir(parents=True, exist_ok=True)

KEY = ["tool", "repo_name", "pr_number"]

pr_files = pd.read_parquet(DATA / "pr_files.parquet")
matched = pd.read_csv(TABLES / "spec_pr_analysis_sample.csv")

required_pr = KEY + ["file_path", "is_spec"]
required_matched = KEY + ["file_path"]

for label, frame, columns in [
    ("pr_files", pr_files, required_pr),
    ("matched", matched, required_matched),
]:
    missing = set(columns) - set(frame.columns)
    if missing:
        raise ValueError(f"{label} missing columns: {missing}")

spec_entries = (
    pr_files.loc[
        pr_files["is_spec"].astype(str).str.lower().isin(
            ["true", "1"]
        ),
        KEY + ["file_path"]
    ]
    .drop_duplicates()
)

matched_entries = matched[KEY + ["file_path"]].drop_duplicates()

coverage = spec_entries.merge(
    matched_entries.assign(is_matched=True),
    on=KEY + ["file_path"],
    how="left",
    validate="one_to_one"
)

coverage["is_matched"] = (
    coverage["is_matched"].fillna(False).astype(bool)
)

summary = coverage.groupby(KEY).agg(
    total_spec_files=("file_path", "size"),
    matched_spec_files=("is_matched", "sum")
).reset_index()

summary["unmatched_spec_files"] = (
    summary["total_spec_files"] -
    summary["matched_spec_files"]
)

summary["coverage_category"] = "partial_match"

summary.loc[
    summary["matched_spec_files"] == 0,
    "coverage_category"
] = "no_match"

summary.loc[
    summary["unmatched_spec_files"] == 0,
    "coverage_category"
] = "complete_match"

summary.to_csv(
    OUTPUT / "matching_coverage_by_pr.csv",
    index=False
)

print("\n=== Matching Coverage ===")
print(summary["coverage_category"].value_counts())
print("\nTotal PRs:", len(summary))
print("Total spec entries:", len(spec_entries))
print("Matched spec entries:", coverage["is_matched"].sum())
print("\nSaved:", OUTPUT / "matching_coverage_by_pr.csv")
