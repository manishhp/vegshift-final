import json, numpy as np, pandas as pd, joblib
from scipy import stats

df     = pd.read_csv('data/processed/vegshift_master.csv').dropna()
rf     = joblib.load('models/baselines/rf_baseline.pkl')
scaler = joblib.load('models/baselines/scaler.pkl')

FEATURES = [
    'temp_mean','temp_max','rainfall_annual','wind_speed','humidity','n_dry_months',
    'monsoon_onset_doy','sowing_window_miss','gdd_accumulation','crop_water_deficit',
    'pre_monsoon_depth_mbgl','depletion_rate','recharge_efficiency',
    'dual_deficit','gdd_adequate','gaez_baseline_class','koppen_zone_enc'
]

df['viability_risk_prob'] = rf.predict_proba(
    scaler.transform(df[FEATURES])
)[:, 1]

results = []
for city, cdf in df.groupby('city'):
    cdf  = cdf.sort_values('year')
    x, y = cdf['year'].values, cdf['viability_risk_prob'].values
    slope, intercept, r, pval, _ = stats.linregress(x, y)
    results.append({
        'city':      city,
        'crop':      cdf['crop'].iloc[0],
        'slope':     round(slope, 6),
        'intercept': round(intercept, 4),
        'r_squared': round(r**2, 4),
        'p_value':   round(pval, 4),
        'trend':     'deteriorating' if slope > 0 and pval < 0.05
                     else 'stable'    if pval >= 0.05
                     else 'improving',
    })

results_df = pd.DataFrame(results).sort_values('slope', ascending=False)
results_df.to_json('data/output/viability_trend_report.json',
                   orient='records', indent=2)
print(results_df[['city', 'crop', 'slope', 'r_squared', 'p_value', 'trend']].to_string())
