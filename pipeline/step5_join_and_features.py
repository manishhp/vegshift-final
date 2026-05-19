# pipeline/step5_join_and_features.py
import pandas as pd, numpy as np, json

master      = pd.read_csv('data/processed/master_index.csv')
climate     = pd.read_csv('data/processed/climate_annual.csv')
groundwater = pd.read_csv('data/processed/groundwater_annual.csv')
gaez        = pd.read_csv('data/processed/gaez_baseline.csv')
koppen      = pd.read_csv('data/processed/koppen_annual.csv')[
                  ['city','year','koppen_zone','koppen_zone_enc']]
zone_map    = json.load(open('data/processed/zone_map.json'))

# Three-way join onto master
df = master.merge(climate,     on=['city','year'], how='left')
df = df.merge(groundwater[['city','year','pre_monsoon_depth_mbgl',
                            'post_monsoon_depth_mbgl','depletion_rate',
                            'recharge_efficiency','gw_imputed']],
              on=['city','year'], how='left')
df = df.merge(gaez,   on='city',          how='left')   # static broadcast
df = df.merge(koppen, on=['city','year'],  how='left')   # koppen per year

# Impute missing GW values with city group mean; fall back to global median
# for cities where all values are NaN (e.g. Kolkata has no May readings in CGWB)
for col in ['pre_monsoon_depth_mbgl','post_monsoon_depth_mbgl',
            'depletion_rate','recharge_efficiency']:
    df[col] = df.groupby('city')[col].transform(lambda x: x.fillna(x.mean()))
    global_median = df[col].median()
    df[col] = df[col].fillna(global_median)

# gw_imputed: 0=measured, 1=pre-2005 backfill, 2=nearest-well proxy
# Years 2023-2024 have no CGWB readings (dataset ends 2022); mark as imputed
df['gw_imputed'] = df['gw_imputed'].fillna(1).astype(int)

# Also impute monsoon_onset and sowing_window_miss
for col in ['monsoon_onset_doy','sowing_window_miss','gdd_accumulation']:
    df[col] = df.groupby('city')[col].transform(lambda x: x.fillna(x.mean()))

# Dual-deficit: atmospheric AND subsurface failure simultaneously
df['dual_deficit'] = (
    (df['crop_water_deficit'] > 0.4) &
    (df['recharge_efficiency'] < 0.30)
).astype(int)

# GDD adequacy
df['gdd_adequate'] = (df['gdd_accumulation'] >= df['gdd_min']).astype(int)

# CVLE = 1 when:
#   (a) dual_deficit active for 2+ consecutive years AND
#   (b) at least 2 of 3 thresholds breached:
#       T1: sowing_window_miss > 0.6
#       T2: crop_water_deficit > 0.4
#       T3: gdd_adequate == 0

def compute_cvle(group):
    group = group.sort_values('year').reset_index(drop=True).copy()
    cvle  = [0] * len(group)
    for i in range(1, len(group)):
        consec = (group.loc[i,  'dual_deficit'] == 1 and
                  group.loc[i-1,'dual_deficit'] == 1)
        t1 = int(group.loc[i,'sowing_window_miss'] > 0.6)
        t2 = int(group.loc[i,'crop_water_deficit'] > 0.4)
        t3 = int(group.loc[i,'gdd_adequate'] == 0)
        if consec and (t1 + t2 + t3) >= 2:
            cvle[i] = 1
    group['cvle_label'] = cvle
    return group

# pandas 3 may exclude group keys from groupby-apply results; keep city explicitly.
parts = []
for city, group in df.groupby('city', sort=False):
    group = group.copy()
    group['city'] = city
    parts.append(compute_cvle(group))
df = pd.concat(parts, ignore_index=True)

df.to_csv('data/processed/vegshift_master.csv', index=False)
print(f"vegshift_master: {df.shape}")
print(f"\nCVLE count per city:\n{df.groupby('city')['cvle_label'].sum().sort_values(ascending=False)}")
print(f"\nSample Koppen encoding:\n{df[['city','year','koppen_zone','koppen_zone_enc']].head(10)}")
