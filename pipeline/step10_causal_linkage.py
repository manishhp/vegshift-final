import json, numpy as np, pandas as pd
from scipy.stats import wilcoxon

df          = pd.read_csv('data/processed/vegshift_master.csv')
transitions = json.load(open('data/output/transition_report.json'))

results = []
for event in transitions:
    city, t_year = event['city'], event['transition_year']
    cdf = df[df['city'] == city].sort_values('year').reset_index(drop=True)

    pre  = cdf[cdf['year'].between(t_year-3, t_year-1)]['cvle_label'].tolist()
    post = cdf[cdf['year'].between(t_year+1, t_year+3)]['cvle_label'].tolist()

    if len(pre) < 2 or len(post) < 2:
        continue

    n = min(len(pre), len(post))
    try:
        _, pval = wilcoxon(pre[:n], post[:n])
    except Exception:
        pval = np.nan

    post_rows  = cdf[cdf['year'] > t_year]
    cvle_years = post_rows[post_rows['cvle_label'] == 1]['year'].tolist()
    cvle_lag   = (cvle_years[0] - t_year) if cvle_years else None

    results.append({
        'city':                    city,
        'transition_year':         t_year,
        'from_zone':               event['from_zone'],
        'to_zone':                 event['to_zone'],
        'pre_risk_mean':           round(np.mean(pre), 3),
        'post_risk_mean':          round(np.mean(post), 3),
        'risk_delta':              round(np.mean(post) - np.mean(pre), 3),
        'p_value':                 round(pval, 4) if not np.isnan(pval) else None,
        'significant':             bool(pval < 0.05) if not np.isnan(pval) else False,
        'post_transition_cvle_lag': cvle_lag,
    })

json.dump(results, open('data/output/transition_cvle_linkage.json', 'w'), indent=2)
print(f"\nTransition-to-CVLE Linkage ({len(results)} events):")
for r in results:
    lag_str = f"lag={r['post_transition_cvle_lag']}yr" if r['post_transition_cvle_lag'] else "no CVLE"
    sig = "YES" if r['significant'] else "no"
    print(f"  {r['city']} {r['transition_year']}: {r['from_zone']}->{r['to_zone']} "
          f"delta={r['risk_delta']:+.3f} p={r['p_value']} "
          f"sig={sig} {lag_str}")
