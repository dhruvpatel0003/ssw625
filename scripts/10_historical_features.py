from pathlib import Path
import re
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
TABLES = ROOT / "results" / "tables"

RETRIEVAL = TABLES / "historical_retrieval_results.csv"

if not RETRIEVAL.exists():
    raise FileNotFoundError(
        "Run Step 10 before Step 11."
    )

SIGNALS = [
    "has_requirements",
    "has_purpose",
    "has_dependencies",
    "has_non_goals",
    "has_out_of_scope",
    "has_edge_cases",
    "has_acceptance_criteria",
    "has_success_criteria",
    "has_gherkin",
    "n_scenario_blocks",
    "n_todo",
    "has_open_questions",
    "n_needs_clarification",
    "has_unfilled_placeholder",
]

# Headings in Markdown-style specifications.
HEADINGS = {
    "has_requirements": r"requirements?",
    "has_purpose": r"purpose|objectives?",
    "has_dependencies": r"dependencies",
    "has_non_goals": r"non[- ]goals?",
    "has_out_of_scope": r"out[- ]of[- ]scope",
    "has_edge_cases": r"edge[- ]cases?",
    "has_acceptance_criteria": r"acceptance[- ]criteria",
    "has_success_criteria": r"success[- ]criteria",
    "has_open_questions": r"open[- ]questions?",
}

def has_heading(text, pattern):
    expression = (
        r"(?im)^\s{0,3}#{1,6}\s+"
        r"(?:" + pattern + r")\s*:?\s*$"
    )
    return int(bool(re.search(expression, text)))

def extract_signals(text):
    values = {}

    for signal, pattern in HEADINGS.items():
        values[signal] = has_heading(text, pattern)

    scenario_pattern = (
        r"(?im)^\s*(?:Scenario|Scenario Outline):"
    )

    scenario_matches = re.findall(
        scenario_pattern, text
    )

    values["n_scenario_blocks"] = len(
        scenario_matches
    )

    values["has_gherkin"] = int(bool(
        re.search(
            r"(?im)^\s*(?:Feature|Scenario|Scenario Outline):",
            text,
        )
    ))

    values["n_todo"] = len(
        re.findall(r"(?i)\bTODO\b", text)
    )

    values["n_needs_clarification"] = len(
        re.findall(
            r"(?i)\bneeds?\s+clarification\b",
            text,
        )
    )

    values["has_unfilled_placeholder"] = int(bool(
        re.search(
            r"(?i)\b(?:TBD|TBC)\b|<placeholder>",
            text,
        )
    ))

    return values

def read_historical_file(relative_path):
    path = (ROOT / relative_path).resolve()

    # Reject paths outside the project.
    if ROOT.resolve() not in path.parents:
        raise ValueError("Unsafe file path")

    raw = path.read_bytes()

    try:
        return raw.decode("utf-8"), "utf8"
    except UnicodeDecodeError:
        return None, "decode_failed"

retrieval = pd.read_csv(RETRIEVAL)

records = []

for _, row in retrieval.iterrows():
    result = {
        "repo_name": row["repo_name"],
        "file_path": row["file_path"],
        "commit_sha": row["commit_sha"],
        "retrieval_status": row["status"],
        "extraction_status": "not_processed",
    }

    if row["status"] != "retrieved":
        records.append(result)
        continue

    if pd.isna(row["saved_path"]):
        result["extraction_status"] = "missing_saved_path"
        records.append(result)
        continue

    try:
        text, decoding = read_historical_file(
            str(row["saved_path"])
        )

        if text is None:
            result["extraction_status"] = decoding
        else:
            result.update(extract_signals(text))
            result["extraction_status"] = "extracted"

    except (OSError, ValueError) as exc:
        result["extraction_status"] = "file_error"
        result["error"] = str(exc)

    records.append(result)

historical = pd.DataFrame(records)

historical.to_csv(
    TABLES / "historical_exploratory_features.csv",
    index=False,
)

print("=== HISTORICAL FEATURE EXTRACTION ===")
print(
    historical["extraction_status"]
    .value_counts(dropna=False)
    .to_string()
)

# --------------------------------------------------
# Compare exploratory historical values with
# SpecMine's captured feature values.
# --------------------------------------------------
captured = pd.read_parquet(
    DATA / "spec_content_features.parquet",
    columns=["file_url_sha16"] + SIGNALS,
)

manifest = pd.read_csv(
    TABLES / "historical_retrieval_manifest.csv",
    dtype={"file_url_sha16": "string"},
)

historical = manifest.merge(
    historical,
    left_on=[
        "repo_name",
        "file_path",
        "pre_pr_spec_commit_sha",
    ],
    right_on=[
        "repo_name",
        "file_path",
        "commit_sha",
    ],
    how="left",
    validate="many_to_one",
)

comparison = historical.merge(
    captured,
    on="file_url_sha16",
    how="left",
    suffixes=("_historical", "_captured"),
    validate="many_to_one",
)

# Calculate agreement on binary signal presence.
# Counts are converted to >0 for this comparison.
agreement = []

valid = comparison.loc[
    comparison["extraction_status"] == "extracted"
].copy()

for signal in SIGNALS:
    old = pd.to_numeric(
        valid[f"{signal}_historical"],
        errors="coerce",
    )
    new = pd.to_numeric(
        valid[f"{signal}_captured"],
        errors="coerce",
    )

    comparable = old.notna() & new.notna()

    if not comparable.any():
        continue

    same = (
        old.loc[comparable].gt(0)
        == new.loc[comparable].gt(0)
    )

    agreement.append({
        "signal": signal,
        "n_compared": int(comparable.sum()),
        "n_agree": int(same.sum()),
        "agreement_pct": round(
            100 * same.mean(), 2
        ),
    })

agreement_df = pd.DataFrame(agreement)

comparison.to_csv(
    TABLES / "historical_feature_comparison.csv",
    index=False,
)

agreement_df.to_csv(
    TABLES / "historical_feature_agreement.csv",
    index=False,
)

print("\n=== HISTORICAL VS CAPTURED AGREEMENT ===")
print(agreement_df.to_string(index=False))

print("\nSaved:")
print("results/tables/historical_exploratory_features.csv")
print("results/tables/historical_feature_comparison.csv")