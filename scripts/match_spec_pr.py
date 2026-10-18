from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "results" / "tables"
OUT.mkdir(parents=True, exist_ok=True)

# Load only the columns needed for matching.
specs = pd.read_parquet(
    DATA / "spec_files.parquet",
    columns=[
        "file_url_sha16",
        "repo_name",
        "file_path",
        "file_first_commit_at",
        "file_last_commit_at",
    ],
)

features = pd.read_parquet(
    DATA / "spec_content_features.parquet",
    columns=["file_url_sha16"],
)

prs = pd.read_parquet(
    DATA / "pull_requests.parquet",
    columns=[
        "tool", "repo_name", "pr_number",
        "created_at", "merged_at",
        "touches_code", "n_code_files",
        "n_code_outside", "additions", "deletions",
    ],
)

pr_files = pd.read_parquet(
    DATA / "pr_files.parquet",
    columns=[
        "tool", "repo_name", "pr_number",
        "file_path", "is_spec",
    ],
)

# Match PR file changes with captured specification files.
spec_changes = pr_files.loc[
    pr_files["is_spec"] == 1
].copy()

# Deduplicate identical spec-file entries within a PR.
spec_changes = spec_changes.drop_duplicates(
    ["tool", "repo_name", "pr_number", "file_path"]
)

# Check whether repo/path identifies a unique specification.
duplicates = specs.duplicated(
    ["repo_name", "file_path"], keep=False
)

ambiguous = specs.loc[duplicates].copy()
unique_specs = specs.loc[~duplicates].copy()

# Join only uniquely identifiable repo/path pairs.
matched = spec_changes.merge(
    unique_specs,
    on=["repo_name", "file_path"],
    how="left",
    validate="many_to_one",
    indicator=True,
)

# Attach PR outcomes.
matched = matched.merge(
    prs,
    on=["tool", "repo_name", "pr_number"],
    how="left",
    validate="many_to_one",
)

# Check which matched specs have content features.
feature_ids = features.drop_duplicates("file_url_sha16")
matched = matched.merge(
    feature_ids.assign(has_features=True),
    on="file_url_sha16",
    how="left",
    validate="many_to_one",
)

matched["has_features"] = (
    matched["has_features"].fillna(False).astype(bool)
)

# Only keep records with a unique spec match and feature row.
analysis_sample = matched.loc[
    (matched["_merge"] == "both")
    & matched["has_features"]
].copy()

analysis_sample = analysis_sample.drop(columns=["_merge"])

matched.to_csv(OUT / "spec_pr_match_audit.csv", index=False)
analysis_sample.to_csv(
    OUT / "spec_pr_analysis_sample.csv", index=False
)

print("\n=== MATCHING AUDIT ===")
print(f"PR spec-file entries: {len(spec_changes):,}")
print(f"Ambiguous census spec rows: {len(ambiguous):,}")
print(f"Matched unique spec-file entries: "
      f"{(matched['_merge'] == 'both').sum():,}")
print(f"Unmatched PR spec-file entries: "
      f"{(matched['_merge'] == 'left_only').sum():,}")
print(f"Matched entries with content features: "
      f"{len(analysis_sample):,}")
print(f"Distinct PRs in analysis sample: "
      f"{analysis_sample[['tool','repo_name','pr_number']].drop_duplicates().shape[0]:,}")

print("\nOutputs saved in results/tables/")
