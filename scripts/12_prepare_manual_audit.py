from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MATCHES = ROOT / 'results' / 'tables' / 'spec_pr_analysis_sample.csv'
FEATURES = ROOT / 'data' / 'spec_content_features.parquet'
OUTPUT = ROOT / 'results' / 'manual_audit'
OUTPUT.mkdir(parents=True, exist_ok=True)

SEED = 625
SAMPLE_SIZE = 40
PR_KEY = ['tool', 'repo_name', 'pr_number']
SIGNALS = [
    'has_requirements', 'has_purpose', 'has_dependencies',
    'has_non_goals', 'has_out_of_scope', 'has_edge_cases',
    'has_acceptance_criteria', 'has_success_criteria',
    'has_gherkin', 'n_scenario_blocks', 'n_todo',
    'has_open_questions', 'n_needs_clarification',
    'has_unfilled_placeholder',
]

if not MATCHES.exists() or not FEATURES.exists():
    raise SystemExit('Missing Step 2 output or features Parquet. Run Step 2 first and check data/.')

matches = pd.read_csv(MATCHES, dtype={'file_url_sha16': 'string'})
required = PR_KEY + ['file_url_sha16', 'file_path']
missing = [c for c in required if c not in matches.columns]
if missing:
    raise SystemExit(f'Matching output missing columns: {missing}')

features = pd.read_parquet(FEATURES, columns=['file_url_sha16'] + SIGNALS)
if features.file_url_sha16.duplicated().any():
    raise SystemExit('Feature IDs are not unique; investigate before sampling.')

pairs = matches.dropna(subset=['file_url_sha16']).drop_duplicates(PR_KEY + ['file_url_sha16']).copy()
pairs = pairs.merge(features, on='file_url_sha16', how='inner', validate='many_to_one')
if pairs.empty:
    raise SystemExit('No matched specification–PR pairs with features found.')

# Form explicit review strata; each case is a spec–PR pair, not a unique spec.
# Prioritize both positive and negative feature values in the selected cases.
for s in SIGNALS:
    v = pd.to_numeric(pairs[s], errors='coerce')
    pairs[s + '_binary'] = np.where(v.isna(), np.nan, (v > 0).astype(float))

rng = np.random.default_rng(SEED)
selected = []
selected_keys = set()

# One candidate per signal and observed state, where possible.
for signal in SIGNALS:
    for value in (1.0, 0.0):
        eligible = pairs.loc[pairs[signal + '_binary'] == value]
        if eligible.empty:
            continue 
       # Stable sort before RNG so selection is reproducible across runs.
        eligible = eligible.sort_values(PR_KEY + ['file_url_sha16'], kind='stable')
        order = rng.permutation(len(eligible))
        for idx in order:
            row = eligible.iloc[int(idx)]
            key = tuple(str(row[c]) for c in PR_KEY + ['file_url_sha16'])
            if key not in selected_keys:
                selected_keys.add(key)
                selected.append((row, signal, 'present' if value == 1 else 'absent'))
                break

# Fill remaining slots from all eligible pairs without replacement.
if len(selected) < SAMPLE_SIZE:
    ordered = pairs.sort_values(PR_KEY + ['file_url_sha16'], kind='stable')
    for idx in rng.permutation(len(ordered)):
        row = ordered.iloc[int(idx)]
        key = tuple(str(row[c]) for c in PR_KEY + ['file_url_sha16'])
        if key not in selected_keys:
            selected_keys.add(key)
            selected.append((row, 'has_acceptance_criteria', 'supplemental'))
            if len(selected) >= SAMPLE_SIZE:
                break

records = []
for i, (row, signal, stratum) in enumerate(selected[:SAMPLE_SIZE], start=1):
    rec = {
        'audit_id': f'MA-{i:03d}',
        **{c: row[c] for c in PR_KEY},
        'file_url_sha16': row['file_url_sha16'],
        'spec_path': row['file_path'],
        'signal_name': signal,
        'sampling_stratum': stratum,
        'automated_value': row[signal],
        'manual_signal_present': '',  # 1, 0, or uncertain after human inspection
        'manual_match_valid': '',     # yes, no, or uncertain after human inspection
        'spec_version_reviewed': '', # commit SHA or source version
        'evidence_url': '',
        'evidence_excerpt': '',
        'timing_assessment': '',      # pre-code, post-code, uncertain, etc.
        'reviewer_notes': '',
    }
    records.append(rec)

out = pd.DataFrame(records)
path = OUTPUT / 'manual_audit_template.csv'
out.to_csv(path, index=False)
print(f'Candidate pairs: {len(pairs):,}')
print(f'Selected records: {len(out):,} (seed={SEED})')
print(f'Output: {path}')