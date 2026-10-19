from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
TABLES = ROOT / "results" / "tables"

TABLES.mkdir(parents=True, exist_ok=True)

PR_KEY = ["tool", "repo_name", "pr_number"]
PAIR_KEY = PR_KEY + ["file_url_sha16"]

# --------------------------------------------------
# 1. Load matched specification-PR pairs
# --------------------------------------------------
matches = pd.read_csv(
    TABLES / "spec_pr_analysis_sample.csv",
    dtype={"file_url_sha16": "string"},
)

required = PAIR_KEY + ["created_at"]

missing = set(required) - set(matches.columns)

if missing:
    raise ValueError(
        f"Matching sample is missing columns: {sorted(missing)}"
    )

pairs = matches[required].drop_duplicates(PAIR_KEY).copy()

pairs["created_at"] = pd.to_datetime(
    pairs["created_at"],
    utc=True,
    errors="coerce",
)

# --------------------------------------------------
# 2. Load specification commit history
# --------------------------------------------------
commits = pd.read_parquet(
    DATA / "spec_file_commits.parquet",
    columns=[
        "file_url_sha16",
        "commit_sha",
        "committed_at",
    ],
)

commits["committed_at"] = pd.to_datetime(
    commits["committed_at"],
    utc=True,
    errors="coerce",
)

commits = commits.drop_duplicates(
    ["file_url_sha16", "commit_sha", "committed_at"]
)

# Only retain commits belonging to matched specs.
commits = commits[
    commits["file_url_sha16"].isin(
        pairs["file_url_sha16"]
    )
].copy()

# --------------------------------------------------
# 3. Match commits to PRs and select historical version
# --------------------------------------------------
history = pairs.merge(
    commits,
    on="file_url_sha16",
    how="left",
)

eligible = history.loc[
    history["committed_at"].notna()
    & history["created_at"].notna()
    & (history["committed_at"] <= history["created_at"])
].copy()

eligible = eligible.sort_values(
    PAIR_KEY + ["committed_at", "commit_sha"]
)

latest_pre_pr = eligible.drop_duplicates(
    PAIR_KEY,
    keep="last",
)[PAIR_KEY + ["commit_sha", "committed_at"]].copy()

latest_pre_pr = latest_pre_pr.rename(
    columns={
        "commit_sha": "pre_pr_spec_commit_sha",
        "committed_at": "pre_pr_spec_committed_at",
    }
)

# --------------------------------------------------
# 4. Build complete manifest
# --------------------------------------------------
manifest = pairs.merge(
    latest_pre_pr,
    on=PAIR_KEY,
    how="left",
    validate="one_to_one",
)

history_available = (
    commits.groupby("file_url_sha16")["committed_at"]
    .apply(lambda x: x.notna().any())
    .rename("has_dated_commit_history")
    .reset_index()
)

manifest = manifest.merge(
    history_available,
    on="file_url_sha16",
    how="left",
    validate="many_to_one",
)

manifest["has_dated_commit_history"] = (
    manifest["has_dated_commit_history"]
    .fillna(False)
    .astype(bool)
)

manifest["historical_status"] = "unknown"

manifest.loc[
    manifest["created_at"].isna(),
    "historical_status",
] = "missing_pr_creation_date"

manifest.loc[
    manifest["created_at"].notna()
    & ~manifest["has_dated_commit_history"],
    "historical_status",
] = "no_dated_spec_history"

manifest.loc[
    manifest["created_at"].notna()
    & manifest["has_dated_commit_history"]
    & manifest["pre_pr_spec_commit_sha"].isna(),
    "historical_status",
] = "no_recorded_pre_pr_commit"

manifest.loc[
    manifest["pre_pr_spec_commit_sha"].notna(),
    "historical_status",
] = "pre_pr_commit_identified"

# --------------------------------------------------
# 5. Attach repository/path information for retrieval
# --------------------------------------------------
specs = pd.read_parquet(
    DATA / "spec_files.parquet",
    columns=[
        "file_url_sha16",
        "repo_name",
        "file_path",
    ],
)

# Preserve only unambiguous ID-to-path mappings.
path_counts = (
    specs.groupby("file_url_sha16")
    .agg(
        n_repos=("repo_name", "nunique"),
        n_paths=("file_path", "nunique"),
    )
    .reset_index()
)

unambiguous = path_counts.loc[
    (path_counts["n_repos"] == 1)
    & (path_counts["n_paths"] == 1),
    "file_url_sha16",
]

spec_paths = (
    specs[
        specs["file_url_sha16"].isin(unambiguous)
    ][["file_url_sha16", "repo_name", "file_path"]]
    .drop_duplicates()
)

manifest = manifest.merge(
    spec_paths,
    on=["file_url_sha16", "repo_name"],
    how="left",
    validate="many_to_one",
)

# --------------------------------------------------
# 6. Save audit and retrieval manifest
# --------------------------------------------------
manifest.to_csv(
    TABLES / "historical_version_audit.csv",
    index=False,
)

retrieval = manifest.loc[
    (manifest["historical_status"] == "pre_pr_commit_identified")
    & manifest["file_path"].notna(),
    [
        "tool",
        "repo_name",
        "pr_number",
        "file_url_sha16",
        "file_path",
        "created_at",
        "pre_pr_spec_commit_sha",
        "pre_pr_spec_committed_at",
    ],
].copy()

retrieval.to_csv(
    TABLES / "historical_retrieval_manifest.csv",
    index=False,
)

summary = (
    manifest["historical_status"]
    .value_counts(dropna=False)
    .rename_axis("historical_status")
    .reset_index(name="spec_pr_pairs")
)

summary.to_csv(
    TABLES / "historical_version_summary.csv",
    index=False,
)

print("=== HISTORICAL VERSION AUDIT ===")
print(f"Matched spec-PR pairs: {len(manifest):,}")
print("\nStatus distribution:")
print(summary.to_string(index=False))
print(
    "\nRecords with a pre-PR commit and path:",
    f"{len(retrieval):,}"
)

print("\nSaved:")
print("results/tables/historical_version_audit.csv")
print("results/tables/historical_retrieval_manifest.csv")
print("results/tables/historical_version_summary.csv")