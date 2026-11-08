import csv
from collections import Counter
from pathlib import Path

SOURCE = Path("results/manual_audit/manual_audit_reviewed.csv")

if not SOURCE.exists():
    SOURCE = Path("manual_audit_reviewed.csv")

if not SOURCE.exists():
    raise FileNotFoundError(
        "Place manual_audit_reviewed.csv in results/manual_audit/"
    )

with SOURCE.open(newline="", encoding="utf-8-sig") as handle:
    records = list(csv.DictReader(handle))

status = Counter(
    r.get("review_status", "UNKNOWN")
    for r in records
)

provisional = Counter(
    r.get("provisional_classification", "")
    for r in records
    if r.get("provisional_classification")
)

confirmed = [
    r for r in records
    if r.get("manual_signal_present") in ("0", "1")
    and r.get("manual_match_valid") in ("0", "1")
    and r.get("spec_version_reviewed", "").strip()
    and r.get("evidence_url", "").strip()
    and r.get("evidence_excerpt", "").strip()
]

print("\n=== Phase 3 Manual Audit Summary ===")
print("Total sampled records:", len(records))
print("Review status:", dict(status))
print("Provisional classifications:", dict(provisional))
print("Records with basic evidence completed:", len(confirmed))

print("\nIMPORTANT:")
print("Provisional classifications are NOT confirmed results.")
print("Evidence completeness does not prove detector correctness.")
print("Historical version equivalence must be checked separately.")
