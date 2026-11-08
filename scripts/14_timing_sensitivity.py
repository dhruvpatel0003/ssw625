from pathlib import Path
import pandas as pd

ROOT = Path('results/tables')
KEY = ['tool', 'repo_name', 'pr_number']
SIGNALS = ['has_requirements','has_purpose','has_dependencies','has_non_goals','has_out_of_scope','has_edge_cases','has_acceptance_criteria','has_success_criteria','has_gherkin','n_scenario_blocks','n_todo','has_open_questions','n_needs_clarification','has_unfilled_placeholder']

pr = pd.read_csv(ROOT / 'rq2_pr_level_data.csv')
timing = pd.read_csv(ROOT / 'spec_pr_timing_audit.csv')
hist = pd.read_csv(ROOT / 'historical_version_audit.csv')
for label, df in [('PR',pr),('timing',timing),('history',hist)]:
    missing = set(KEY)-set(df.columns)
    if missing: raise ValueError(f'{label} missing keys: {missing}')
assert not pr.duplicated(KEY).any(), 'PR data has duplicate PR keys'
JOIN = KEY + ['file_url_sha16']
assert not timing.duplicated(JOIN).any(), 'Timing data has duplicate spec-PR keys'
assert not hist.duplicated(JOIN).any(), 'History data has duplicate spec-PR keys'
records = timing.merge(hist[JOIN+['historical_status']],on=JOIN,how='left',validate='one_to_one',indicator=True)
assert (records['_merge']=='both').all(), 'History audit does not cover every timing record'
records['pre_pr'] = records['historical_status'].eq('pre_pr_commit_identified')
records['consistent_pre_pr'] = records['pre_pr'] & records['history_first_matches'].eq(True) & records['history_last_matches'].eq(True)
# Conservative PR-level restriction: ALL matched specs must satisfy the condition.
flags = records.groupby(KEY,dropna=False).agg(
    n_specs=('file_url_sha16','size'),
    all_pre_pr=('pre_pr','all'),
    all_consistent_pre_pr=('consistent_pre_pr','all')
).reset_index()
merged = pr.merge(flags,on=KEY,how='left',validate='one_to_one',indicator=True)
assert (merged['_merge']=='both').all(), 'PR timing coverage incomplete'
merged['all_pre_pr'] = merged['all_pre_pr'].fillna(False).astype(bool)
merged['all_consistent_pre_pr'] = merged['all_consistent_pre_pr'].fillna(False).astype(bool)

populations = {
    'all_matched': merged,
    'all_specs_pre_pr_history': merged[merged['all_pre_pr']],
    'all_specs_consistent_pre_pr_history': merged[merged['all_consistent_pre_pr']],
}
out = Path('results/phase3')
out.mkdir(parents=True,exist_ok=True)

summary = []
comparisons = []
for population_name, subset in populations.items():
    code = pd.to_numeric(subset['code_changed'],errors='coerce')
    summary.append({
        'population':population_name,
        'n_prs':len(subset),
        'n_code_changing':int((code==1).sum()),
        'code_change_rate':float((code==1).mean()) if len(subset) else float('nan'),
    })
    for signal in SIGNALS:
        values = pd.to_numeric(subset[signal],errors='coerce')
        present = values > 0
        absent = values == 0
        pos = subset.loc[present]
        neg = subset.loc[absent]
        pos_code = pd.to_numeric(pos['code_changed'],errors='coerce')
        neg_code = pd.to_numeric(neg['code_changed'],errors='coerce')
        rate_pos = float((pos_code==1).mean()) if len(pos) else float('nan')
        rate_neg = float((neg_code==1).mean()) if len(neg) else float('nan')
        pos_files = pd.to_numeric(pos.loc[pos_code==1,'code_file_count'],errors='coerce')
        neg_files = pd.to_numeric(neg.loc[neg_code==1,'code_file_count'],errors='coerce')
        comparisons.append({
            'population':population_name,
            'signal':signal,
            'n_present':len(pos),
            'n_absent':len(neg),
            'rate_present':rate_pos,
            'rate_absent':rate_neg,
            'rate_difference':rate_pos-rate_neg,
            'median_files_present_code_changing':pos_files.median(),
            'median_files_absent_code_changing':neg_files.median(),
            'median_difference':pos_files.median()-neg_files.median(),
        })
pd.DataFrame(summary).to_csv(out/'timing_sensitivity_populations.csv',index=False)
pd.DataFrame(comparisons).to_csv(out/'timing_sensitivity_rq2.csv',index=False)
print(pd.DataFrame(summary).to_string(index=False))
print(f'Saved {len(comparisons)} comparisons to {out}')
