from pathlib import Path
from urllib.parse import quote
import hashlib
import json
import os
import time

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "results" / "tables"
HISTORY = ROOT / "data" / "historical_specs"

MANIFEST = TABLES / "historical_retrieval_manifest.csv"
OUTPUT = TABLES / "historical_retrieval_results.csv"

HISTORY.mkdir(parents=True, exist_ok=True)

# Start with a small, reproducible pilot.
# Set to 0 for all records after reviewing the pilot.
MAX_RECORDS = 50

TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()

session = requests.Session()
session.headers.update({
    "Accept": "application/vnd.github.raw+json",
    "User-Agent": "SpecMine-Research-History-Audit",
    "X-GitHub-Api-Version": "2022-11-28",
})

if TOKEN:
    session.headers["Authorization"] = f"Bearer {TOKEN}"

def retrieve(repo, path, commit):
    encoded_repo = "/".join(
        quote(part, safe="") for part in repo.split("/")
    )
    encoded_path = quote(path, safe="/")
    encoded_sha = quote(commit, safe="")

    url = (
        f"https://api.github.com/repos/{encoded_repo}"
        f"/contents/{encoded_path}?ref={encoded_sha}"
    )

    try:
        response = session.get(url, timeout=30)
    except requests.RequestException as exc:
        return None, "network_error", str(exc)

    if response.status_code == 200:
        return response.content, "retrieved", ""

    if response.status_code in (403, 429):
        return None, "rate_limit_or_access_denied", (
            f"HTTP {response.status_code}"
        )

    if response.status_code == 404:
        return None, "not_found_or_inaccessible", "HTTP 404"

    return None, "http_error", f"HTTP {response.status_code}"

def main():
    if not MANIFEST.exists():
        raise FileNotFoundError(
            "Step 9 manifest missing. Run Step 9 first."
        )

    manifest = pd.read_csv(
        MANIFEST,
        dtype={
            "repo_name": "string",
            "file_path": "string",
            "pre_pr_spec_commit_sha": "string",
            "file_url_sha16": "string",
        },
    )

    required = [
        "repo_name",
        "file_path",
        "pre_pr_spec_commit_sha",
        "file_url_sha16",
    ]

    missing = set(required) - set(manifest.columns)
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    # One download per unique repository, path and commit.
    manifest = manifest.drop_duplicates(
        ["repo_name", "file_path", "pre_pr_spec_commit_sha"]
    ).sort_values(
        ["repo_name", "file_path", "pre_pr_spec_commit_sha"]
    )

    if MAX_RECORDS > 0:
        manifest = manifest.head(MAX_RECORDS)

    results = []

    for number, (_, row) in enumerate(
        manifest.iterrows(), start=1
    ):
        repo = str(row["repo_name"])
        path = str(row["file_path"])
        commit = str(row["pre_pr_spec_commit_sha"])

        print(f"[{number}/{len(manifest)}] {repo}: {path}")

        content, status, error = retrieve(
            repo, path, commit
        )

        saved_path = ""
        content_hash = ""
        byte_count = 0

        if content is not None:
            # Stable, collision-resistant local filename.
            identity = json.dumps(
                [repo, path, commit],
                ensure_ascii=False,
            )
            identifier = hashlib.sha256(
                identity.encode("utf-8")
            ).hexdigest()

            destination = HISTORY / f"{identifier}.bin"
            destination.write_bytes(content)

            saved_path = str(
                destination.relative_to(ROOT)
            )
            content_hash = hashlib.sha256(
                content
            ).hexdigest()
            byte_count = len(content)

        results.append({
            "repo_name": repo,
            "file_path": path,
            "commit_sha": commit,
            "status": status,
            "error": error,
            "saved_path": saved_path,
            "sha256": content_hash,
            "bytes": byte_count,
        })

        # Checkpoint after each request.
        pd.DataFrame(results).to_csv(
            OUTPUT, index=False
        )

        if status == "rate_limit_or_access_denied":
            print(
                "Stopping after HTTP 403/429. "
                "Check token permissions or rate limits."
            )
            break

        time.sleep(0.25)

    summary = pd.DataFrame(results)

    print("\n=== HISTORICAL RETRIEVAL SUMMARY ===")
    print(summary["status"].value_counts().to_string())
    print(f"\nSaved manifest: {OUTPUT}")

    print(
        "\nCAUTION: Retrieved content is not yet "
        "historically feature-validated."
    )

if __name__ == "__main__":
    main()