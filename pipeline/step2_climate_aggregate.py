# pipeline/step2_climate_aggregate.py
import pandas as pd, numpy as np

df = pd.read_csv('data/processed/kaggle_climate.csv', parse_dates=['date'])
df['year'] = df['date'].dt.year
df['doy']  = df['date'].dt.dayofyear

CROP_CONFIG = {
    'Delhi':     {'crop':'wheat',    'gdd_base':5,  'gdd_min':1200,'water_req':450, 'sow_doy':120,'max_temp':35},
    'Jaipur':    {'crop':'mustard',  'gdd_base':5,  'gdd_min':800, 'water_req':300, 'sow_doy':120,'max_temp':35},
    'Ahmedabad': {'crop':'cotton',   'gdd_base':15, 'gdd_min':1800,'water_req':700, 'sow_doy':152,'max_temp':40},
    'Lucknow':   {'crop':'sugarcane','gdd_base':10, 'gdd_min':2500,'water_req':1500,'sow_doy':90, 'max_temp':38},
    'Hyderabad': {'crop':'groundnut','gdd_base':10, 'gdd_min':1600,'water_req':500, 'sow_doy':152,'max_temp':40},
    'Chennai':   {'crop':'rice',     'gdd_base':10, 'gdd_min':2000,'water_req':1200,'sow_doy':152,'max_temp':38},
    'Bangalore': {'crop':'ragi',     'gdd_base':10, 'gdd_min':1400,'water_req':350, 'sow_doy':152,'max_temp':38},
    'Pune':      {'crop':'sorghum',  'gdd_base':10, 'gdd_min':1400,'water_req':400, 'sow_doy':152,'max_temp':40},
    'Kolkata':   {'crop':'rice',     'gdd_base':10, 'gdd_min':2000,'water_req':1200,'sow_doy':135,'max_temp':38},
    'Mumbai':    {'crop':'rice',     'gdd_base':10, 'gdd_min':2000,'water_req':1200,'sow_doy':152,'max_temp':38},
}

def monsoon_onset(city_df):
    """IMD: first 5-day window after doy 121 with >= 3 days of rain >= 2.5mm."""
    result = {}
    for year, ydf in city_df.groupby('year'):
        ydf   = ydf[ydf['doy'] >= 121].sort_values('doy').reset_index(drop=True)
        onset = np.nan
        for i in range(len(ydf) - 4):
            if (ydf.iloc[i:i+5]['rainfall'] >= 2.5).sum() >= 3:
                onset = ydf.iloc[i]['doy']
                break
        result[year] = onset
    return result

def compute_gdd(city_df, base):
    s = city_df[city_df['doy'].between(91,273)]
    return s.groupby('year').apply(
        lambda x: ((x['temp_mean'] - base).clip(lower=0)).sum()
    )

records = []
for city, cfg in CROP_CONFIG.items():
    cdf      = df[df['city'] == city].copy()
    onset_m  = monsoon_onset(cdf)
    gdd_m    = compute_gdd(cdf, cfg['gdd_base'])

    for year, ydf in cdf.groupby('year'):
        onset  = onset_m.get(year, np.nan)
        s_miss = np.nan
        if not np.isnan(onset):
            s_miss = min(max(0, onset - cfg['sow_doy']) / 30, 1.0)

        s_rain  = ydf[ydf['doy'].between(91,273)]['rainfall'].sum()
        deficit = min(max(0, (cfg['water_req'] - s_rain) / cfg['water_req']), 1.0)
        gdd     = float(gdd_m.get(year, np.nan))

        records.append({
            'city': city, 'year': year,
            'temp_mean':          round(ydf['temp_mean'].mean(), 3),
            'temp_max':           round(ydf['temp_max'].mean(), 3),
            'rainfall_annual':    round(ydf['rainfall'].sum(), 2),
            'wind_speed':         round(ydf['wind_speed'].mean(), 3),
            'humidity':           round(ydf['humidity'].mean(), 3),
            'n_dry_months':       int((ydf.groupby(ydf['date'].dt.month)['rainfall'].sum() < 60).sum()),
            'monsoon_onset_doy':  onset,
            'sowing_window_miss': round(s_miss, 4) if not np.isnan(s_miss) else np.nan,
            'gdd_accumulation':   round(gdd, 2) if not np.isnan(gdd) else np.nan,
            'crop_water_deficit': round(deficit, 4),
        })

out = pd.DataFrame(records)
out.to_csv('data/processed/climate_annual.csv', index=False)
print(f"climate_annual: {out.shape}")  # (250, 12)
