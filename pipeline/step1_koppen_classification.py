# pipeline/step1_koppen_classification.py
import pandas as pd
import numpy as np

df = pd.read_csv('data/processed/kaggle_climate.csv', parse_dates=['date'])
df['year']  = df['date'].dt.year
df['month'] = df['date'].dt.month

def classify_koppen(T_ann, P_ann, T_min, T_max, P_dry,
                    P_wet, P_sum, P_win):
    """
    Simplified Koppen-Geiger for Indian cities.
    T_ann : mean annual temperature (°C)
    P_ann : total annual precipitation (mm)
    T_min : mean temperature coldest month (°C)
    T_max : mean temperature hottest month (°C)
    P_dry : precipitation driest month (mm)
    P_wet : precipitation wettest month (mm)
    P_sum : total Apr–Sep precipitation (mm)
    P_win : total Oct–Mar precipitation (mm)
    """
    # Koppen aridity threshold (Pth in mm; formula is 20*(T+c), not 2*(T+c))
    if P_sum >= 0.7 * P_ann:
        Pth = 20 * T_ann + 280
    elif P_win >= 0.7 * P_ann:
        Pth = 20 * T_ann
    else:
        Pth = 20 * T_ann + 140

    # B — Arid / Semi-arid
    if P_ann < Pth:
        if P_ann < 0.5 * Pth:
            return 'BWh' if T_ann >= 18 else 'BWk'
        else:
            return 'BSh' if T_ann >= 18 else 'BSk'

    # A — Tropical
    if T_min >= 18:
        if P_dry >= 60:
            return 'Af'
        elif P_dry >= 100 - P_ann / 25:
            return 'Am'
        else:
            return 'Aw'

    # C — Temperate
    if T_min >= 0:
        if P_sum >= 10 * P_win and P_dry < 30:
            return 'Csa' if T_max >= 22 else 'Csb'
        elif P_win >= 10 * P_dry:
            return 'Cwa' if T_max >= 22 else 'Cwb'
        else:
            return 'Cfa' if T_max >= 22 else 'Cfb'

    return 'Unknown'

# Monthly aggregation
monthly = df.groupby(['city','year','month']).agg(
    temp_mean = ('temp_mean','mean'),
    rainfall  = ('rainfall','sum')
).reset_index()

records = []
for (city, year), ydf in monthly.groupby(['city','year']):
    T_ann = ydf['temp_mean'].mean()
    P_ann = ydf['rainfall'].sum()
    T_min = ydf['temp_mean'].min()
    T_max = ydf['temp_mean'].max()
    P_dry = ydf['rainfall'].min()
    P_wet = ydf['rainfall'].max()
    P_sum = ydf[ydf['month'].between(4,9)]['rainfall'].sum()
    P_win = ydf[~ydf['month'].between(4,9)]['rainfall'].sum()
    n_dry = int((ydf['rainfall'] < 60).sum())

    zone = classify_koppen(T_ann, P_ann, T_min, T_max,
                           P_dry, P_wet, P_sum, P_win)
    records.append(dict(city=city, year=year, koppen_zone=zone,
                        T_ann=round(T_ann,2), P_ann=round(P_ann,2),
                        T_min=round(T_min,2), T_max=round(T_max,2),
                        n_dry_months=n_dry))

koppen_df = pd.DataFrame(records)

# Encode zone as integer for model use
zone_categories = sorted(koppen_df['koppen_zone'].unique())
zone_map = {z: i for i, z in enumerate(zone_categories)}
koppen_df['koppen_zone_enc'] = koppen_df['koppen_zone'].map(zone_map)
import json
json.dump(zone_map, open('data/processed/zone_map.json','w'), indent=2)

koppen_df.to_csv('data/processed/koppen_annual.csv', index=False)
print(f"Koppen annual: {koppen_df.shape}")
print(f"Zones found: {zone_categories}")
