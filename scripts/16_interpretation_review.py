
from pathlib import Path
import pandas as pd

SOURCE = Path("results/phase3/timing_sensitivity_rq2.csv")
OUT = Path("results/phase3")
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(SOURCE)

metric = "rate_difference"

required = {
    "population", "signal", "n_present", "n_absent", metric
}
missing = required - set(df.columns)
if missing:
    raise ValueError(f"Missing columns: {missing}")

wide = df.pivot(
    index="signal",
    columns="population",
    values=metric
)

counts = df.pivot(
    index="signal",
    columns="population",
    values="n_present"
)

absent = df.pivot(
    index="signal",
    columns="population",
    values="n_absent"
)

population_order = [
    "all_matched",
    "all_specs_pre_pr_history",
    "all_specs_consistent_pre_pr_history",
]

for population in population_order:
    if population not in wide.columns:
        raise ValueError(f"Missing population: {population}")

rows = []

for signal in wide.index:
    effects = [wide.loc[signal, p] for p in population_order]
    smallest_group = min(
        min(counts.loc[signal, p], absent.loc[signal, p])
        for p in population_order
    )

    signs = [
        "positive" if x > 0 else
        "negative" if x < 0 else "zero"
        for x in effects
    ]

    rows.append({
        "signal": signal,
        "full_difference_pp": effects[0] * 100,
        "pre_pr_difference_pp": effects[1] * 100,
        "consistent_difference_pp": effects[2] * 100,
        "direction_changes": len(set(signs)) > 1,
        "smallest_comparison_group": smallest_group,
        "small_group_warning": smallest_group < 30,
        "max_difference_shift_pp": (
            max(effects) - min(effects)
        ) * 100,
    })

result = pd.DataFrame(rows)
result = result.sort_values(
    "max_difference_shift_pp", ascending=False
)

destination = OUT / "interpretation_review.csv"
result.to_csv(destination, index=False)

print(result.to_string(index=False))
print(f"\nSaved: {destination}")
