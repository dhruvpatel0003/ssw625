from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "results" / "tables"
FIGURES = ROOT / "results" / "figures"
FIGURES.mkdir(parents=True, exist_ok=True)

manifest = []

def load_required(filename, columns):
    path = TABLES / filename
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {filename}. Run the earlier experiment first."
        )

    df = pd.read_csv(path)
    missing = set(columns) - set(df.columns)
    if missing:
        raise ValueError(
            f"{filename} is missing columns: {sorted(missing)}"
        )
    return df

def save_figure(fig, filename, source):
    output = FIGURES / filename
    fig.savefig(output, dpi=250, bbox_inches="tight")
    plt.close(fig)
    manifest.append({
        "figure": filename,
        "source": source,
    })
    print(f"[SAVED] {output.name}")

# --------------------------------------------------
# Figure 1: RQ1 signal prevalence
# --------------------------------------------------
rq1 = load_required(
    "rq1_signal_frequencies.csv",
    ["dimension", "signal", "percentage"],
)

for dimension, group in rq1.groupby("dimension", sort=False):
    group = group.sort_values("percentage")

    fig, ax = plt.subplots(
        figsize=(10, max(4, len(group) * 0.65))
    )
    ax.barh(group["signal"], group["percentage"])
    ax.set_xlim(0, 100)
    ax.set_xlabel("Specifications containing signal (%)")
    ax.set_title(f"RQ1: {dimension}")
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()

    slug = dimension.lower().replace(" ", "_")
    save_figure(
        fig,
        f"final_rq1_{slug}.png",
        "rq1_signal_frequencies.csv",
    )

# --------------------------------------------------
# Figure 2: RQ2A code co-change rate
# --------------------------------------------------
rq2 = load_required(
    "rq2_associations.csv",
    [
        "dimension", "signal", "group",
        "code_change_rate_pct", "median_code_files",
    ],
)

for dimension, group in rq2.groupby("dimension", sort=False):
    pivot = group.pivot(
        index="signal",
        columns="group",
        values="code_change_rate_pct",
    )

    ax = pivot.plot.barh(
        figsize=(11, max(4, len(pivot) * 0.75))
    )
    ax.set_xlim(0, 100)
    ax.set_xlabel("PRs changing code (%)")
    ax.set_title(f"RQ2A: {dimension}")
    ax.legend(title="Signal")
    ax.grid(axis="x", alpha=0.2)
    plt.tight_layout()

    slug = dimension.lower().replace(" ", "_")
    fig = ax.get_figure()
    save_figure(
        fig,
        f"final_rq2a_{slug}.png",
        "rq2_associations.csv",
    )

# --------------------------------------------------
# Figure 3: RQ2B median code-file count
# --------------------------------------------------
for dimension, group in rq2.groupby("dimension", sort=False):
    pivot = group.pivot(
        index="signal",
        columns="group",
        values="median_code_files",
    )

    ax = pivot.plot.barh(
        figsize=(11, max(4, len(pivot) * 0.75))
    )
    ax.set_xlabel(
        "Median code files changed among code-changing PRs"
    )
    ax.set_title(f"RQ2B: {dimension}")
    ax.legend(title="Signal")
    ax.grid(axis="x", alpha=0.2)
    plt.tight_layout()

    slug = dimension.lower().replace(" ", "_")
    fig = ax.get_figure()
    save_figure(
        fig,
        f"final_rq2b_{slug}.png",
        "rq2_associations.csv",
    )

# --------------------------------------------------
# Figure 4: Timing audit
# --------------------------------------------------
timing_path = TABLES / "timing_summary.csv"

if timing_path.exists():
    timing = load_required(
        "timing_summary.csv",
        ["timing_class", "spec_pr_entries"],
    )

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.barh(
        timing["timing_class"],
        timing["spec_pr_entries"],
    )
    ax.set_xlabel("Specification-PR entries")
    ax.set_title("Specification Timing Relative to PR Creation")
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()

    save_figure(
        fig,
        "final_timing_audit.png",
        "timing_summary.csv",
    )
else:
    print(
        "[SKIPPED] Timing figure: timing_summary.csv not found."
    )

# --------------------------------------------------
# Save manifest
# --------------------------------------------------
manifest_df = pd.DataFrame(manifest)
manifest_df.to_csv(
    TABLES / "figure_manifest.csv",
    index=False,
)

print(f"\nGenerated {len(manifest)} figures.")
print("Manifest: results/tables/figure_manifest.csv")