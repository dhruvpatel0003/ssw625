from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "results" / "tables"
OUT.mkdir(parents=True, exist_ok=True)

INPUT = OUT / "spec_pr_analysis_sample.csv"

if not INPUT.exists():
    raise FileNotFoundError(
        "Run Step 2 first: spec_pr_analysis_sample.csv is missing."
    )

# -------------------------------------------------
# 1. Load Step 2 candidate matches
# -------------------------------------------------
sample = pd.read_csv(
    INPUT,
    dtype={
        "file_url_sha16": "string",
        "repo_name": "string",
        "file_path": "string",
        "tool": "string",
    },
)

PR_KEY = ["tool", "repo_name", "pr_number"]
PAIR_KEY = PR_KEY + ["file_url_sha16"]

print(f"Candidate spec-PR rows: {len(sample):,}")

# -------------------------------------------------
# 2. Audit duplicates and multiple specs per PR
# -------------------------------------------------
duplicate_pairs = sample.duplicated(PAIR_KEY).sum()

pr_counts = (
    sample.groupby(PR_KEY, dropna=False)
    .agg(
        spec_entries=("file_url_sha16", "size"),
        unique_specs=("file_url_sha16", "nunique"),
    )
    .reset_index()
)

multiple_specs = (pr_counts["unique_specs"] > 1).sum()

print(f"Duplicate spec-PR pairs: {duplicate_pairs:,}")
print(f"PRs with multiple specifications: {multiple_specs:,}")

# Do not silently discard conflicting duplicates.
if duplicate_pairs:
    print("WARNING: Duplicate spec-PR pairs need investigation.")

# -------------------------------------------------
# 3. Load specification commit history
# -------------------------------------------------
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
    errors="coerce",
    utc=True,
)

commit_summary = (
    commits.groupby("file_url_sha16", dropna=False)
    .agg(
        history_commit_rows=("commit_sha", "size"),
        history_first_commit=("committed_at", "min"),
        history_last_commit=("committed_at", "max"),
    )
    .reset_index()
)

sample = sample.merge(
    commit_summary,
    on="file_url_sha16",
    how="left",
    validate="many_to_one",
)

# -------------------------------------------------
# 4. Parse specification and PR timestamps
# -------------------------------------------------
DATE_COLUMNS = [
    "file_first_commit_at",
    "file_last_commit_at",
    "created_at",
    "merged_at",
]

for col in DATE_COLUMNS:
    if col not in sample.columns:
        raise ValueError(f"Required column missing: {col}")

    sample[col] = pd.to_datetime(
        sample[col],
        errors="coerce",
        utc=True,
    )

# -------------------------------------------------
# 5. Classify timing relative to PR creation
# -------------------------------------------------
def classify_timing(row):
    pr = row["created_at"]
    first = row["file_first_commit_at"]
    last = row["file_last_commit_at"]

    if pd.isna(pr) or pd.isna(first) or pd.isna(last):
        return "unknown_missing_dates"

    if first > last:
        return "inconsistent_dates"

    if last <= pr:
        return "captured_last_commit_before_pr"

    if first > pr:
        return "first_recorded_after_pr"

    return "existed_before_pr_but_later_edits"

sample["timing_class"] = sample.apply(
    classify_timing, axis=1
)

# -------------------------------------------------
# 6. Check consistency with commit-history table
# -------------------------------------------------
sample["history_available"] = (
    sample["history_commit_rows"].notna()
)

sample["history_first_matches"] = (
    sample["history_first_commit"].notna()
    & sample["file_first_commit_at"].notna()
    & (
        sample["history_first_commit"]
        == sample["file_first_commit_at"]
    )
)

sample["history_last_matches"] = (
    sample["history_last_commit"].notna()
    & sample["file_last_commit_at"].notna()
    & (
        sample["history_last_commit"]
        == sample["file_last_commit_at"]
    )
)

# These mismatches are audit signals, not necessarily errors.
# Commit-history coverage may be incomplete or use different
# timestamp conventions.

# -------------------------------------------------
# 7. Summarize and save results
# -------------------------------------------------
summary = (
    sample.groupby("timing_class", dropna=False)
    .size()
    .reset_index(name="spec_pr_entries")
)

summary["percentage"] = (
    100 * summary["spec_pr_entries"] / len(sample)
).round(2)

sample.to_csv(
    OUT / "spec_pr_timing_audit.csv",
    index=False,
)

summary.to_csv(
    OUT / "timing_summary.csv",
    index=False,
)

pr_counts.to_csv(
    OUT / "pr_spec_multiplicity.csv",
    index=False,
)

print("\n=== TIMING SUMMARY ===")
print(summary.to_string(index=False))

print("\n=== COMMIT HISTORY CHECK ===")
print(
    "Entries with commit history:",
    f"{sample['history_available'].sum():,}",
)

print(
    "First-date matches:",
    f"{sample['history_first_matches'].sum():,}",
)

print(
    "Last-date matches:",
    f"{sample['history_last_matches'].sum():,}",
)

print("\n=== OUTPUT FILES ===")
print("spec_pr_timing_audit.csv")
print("timing_summary.csv")
print("pr_spec_multiplicity.csv")
