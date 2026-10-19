from pathlib import Path
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT = ROOT / "results" / "tables" / "dataset_schema.txt"

TABLES = [
    "spec_files",
    "spec_content_features",
    "spec_file_commits",
    "pull_requests",
    "pr_files",
]

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

lines = []

for name in TABLES:
    path = DATA_DIR / f"{name}.parquet"

    if not path.exists():
        lines.append(f"MISSING: {path}")
        continue

    pf = pq.ParquetFile(path)

    lines.append(f"\n{'=' * 60}")
    lines.append(f"TABLE: {name}")
    lines.append(f"ROWS: {pf.metadata.num_rows:,}")
    lines.append(f"COLUMNS: {pf.metadata.num_columns}")

    for field in pf.schema_arrow:
        lines.append(f"{field.name}: {field.type}")

OUTPUT.write_text("\n".join(lines), encoding="utf-8")

print(f"Inspection complete: {OUTPUT}")

for name in TABLES:
    path = DATA_DIR / f"{name}.parquet"
    if path.exists():
        pf = pq.ParquetFile(path)
        print(f"{name}: {pf.metadata.num_rows:,} rows")
    else:
        print(f"{name}: MISSING")