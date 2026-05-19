# pipeline/step16_irrigation_strategy.py
import json, pandas as pd, numpy as np

# recharge_efficiency = depth_recovery_m / rainfall_annual_mm → values ~0.001–0.016
RSI_CRITICAL = 0.002  # recharge_efficiency < 0.002 → critical
RSI_STRESSED = 0.004  # recharge_efficiency < 0.004 → stressed
RSI_MODERATE = 0.006  # recharge_efficiency < 0.006 → moderate

WATER_HEAVY = {'rice', 'sugarcane', 'cotton'}

GOVT_SCHEMES = {
    'PM-KUSUM': 'Solar pump subsidy for off-grid irrigation',
    'PMKSY':    'Pradhan Mantri Krishi Sinchayee Yojana — drip/sprinkler subsidy',
    'MGNREGS':  'Water conservation works — check dams, ponds',
    'RKVY':     'Rashtriya Krishi Vikas Yojana — crop diversification grants',
    'PMFBY':    'Pradhan Mantri Fasal Bima Yojana — crop insurance',
}

df       = pd.read_csv('data/processed/vegshift_master.csv')
advisory = json.load(open('data/output/crop_advisory.json'))

# Monthly avg rainfall from daily file → optimal sowing window
daily = pd.read_csv('data/processed/kaggle_climate.csv', parse_dates=['date'])
daily['month'] = daily['date'].dt.month
monthly_rain = (daily.groupby(['city', 'month'])['rainfall']
                     .mean()
                     .reset_index()
                     .rename(columns={'rainfall': 'avg_monthly_rain_mm'}))

strategies = {}
for city, cdf in df.groupby('city'):
    cdf    = cdf.sort_values('year')
    latest = cdf.iloc[-1]
    rsi    = float(latest['recharge_efficiency'])
    gw_dep = float(latest['pre_monsoon_depth_mbgl'])
    depl   = float(latest['depletion_rate'])

    if rsi < RSI_CRITICAL or gw_dep > 20:
        rsi_level  = 'critical'
        irrigation = 'drip_only'
        avoid      = list(WATER_HEAVY)
        schemes    = ['PMKSY', 'PM-KUSUM', 'PMFBY']
    elif rsi < RSI_STRESSED or gw_dep > 12:
        rsi_level  = 'stressed'
        irrigation = 'drip_or_sprinkler_with_rwh'
        avoid      = ['rice', 'sugarcane']
        schemes    = ['PMKSY', 'MGNREGS', 'PMFBY']
    elif rsi < RSI_MODERATE:
        rsi_level  = 'moderate'
        irrigation = 'sprinkler_recommended'
        avoid      = ['sugarcane']
        schemes    = ['PMKSY', 'RKVY']
    else:
        rsi_level  = 'healthy'
        irrigation = 'conventional_acceptable'
        avoid      = []
        schemes    = ['RKVY', 'PMFBY']

    # Optimal sowing window: peak kharif rainfall month
    city_monthly = monthly_rain[monthly_rain['city'] == city]
    kharif_rain  = city_monthly[city_monthly['month'].between(6, 9)]
    if len(kharif_rain) > 0:
        peak_month = int(kharif_rain.loc[kharif_rain['avg_monthly_rain_mm'].idxmax(), 'month'])
        sow_window = f"Month {peak_month} (sow 2–3 weeks before peak rainfall)"
    else:
        sow_window = 'June–July (default kharif window)'

    rec_crops = [c['crop'] for c in advisory[city]['ranked_crops']
                 if c['crop'] not in avoid][:5]

    strategies[city] = {
        'rsi_level':            rsi_level,
        'recharge_efficiency':  round(rsi, 4),
        'gw_depth_mbgl':        round(gw_dep, 2),
        'depletion_rate':       round(depl, 4),
        'irrigation_method':    irrigation,
        'avoid_crops':          avoid,
        'recommended_crops':    rec_crops,
        'optimal_sow_window':   sow_window,
        'govt_schemes':         {k: GOVT_SCHEMES[k] for k in schemes},
    }

json.dump(strategies, open('data/output/irrigation_strategy.json', 'w'), indent=2)
print(f"Irrigation strategy saved for {len(strategies)} cities")
for city, s in strategies.items():
    print(f"  {city:<12} RSI={s['rsi_level']:<10} method={s['irrigation_method']}")