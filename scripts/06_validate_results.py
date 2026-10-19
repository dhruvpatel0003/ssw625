from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "results" / "tables"

FILES = {
    "matching": "spec_pr_analysis_sample.csv",
    "timing": "spec_pr_timing_audit.csv",
    "rq1": "rq1_signal_frequencies.csv",
    "rq2": "rq2_associations.csv",
    "rq2_pr": "rq2_pr_level_data.csv",
}

data = {}
issues = []

print("=== STEP 6: RESULTS VALIDATION ===")

for name, filename in FILES.items():
    path = TABLES / filename

    if not path.exists():
        issues.append(f"Missing output: {filename}")
        print(f"[MISSING] {filename}")
        continue

    df = pd.read_csv(path)
    data[name] = df
    print(f"[FOUND] {filename}: {len(df):,} rows")

# Check matching sample.
if "matching" in data:
    df = data["matching"]
    keys = ["tool", "repo_name", "pr_number", "file_url_sha16"]

    if all(col in df.columns for col in keys):
        duplicates = int(df.duplicated(keys).sum())
        print(f"\nDuplicate spec-PR pairs: {duplicates:,}")

        if duplicates:
            issues.append("Duplicate specification-PR pairs")

# Check RQ1 frequency calculations.
if "rq1" in data:
    df = data["rq1"]

    required = [
        "valid_values",
        "specs_with_signal",
        "percentage",
    ]

    if all(col in df.columns for col in required):
        invalid = df.loc[
            (df["specs_with_signal"] > df["valid_values"])
            | (df["specs_with_signal"] < 0)
            | (df["percentage"] < 0)
            | (df["percentage"] > 100)
        ]

        if not invalid.empty:
            issues.append("Invalid RQ1 frequency values")

        expected = (
            100
            * df["specs_with_signal"]
            / df["valid_values"].replace(0, float("nan"))
        ).round(2)

        mismatches = (
            (expected - df["percentage"]).abs() > 0.01
        ).fillna(False)

        if mismatches.any():
            issues.append("RQ1 percentage mismatch")

# Check RQ2 group counts and outcomes.
if "rq2" in data:
    df = data["rq2"]

    required = ["n_prs", "n_code_changed", "code_change_rate_pct"]

    if all(col in df.columns for col in required):
        invalid = df.loc[
            (df["n_code_changed"] > df["n_prs"])
            | (df["n_code_changed"] < 0)
            | (df["n_prs"] < 0)
        ]

        if not invalid.empty:
            issues.append("Invalid RQ2 group counts")

# Check timing coverage.
if "timing" in data:
    df = data["timing"]

    if "timing_class" in df.columns:
        print("\n=== TIMING DISTRIBUTION ===")
        print(df["timing_class"].value_counts(dropna=False))

        unknown = df["timing_class"].isin([
            "unknown_missing_dates",
            "inconsistent_dates",
        ]).sum()

        print(f"Unknown/inconsistent timing: {unknown:,}")

# Check PR-level dataset.
if "rq2_pr" in data:
    df = data["rq2_pr"]
    keys = ["tool", "repo_name", "pr_number"]

    if all(col in df.columns for col in keys):
        duplicates = int(df.duplicated(keys).sum())

        print(f"\nDuplicate PR-level rows: {duplicates:,}")

        if duplicates:
            issues.append("Duplicate PR-level records")

print("\n=== VALIDATION SUMMARY ===")

if issues:
    for issue in issues:
        print(f"[CHECK] {issue}")
else:
    print("Basic structural and arithmetic checks passed.")

print(
    "\nNote: Passing these checks does not establish "
    "historical timing validity or causal interpretation."
)