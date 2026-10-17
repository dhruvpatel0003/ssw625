from pathlib import Path
import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"

TABLES = [
    "spec_files",
    "spec_content_features",
    "spec_file_commits",
    "pull_requests",
    "pr_files",
]

def main():
    for table in TABLES:
        path = DATA_DIR / f"{table}.parquet"

        if not path.exists():
            print(f"\n[NOT FOUND] {path}")
            continue

        parquet = pq.ParquetFile(path)

        print(f"\n{'=' * 60}")
        print(f"TABLE: {table}")
        print(f"ROWS: {parquet.metadata.num_rows:,}")
        print(f"COLUMNS: {parquet.metadata.num_columns}")

        for field in parquet.schema_arrow:
            print(f"  {field.name}: {field.type}")

if __name__ == "__main__":
    main()