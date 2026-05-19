# VegShift Modify Scaffold

This workspace is the lightweight integration layer on top of the original VegShift project.

Rules for this folder:
- Keep changes focused on the upgrade path: TFT climate forecasting, forecast-to-DSSAT bridging, and `pyDSSAT` execution.
- Prefer small runnable scripts over large monoliths.
- Keep heavy dependencies optional where possible so the repo remains easy to clone, inspect, and extend.
- Use `run_vegshift.py` as the entry point for orchestration.

Suggested workflow:
1. Generate the master city-year index.
2. Standardize climate inputs.
3. Train or stub the TFT climate forecaster.
4. Export weather forecasts to DSSAT format.
5. Run DSSAT through `pyDSSAT` and feed outputs back into the decision layer.
# VegShift — agents.md
## Vegetation Viability Loss Detection After Climate Zone Transitions in Indian Cities
### Complete Standalone Pipeline — Data → Transitions → Features → Model → Dashboard

---

## 1. Project Overview

VegShift is a standalone pipeline that answers one question: **after a city's climate zone shifts, which crops can no longer be grown there, and when exactly did that become true?**

It operates in five stages:
1. **Acquire and fuse** three datasets into one master tabular dataset
2. **Detect climate zone transitions** using Koppen-Geiger classification over 25 years
3. **Engineer crop viability features** using atmospheric + groundwater layers
4. **Predict and explain** Crop Viability Loss Events using a Temporal Fusion Transformer
5. **Visualize** all outputs in an interactive dashboard

The central output is a **Crop Viability Loss Event (CVLE):** a formally timestamped event marking the year a city's climate permanently crossed below the minimum threshold for its primary crop, with groundwater state recorded as context.

**Cities:** Delhi, Mumbai, Chennai, Kolkata, Bangalore, Hyderabad, Ahmedabad, Jaipur, Lucknow, Pune
**Time range:** 2000–2024 (25 years)
**Control cities:** Pune, Kolkata, Mumbai — expected stable viability, used to validate the model is not detecting noise

---

## 2. Datasets

### Dataset 1 — Kaggle Historical Climate Dataset
**Role:** Primary atmospheric layer.
**Raw file:** `data/raw/climate/india_2000_2024_daily_weather.csv`
**Pipeline file:** `data/processed/kaggle_climate.csv` (standardized by `pipeline/step0b_preprocess_datasets.py`)
**Contains:** Daily temperature (max, min, mean), rainfall, wind speed, humidity for 10 Indian cities, 2000–2024.
**Used for:** Koppen classification, monsoon onset, Growing Degree Days, crop water deficit, core climate features.
**Format:** CSV, one row per city per day.

**Preprocessing applied (`step0b`):**
| Pipeline column | Source column | Transformation |
|---|---|---|
| `temp_max` | `temperature_2m_max` | rename |
| `temp_min` | `temperature_2m_min` | rename |
| `temp_mean` | — | `(temp_max + temp_min) / 2` |
| `rainfall` | `precipitation_sum` | rename |
| `wind_speed` | `wind_speed_10m_max` | km/h ÷ 3.6 → m/s |
| `humidity` | — | derived via Steadman apparent-temperature inversion (see below) |

**Humidity derivation** — the source dataset has no humidity column. Estimated from apparent temperature:
```
e  = (AT_mean - T_mean + 0.70 * wind_ms + 4.00) / 0.33
es = 6.1078 * exp(17.27 * T_mean / (237.3 + T_mean))
RH = clip((e / es) * 100, 5, 100)
```
Validated against climatological means: Mumbai 90%, Chennai 88%, Delhi 74%, Jaipur 65% — all geographically consistent.

---

### Dataset 2 — CGWB Quality-Controlled Groundwater Levels
**Full name:** Quality Controlled, Reliable Groundwater Level Data with Corresponding Specific Yield over India (2000–2022)
**Source:** Scientific Data (Nature), October 2025
**Paper:** `https://www.nature.com/articles/s41597-025-05899-5`
**Downloaded from:** Figshare DOI 10.6084/m9.figshare.29293877.v3
**File:** `data/raw/cgwb/CGWB_India_quality_controlled_GWLs_ref_sy_2000_2022.csv`

**Contains:**
- 2,759 quality-controlled observation wells across India
- Seasonal groundwater levels (metres below ground level, mbgl): January, May, August, November from 2000–2022
- Columns: Station Code, State, District, Latitude, Longitude, Aquifer Type, Well Depth, then `Jan-00`, `May-00`, `Aug-00`, `Nov-00` … `Nov-22`
- Specific yield (Sy) per well from hydrogeological maps
- Higher mbgl = water table deeper = worse depletion

**Known gap — Jaipur:** Rajasthan state is entirely absent from this dataset. The nearest well to Jaipur is 130 km away in Haryana. Step 3 handles this with a nearest-well fallback (5 closest wells regardless of distance) and flags all Jaipur groundwater rows as `gw_imputed = 2`.

**Well coverage at 50 km radius:**
| City | Wells | City | Wells |
|---|---|---|---|
| Lucknow | 18 | Chennai | 5 |
| Mumbai | 14 | Kolkata | 3 |
| Delhi | 12 | Ahmedabad | 3 |
| Pune | 10 | **Jaipur** | **0 → nearest-well fallback** |
| Hyderabad | 9 | Bangalore | 7 |

---

### Dataset 3 — FAO GAEZ v4 Crop Suitability Index
**Source:** FAO and IIASA
**Downloaded from:** FAO S3 bucket (`s3://data.gaezdev.aws.fao.org/res05/CRUTS32/Hist/8110H/`)
**Files:** `data/raw/gaez/*.tif` (rainfed, high input, 1981–2010 historical baseline)

**Contains:**
- Crop suitability index for 53 crops, ~9 km resolution GeoTIFF rasters
- ECOCROP: per-crop minimum GDD, seasonal water requirement, temperature limits, sowing window

**GeoTIFF files (renamed from FAO S3 naming `scHr_{crop}.tif`):**
- `whe_suit_class_r_hist_cruts32_7clim.tif` — wheat
- `cot_suit_class_r_hist_cruts32_7clim.tif` — cotton
- `rcw_suit_class_r_hist_cruts32_7clim.tif` — wetland rice
- `suc_suit_class_r_hist_cruts32_7clim.tif` — sugarcane
- `srg_suit_class_r_hist_cruts32_7clim.tif` — sorghum
- `pig_suit_class_r_hist_cruts32_7clim.tif` — groundnut

**Known encoding issue:** The TIFFs use uint8 with observed values `[1–6, 8–10]`; value 7 is absent and values 8–10 appear to encode irrigated-potential categories beyond the standard 1–7 rainfed scale. Step 4 clips extracted values to max 7. Only Lucknow sugarcane is affected (raw=8 → clipped=7, correctly reflecting that Lucknow is a major sugarcane belt).

**How used:** GAEZ provides the baseline suitability class per city per crop. ECOCROP provides threshold constants (GDD min, water requirement, max temperature) used as reference values in feature engineering — not model inputs but thresholds against which observed data is tested.

---

## 3. Crops Tracked Per City

| City | Primary Crop | Koppen Zone (2000) | Transition Risk | Role |
|------|-------------|-------------------|-----------------|------|
| Delhi | Wheat | BSh (Semi-arid) | → BWh (Arid); sowing window narrowing | At-risk |
| Jaipur | Mustard | BWh (Arid) | → BWk (Hyper-arid); dual deficit | At-risk |
| Ahmedabad | Cotton | BSh (Semi-arid) | → BWh (Arid); heat stress | At-risk |
| Lucknow | Sugarcane | Cwa (Humid subtropical) | → BSh; water deficit rising | At-risk |
| Hyderabad | Groundnut | BSh (Semi-arid) | → BWh (Arid); rain dependency | At-risk |
| Chennai | Rice | Aw (Tropical savanna) | → BSh; monsoon delay | At-risk |
| Bangalore | Ragi | Aw (Tropical savanna) | → BSh; GDD impact | At-risk |
| Pune | Sorghum | BSh (Semi-arid) | Stable | **Control** |
| Kolkata | Rice / Jute | Am (Tropical monsoon) | Stable | **Control** |
| Mumbai | Rice | Am (Tropical monsoon) | Stable | **Control** |

---

## 4. Full Pipeline Implementation

### Step 0 — Master Index

```python
# pipeline/step0_master_index.py
import pandas as pd, itertools

cities = [
    'Delhi','Mumbai','Chennai','Kolkata','Bangalore',
    'Hyderabad','Ahmedabad','Jaipur','Lucknow','Pune'
]
years = list(range(2000, 2025))

master = pd.DataFrame(
    list(itertools.product(cities, years)),
    columns=['city','year']
)
master.to_csv('data/master_index.csv', index=False)
print(f"Master index: {master.shape}")  # (250, 2)
```

---

### Step 1 — Koppen-Geiger Climate Zone Classification

```python
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
```

---

### Step 1b — Transition Detection

```python
# pipeline/step1b_transition_detection.py
import pandas as pd, json

koppen = pd.read_csv('data/processed/koppen_annual.csv').sort_values(['city','year'])

PERSISTENCE = 3   # new zone must persist 3+ years

transitions = []

for city, cdf in koppen.groupby('city'):
    cdf   = cdf.sort_values('year').reset_index(drop=True)
    zones = cdf['koppen_zone'].tolist()
    years = cdf['year'].tolist()

    i = 0
    while i < len(zones) - 1:
        if zones[i] != zones[i+1]:
            end_chk = min(i + 1 + PERSISTENCE, len(zones))
            future  = zones[i+1:end_chk]
            if all(z == zones[i+1] for z in future):
                transitions.append({
                    'city':             city,
                    'transition_year':  years[i+1],
                    'from_zone':        zones[i],
                    'to_zone':          zones[i+1],
                    'years_confirmed':  len(future)
                })
                i += PERSISTENCE
            else:
                i += 1
        else:
            i += 1

json.dump(transitions, open('data/output/transition_report.json','w'), indent=2)

print(f"\nTransitions detected: {len(transitions)}")
for t in transitions:
    print(f"  {t['city']} {t['transition_year']}: "
          f"{t['from_zone']} → {t['to_zone']} "
          f"(confirmed {t['years_confirmed']} yrs)")
```

---

### Step 2 — Climate Feature Aggregation

```python
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
```

---

### Step 3 — Groundwater Aggregation

```python
# pipeline/step3_groundwater_aggregate.py
import pandas as pd, numpy as np
from math import radians, cos, sin, asin, sqrt

CITY_COORDS = {
    'Delhi':     (28.6139, 77.2090), 'Bangalore': (12.9716, 77.5946),
    'Chennai':   (13.0827, 80.2707), 'Hyderabad': (17.3850, 78.4867),
    'Ahmedabad': (23.0225, 72.5714), 'Jaipur':    (26.9124, 75.7873),
    'Lucknow':   (26.8467, 80.9462), 'Mumbai':    (19.0760, 72.8777),
    'Pune':      (18.5204, 73.8567), 'Kolkata':   (22.5726, 88.3639),
}
RADIUS_KM = 50

def haversine(la1, lo1, la2, lo2):
    R = 6371
    la1,lo1,la2,lo2 = map(radians,[la1,lo1,la2,lo2])
    a = sin((la2-la1)/2)**2 + cos(la1)*cos(la2)*sin((lo2-lo1)/2)**2
    return R * 2 * asin(sqrt(a))

cgwb = pd.read_csv(
    'data/raw/cgwb/CGWB_India_quality_controlled_GWLs_ref_sy_2000_2022.csv'
)

records = []
for city, (clat, clon) in CITY_COORDS.items():
    cgwb['dist_km'] = cgwb.apply(
        lambda r: haversine(clat, clon, r['Latitude'], r['Longitude']), axis=1
    )
    nearby = cgwb[cgwb['dist_km'] <= RADIUS_KM]

    # Jaipur fallback: Rajasthan absent from dataset; use 5 nearest wells
    jaipur_fallback = False
    if len(nearby) == 0:
        nearby = cgwb.nsmallest(5, 'dist_km')
        jaipur_fallback = True
        print(f"WARNING: No wells within {RADIUS_KM}km of {city} — using {len(nearby)} nearest wells")

    for year in range(2000, 2023):
        yr2     = str(year)[2:].zfill(2)
        may_col = f'May-{yr2}'
        nov_col = f'Nov-{yr2}'
        pre  = nearby[may_col].median() if may_col in nearby.columns else np.nan
        post = nearby[nov_col].median() if nov_col in nearby.columns else np.nan
        records.append({'city': city, 'year': year,
                        'pre_monsoon_depth_mbgl':  round(pre,3)  if not np.isnan(pre)  else np.nan,
                        'post_monsoon_depth_mbgl': round(post,3) if not np.isnan(post) else np.nan,
                        'n_wells': len(nearby),
                        'jaipur_fallback': int(jaipur_fallback)})

gw = pd.DataFrame(records).sort_values(['city','year']).reset_index(drop=True)
gw['depletion_rate'] = gw.groupby('city')['pre_monsoon_depth_mbgl'].diff()

climate = pd.read_csv('data/processed/climate_annual.csv')[['city','year','rainfall_annual']]
gw = gw.merge(climate, on=['city','year'], how='left')
gw['depth_recovery']      = gw['pre_monsoon_depth_mbgl'] - gw['post_monsoon_depth_mbgl']
gw['recharge_efficiency'] = (gw['depth_recovery'] / gw['rainfall_annual']).clip(0, 1).round(4)
gw['gw_imputed'] = (gw['year'] < 2005).astype(int)
gw.loc[gw['jaipur_fallback'] == 1, 'gw_imputed'] = 2  # nearest-well proxy, not 50km radius
gw = gw.drop(columns=['jaipur_fallback'])

# Backfill pre-2005 depletion_rate
for city in gw['city'].unique():
    base = gw[(gw['city'] == city) & gw['year'].between(2005,2007)]['depletion_rate'].mean()
    mask = (gw['city'] == city) & (gw['year'] < 2005)
    gw.loc[mask, 'depletion_rate'] = gw.loc[mask, 'depletion_rate'].fillna(base)

gw = gw.drop(columns=['rainfall_annual','depth_recovery'])
gw.to_csv('data/processed/groundwater_annual.csv', index=False)
print(f"groundwater_annual: {gw.shape}")
```

---

### Step 4 — FAO GAEZ Extraction

```python
# pipeline/step4_gaez_extract.py
import rasterio, pandas as pd

CITY_COORDS = {
    'Delhi':     (28.6139, 77.2090), 'Bangalore': (12.9716, 77.5946),
    'Chennai':   (13.0827, 80.2707), 'Hyderabad': (17.3850, 78.4867),
    'Ahmedabad': (23.0225, 72.5714), 'Jaipur':    (26.9124, 75.7873),
    'Lucknow':   (26.8467, 80.9462), 'Mumbai':    (19.0760, 72.8777),
    'Pune':      (18.5204, 73.8567), 'Kolkata':   (22.5726, 88.3639),
}
CROP_RASTERS = {
    'Delhi':     'data/raw/gaez/whe_suit_class_r_hist_cruts32_7clim.tif',
    'Jaipur':    'data/raw/gaez/whe_suit_class_r_hist_cruts32_7clim.tif',
    'Ahmedabad': 'data/raw/gaez/cot_suit_class_r_hist_cruts32_7clim.tif',
    'Lucknow':   'data/raw/gaez/suc_suit_class_r_hist_cruts32_7clim.tif',
    'Hyderabad': 'data/raw/gaez/pig_suit_class_r_hist_cruts32_7clim.tif',
    'Chennai':   'data/raw/gaez/rcw_suit_class_r_hist_cruts32_7clim.tif',
    'Bangalore': 'data/raw/gaez/srg_suit_class_r_hist_cruts32_7clim.tif',
    'Pune':      'data/raw/gaez/srg_suit_class_r_hist_cruts32_7clim.tif',
    'Kolkata':   'data/raw/gaez/rcw_suit_class_r_hist_cruts32_7clim.tif',
    'Mumbai':    'data/raw/gaez/rcw_suit_class_r_hist_cruts32_7clim.tif',
}
ECOCROP = {
    'Delhi':     {'crop':'wheat',    'gdd_min':1200,'water_req':450, 'sow_doy':120,'max_temp':35},
    'Jaipur':    {'crop':'mustard',  'gdd_min':800, 'water_req':300, 'sow_doy':120,'max_temp':35},
    'Ahmedabad': {'crop':'cotton',   'gdd_min':1800,'water_req':700, 'sow_doy':152,'max_temp':40},
    'Lucknow':   {'crop':'sugarcane','gdd_min':2500,'water_req':1500,'sow_doy':90, 'max_temp':38},
    'Hyderabad': {'crop':'groundnut','gdd_min':1600,'water_req':500, 'sow_doy':152,'max_temp':40},
    'Chennai':   {'crop':'rice',     'gdd_min':2000,'water_req':1200,'sow_doy':152,'max_temp':38},
    'Bangalore': {'crop':'ragi',     'gdd_min':1400,'water_req':350, 'sow_doy':152,'max_temp':38},
    'Pune':      {'crop':'sorghum',  'gdd_min':1400,'water_req':400, 'sow_doy':152,'max_temp':40},
    'Kolkata':   {'crop':'rice',     'gdd_min':2000,'water_req':1200,'sow_doy':135,'max_temp':38},
    'Mumbai':    {'crop':'rice',     'gdd_min':2000,'water_req':1200,'sow_doy':152,'max_temp':38},
}

records = []
for city, (lat, lon) in CITY_COORDS.items():
    with rasterio.open(CROP_RASTERS[city]) as src:
        row, col   = src.index(lon, lat)
        suit_class = int(src.read(1)[row, col])
    # TIFFs use values 1–10 (8–10 = irrigated-potential categories); clip to 1–7 rainfed scale
    suit_class = min(suit_class, 7)
    rec = {'city': city, 'gaez_baseline_class': suit_class}
    rec.update(ECOCROP[city])
    records.append(rec)

gaez = pd.DataFrame(records)
gaez.to_csv('data/processed/gaez_baseline.csv', index=False)
print(gaez[['city','crop','gaez_baseline_class','gdd_min','water_req']])
```

---

### Step 5 — Three-Way Join, Koppen Encoding, and CVLE Label Engineering

```python
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

# Impute missing GW values with city group mean
for col in ['pre_monsoon_depth_mbgl','post_monsoon_depth_mbgl',
            'depletion_rate','recharge_efficiency']:
    df[col] = df.groupby('city')[col].transform(lambda x: x.fillna(x.mean()))

# Also impute monsoon_onset and sowing_window_miss
for col in ['monsoon_onset_doy','sowing_window_miss','gdd_accumulation']:
    df[col] = df.groupby('city')[col].transform(lambda x: x.fillna(x.mean()))

# ── Compound features ─────────────────────────────────────────────────────────
# Dual-deficit: atmospheric AND subsurface failure simultaneously
df['dual_deficit'] = (
    (df['crop_water_deficit'] > 0.4) &
    (df['recharge_efficiency'] < 0.30)
).astype(int)

# GDD adequacy
df['gdd_adequate'] = (df['gdd_accumulation'] >= df['gdd_min']).astype(int)

# ── CVLE Label ────────────────────────────────────────────────────────────────
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

df = df.groupby('city', group_keys=False).apply(compute_cvle)

df.to_csv('data/processed/vegshift_master.csv', index=False)
print(f"vegshift_master: {df.shape}")
print(f"\nCVLE count per city:\n{df.groupby('city')['cvle_label'].sum().sort_values(ascending=False)}")
print(f"\nSample Koppen encoding:\n{df[['city','year','koppen_zone','koppen_zone_enc']].head(10)}")
```

---

### Step 6 — TFT Model Training

```python
# pipeline/step6_tft_train.py
import pandas as pd, numpy as np, torch
from pytorch_forecasting import TemporalFusionTransformer, TimeSeriesDataSet
from pytorch_forecasting.data import GroupNormalizer
from pytorch_forecasting.metrics import QuantileLoss
from pytorch_lightning import Trainer
from pytorch_lightning.callbacks import EarlyStopping, ModelCheckpoint

df = pd.read_csv('data/processed/vegshift_master.csv')
df = df.sort_values(['city','year']).reset_index(drop=True)
df['time_idx']        = df.groupby('city').cumcount()
df['city']            = df['city'].astype(str)
df['crop']            = df['crop'].astype(str)
df['koppen_zone']     = df['koppen_zone'].astype(str)
df['koppen_zone_enc'] = df['koppen_zone_enc'].astype(float)

# Fill remaining NaNs
num_cols = ['pre_monsoon_depth_mbgl','post_monsoon_depth_mbgl','depletion_rate',
            'recharge_efficiency','monsoon_onset_doy','sowing_window_miss','gdd_accumulation']
for col in num_cols:
    df[col] = df.groupby('city')[col].transform(lambda x: x.fillna(x.mean()))

# Feature groups
TIME_VARYING_KNOWN = [
    # Atmospheric
    'temp_mean','temp_max','rainfall_annual','wind_speed','humidity','n_dry_months',
    'monsoon_onset_doy','sowing_window_miss','gdd_accumulation','crop_water_deficit',
    # Groundwater
    'pre_monsoon_depth_mbgl','depletion_rate','recharge_efficiency',
    # Compound
    'dual_deficit','gdd_adequate',
    # Koppen encoded (changes year to year)
    'koppen_zone_enc',
]
TIME_VARYING_CATS = ['koppen_zone']   # string categorical version
STATIC_CATS       = ['city','crop']
STATIC_REALS      = ['gaez_baseline_class','gdd_min','water_req','sow_doy','max_temp']

MAX_ENCODER = 5
MAX_PRED    = 1

train_df = df[df['time_idx'] <= 18]   # 2000–2018
val_df   = df[df['time_idx'] <= 21]   # 2000–2021

training = TimeSeriesDataSet(
    train_df,
    time_idx                    = 'time_idx',
    target                      = 'cvle_label',
    group_ids                   = ['city'],
    min_encoder_length          = MAX_ENCODER // 2,
    max_encoder_length          = MAX_ENCODER,
    min_prediction_length       = 1,
    max_prediction_length       = MAX_PRED,
    static_categoricals         = STATIC_CATS,
    static_reals                = STATIC_REALS,
    time_varying_known_categoricals = TIME_VARYING_CATS,
    time_varying_known_reals    = TIME_VARYING_KNOWN,
    time_varying_unknown_reals  = ['cvle_label'],
    target_normalizer           = GroupNormalizer(
                                    groups=['city'], transformation='softplus'),
    add_relative_time_idx       = True,
    add_target_scales           = True,
    add_encoder_length          = True,
)

validation   = TimeSeriesDataSet.from_dataset(
    training, val_df, predict=True, stop_randomization=True)

train_loader = training.to_dataloader(train=True,  batch_size=16, num_workers=0)
val_loader   = validation.to_dataloader(train=False, batch_size=16, num_workers=0)

tft = TemporalFusionTransformer.from_dataset(
    training,
    learning_rate              = 1e-3,
    hidden_size                = 64,
    attention_head_size        = 4,
    dropout                    = 0.1,
    hidden_continuous_size     = 32,
    output_size                = 7,
    loss                       = QuantileLoss(),
    log_interval               = 10,
    reduce_on_plateau_patience = 4,
)
print(f"TFT parameters: {tft.size()/1e3:.1f}k")

trainer = Trainer(
    max_epochs        = 50,
    accelerator       = 'auto',
    gradient_clip_val = 0.1,
    callbacks         = [
        EarlyStopping(monitor='val_loss', patience=5, mode='min'),
        ModelCheckpoint(dirpath='models/tft/', filename='vegshift-tft-best',
                        monitor='val_loss', save_top_k=1, mode='min'),
    ],
)
trainer.fit(tft, train_dataloaders=train_loader, val_dataloaders=val_loader)
print("TFT training complete.")
```

---

### Step 7 — TFT Prediction and Attention Extraction

```python
# pipeline/step7_tft_predict.py
import json, numpy as np, pandas as pd
from pytorch_forecasting import TemporalFusionTransformer, TimeSeriesDataSet
from pytorch_forecasting.data import GroupNormalizer
from pytorch_forecasting.metrics import QuantileLoss

# Load best checkpoint
best_model = TemporalFusionTransformer.load_from_checkpoint(
    'models/tft/vegshift-tft-best.ckpt'
)
best_model.eval()

df = pd.read_csv('data/processed/vegshift_master.csv')
df = df.sort_values(['city','year']).reset_index(drop=True)
df['time_idx']        = df.groupby('city').cumcount()
df['city']            = df['city'].astype(str)
df['crop']            = df['crop'].astype(str)
df['koppen_zone']     = df['koppen_zone'].astype(str)
df['koppen_zone_enc'] = df['koppen_zone_enc'].astype(float)

num_cols = ['pre_monsoon_depth_mbgl','post_monsoon_depth_mbgl','depletion_rate',
            'recharge_efficiency','monsoon_onset_doy','sowing_window_miss','gdd_accumulation']
for col in num_cols:
    df[col] = df.groupby('city')[col].transform(lambda x: x.fillna(x.mean()))

# Rebuild val dataset (time_idx <= 21) — same config as step6
# (TimeSeriesDataSet re-constructed identically — omitted for brevity)
# raw_preds, x = best_model.predict(val_loader, mode='raw', return_x=True)

# ── Attach predicted CVLE probability to all rows ─────────────────────────────
# preds_median: shape (n_samples, 1) — median quantile (index 3 of 7)
# Attach back to df by city + time_idx alignment

# ── Attention weights — which past years did model attend to? ─────────────────
# interpretation = best_model.interpret_output(raw_preds, reduction='sum')
# attention = interpretation['attention']  # (n_samples, encoder_len=5)

attention_out = {}
cities = df['city'].unique().tolist()
# For each city, average attention over all prediction windows
for city in cities:
    # attention_out[city] = avg_attention_for_city (list of 5 floats, sum=1)
    attention_out[city] = [0.05, 0.10, 0.20, 0.30, 0.35]  # placeholder; replace with actual

json.dump(attention_out, open('data/output/tft_attention_weights.json','w'), indent=2)

# ── CVLE event export ─────────────────────────────────────────────────────────
cvle_events = df[df['cvle_label'] == 1][[
    'city','year','crop','koppen_zone','dual_deficit',
    'sowing_window_miss','crop_water_deficit',
    'gdd_adequate','depletion_rate','recharge_efficiency'
]].copy()
cvle_events.to_json('data/output/crop_viability_events.json',
                     orient='records', indent=2)

print(f"CVLE events: {len(cvle_events)}")
print(f"Attention weights saved for {len(attention_out)} cities")
```

---

### Step 8 — Baseline Models (RF, LR, LSTM)

```python
# pipeline/step8_baselines.py
import pandas as pd, numpy as np, joblib, json
import torch, torch.nn as nn
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.preprocessing import StandardScaler

df = pd.read_csv('data/processed/vegshift_master.csv').dropna()

FEATURES = [
    'temp_mean','temp_max','rainfall_annual','wind_speed','humidity','n_dry_months',
    'monsoon_onset_doy','sowing_window_miss','gdd_accumulation','crop_water_deficit',
    'pre_monsoon_depth_mbgl','depletion_rate','recharge_efficiency',
    'dual_deficit','gdd_adequate','gaez_baseline_class','koppen_zone_enc'
]

X, y = df[FEATURES], df['cvle_label']
train_mask = df['year'] <= 2018
test_mask  = df['year'] >= 2022

scaler    = StandardScaler()
X_tr      = scaler.fit_transform(X[train_mask])
X_te      = scaler.transform(X[test_mask])
y_tr, y_te = y[train_mask], y[test_mask]

# ── Random Forest ─────────────────────────────────────────────────────────────
rf = RandomForestClassifier(n_estimators=200, max_depth=6,
                             class_weight='balanced', random_state=42)
rf.fit(X_tr, y_tr)
rf_preds = rf.predict(X_te)
print("=== Random Forest ===")
print(classification_report(y_te, rf_preds))
print(f"AUC: {roc_auc_score(y_te, rf.predict_proba(X_te)[:,1]):.3f}")

# ── Logistic Regression ───────────────────────────────────────────────────────
lr = LogisticRegression(class_weight='balanced', max_iter=1000)
lr.fit(X_tr, y_tr)
print("=== Logistic Regression ===")
print(classification_report(y_te, lr.predict(X_te)))
print(f"AUC: {roc_auc_score(y_te, lr.predict_proba(X_te)[:,1]):.3f}")

# ── LSTM Baseline ─────────────────────────────────────────────────────────────
SEQ_LEN = 5

def make_sequences(X_arr, y_arr, city_arr, seq_len=SEQ_LEN):
    """Build (seq_len, n_features) sequences per city preserving temporal order."""
    Xs, ys = [], []
    for city in np.unique(city_arr):
        idx  = np.where(city_arr == city)[0]
        Xc   = X_arr[idx]
        yc   = y_arr.iloc[idx].values if hasattr(y_arr,'iloc') else y_arr[idx]
        for i in range(seq_len, len(Xc)):
            Xs.append(Xc[i-seq_len:i])
            ys.append(yc[i])
    return np.array(Xs, dtype=np.float32), np.array(ys, dtype=np.float32)

X_all  = scaler.transform(X)
y_all  = y.values
c_all  = df['city'].values

X_seq, y_seq = make_sequences(X_all, y_all, c_all)
n_tr         = int(0.75 * len(X_seq))
X_seq_tr, y_seq_tr = X_seq[:n_tr], y_seq[:n_tr]
X_seq_te, y_seq_te = X_seq[n_tr:], y_seq[n_tr:]

class LSTMClassifier(nn.Module):
    def __init__(self, n_feat, hidden=64, layers=2, drop=0.2):
        super().__init__()
        self.lstm = nn.LSTM(n_feat, hidden, layers,
                            batch_first=True, dropout=drop)
        self.fc   = nn.Linear(hidden, 1)

    def forward(self, x):
        _, (h, _) = self.lstm(x)
        return torch.sigmoid(self.fc(h[-1])).squeeze()

n_feat = X_seq.shape[2]
lstm   = LSTMClassifier(n_feat)
opt    = torch.optim.Adam(lstm.parameters(), lr=1e-3)
loss_fn= nn.BCELoss()

Xt = torch.tensor(X_seq_tr)
yt = torch.tensor(y_seq_tr)

lstm.train()
for epoch in range(30):
    opt.zero_grad()
    pred  = lstm(Xt)
    loss  = loss_fn(pred, yt)
    loss.backward()
    opt.step()
    if (epoch+1) % 10 == 0:
        print(f"LSTM Epoch {epoch+1}/30 — Loss: {loss.item():.4f}")

lstm.eval()
with torch.no_grad():
    Xte_t    = torch.tensor(X_seq_te)
    lstm_prob = lstm(Xte_t).numpy()
    lstm_pred = (lstm_prob >= 0.5).astype(int)

print("=== LSTM Baseline ===")
print(classification_report(y_seq_te.astype(int), lstm_pred))
print(f"AUC: {roc_auc_score(y_seq_te, lstm_prob):.3f}")

# Save all
joblib.dump(rf,     'models/baselines/rf_baseline.pkl')
joblib.dump(lr,     'models/baselines/lr_baseline.pkl')
joblib.dump(scaler, 'models/baselines/scaler.pkl')
torch.save(lstm.state_dict(), 'models/baselines/lstm_baseline.pt')
print("All baseline models saved.")
```

---

### Step 9 — SHAP Explainability on Random Forest

```python
# pipeline/step9_shap_explainability.py
import shap, json, pandas as pd, numpy as np, joblib

df     = pd.read_csv('data/processed/vegshift_master.csv').dropna()
rf     = joblib.load('models/baselines/rf_baseline.pkl')
scaler = joblib.load('models/baselines/scaler.pkl')

FEATURES = [
    'temp_mean','temp_max','rainfall_annual','wind_speed','humidity','n_dry_months',
    'monsoon_onset_doy','sowing_window_miss','gdd_accumulation','crop_water_deficit',
    'pre_monsoon_depth_mbgl','depletion_rate','recharge_efficiency',
    'dual_deficit','gdd_adequate','gaez_baseline_class','koppen_zone_enc'
]

X      = scaler.transform(df[FEATURES])
explainer   = shap.TreeExplainer(rf)
shap_values = explainer.shap_values(X)  # shape: (n_samples, n_features, 2)

# SHAP values for class 1 (CVLE)
sv = shap_values[1] if isinstance(shap_values, list) else shap_values

shap_df = pd.DataFrame(sv, columns=FEATURES)
shap_df['city'] = df['city'].values
shap_df['year'] = df['year'].values

# Global feature importance (mean absolute SHAP)
global_imp = pd.DataFrame({
    'feature':    FEATURES,
    'mean_abs_shap': np.abs(sv).mean(axis=0)
}).sort_values('mean_abs_shap', ascending=False)

print("=== Global SHAP Feature Importance ===")
print(global_imp.to_string(index=False))

# Per-city top features
city_shap = {}
for city, cdf in shap_df.groupby('city'):
    top = pd.Series(
        np.abs(cdf[FEATURES].values).mean(axis=0),
        index=FEATURES
    ).sort_values(ascending=False).head(5)
    city_shap[city] = top.to_dict()

output = {
    'global_importance': global_imp.to_dict(orient='records'),
    'city_importance':   city_shap
}
json.dump(output, open('data/output/shap_explanation.json','w'), indent=2)
print("\nSHAP explanation saved.")
```

---

### Step 10 — Transition-to-CVLE Causal Linkage with CVLE Lag (M3)

```python
# pipeline/step10_causal_linkage.py
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

    # Post-transition CVLE lag: years between transition and first CVLE after it
    post_rows = cdf[cdf['year'] > t_year]
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

json.dump(results, open('data/output/transition_cvle_linkage.json','w'), indent=2)
print(f"\nTransition-to-CVLE Linkage ({len(results)} events):")
for r in results:
    lag_str = f"lag={r['post_transition_cvle_lag']}yr" if r['post_transition_cvle_lag'] else "no CVLE"
    print(f"  {r['city']} {r['transition_year']}: {r['from_zone']}→{r['to_zone']} "
          f"Δ={r['risk_delta']:+.3f} p={r['p_value']} "
          f"{'✓' if r['significant'] else '✗'} {lag_str}")
```

---

### Step 11 — Viability Trend Regression (M2)

```python
# pipeline/step11_trend_regression.py
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
print(results_df[['city','crop','slope','r_squared','p_value','trend']].to_string())
```

---

### Step 12 — Control City Validation

```python
# pipeline/step12_control_validation.py
import json, pandas as pd

CONTROL_CITIES  = ['Pune','Kolkata','Mumbai']
AT_RISK_CITIES  = ['Delhi','Jaipur','Ahmedabad','Lucknow',
                   'Hyderabad','Chennai','Bangalore']

trend_report    = pd.read_json('data/output/viability_trend_report.json')
transition_rep  = json.load(open('data/output/transition_report.json'))
cvle_events     = pd.read_json('data/output/crop_viability_events.json')

print("=" * 60)
print("CONTROL CITY VALIDATION")
print("=" * 60)

# 1. Control cities should have trend == 'stable'
ctrl_trends = trend_report[trend_report['city'].isin(CONTROL_CITIES)]
print("\n[1] Trend check (expected: stable)")
print(ctrl_trends[['city','slope','p_value','trend']].to_string(index=False))
failed_trend = ctrl_trends[ctrl_trends['trend'] != 'stable']
if len(failed_trend) > 0:
    print(f"\nWARNING: {list(failed_trend['city'])} show non-stable trends — check model.")
else:
    print("✓ All control cities show stable viability trends.")

# 2. Control cities should have 0 CVLE events
ctrl_cvle = cvle_events[cvle_events['city'].isin(CONTROL_CITIES)]
print(f"\n[2] CVLE count in control cities (expected: 0): {len(ctrl_cvle)}")
if len(ctrl_cvle) > 0:
    print(f"WARNING: Control cities flagged for CVLEs: {ctrl_cvle[['city','year']].values}")
else:
    print("✓ No CVLE events in control cities.")

# 3. Control cities should have no transitions
ctrl_transitions = [t for t in transition_rep if t['city'] in CONTROL_CITIES]
print(f"\n[3] Transitions in control cities (expected: 0): {len(ctrl_transitions)}")
if ctrl_transitions:
    print(f"WARNING: {ctrl_transitions}")
else:
    print("✓ No climate zone transitions in control cities.")

# 4. At-risk cities should have at least 1 transition or CVLE
print("\n[4] At-risk city summary:")
for city in AT_RISK_CITIES:
    n_trans = len([t for t in transition_rep if t['city'] == city])
    n_cvle  = len(cvle_events[cvle_events['city'] == city])
    slope   = trend_report[trend_report['city'] == city]['slope'].values[0]
    print(f"  {city:<12} transitions={n_trans}  CVLEs={n_cvle}  slope={slope:+.6f}")

print("\n✓ Control validation complete.")
```

---

### Step 13 — Groundwater Recharge Grid Export

```python
# pipeline/step13_recharge_grid.py
import json, pandas as pd

df   = pd.read_csv('data/processed/vegshift_master.csv')
grid = {
    city: dict(zip(
        cdf.sort_values('year')['year'].astype(str),
        cdf.sort_values('year')['recharge_efficiency'].round(4)
    ))
    for city, cdf in df.groupby('city')
}
json.dump(grid, open('data/output/groundwater_recharge_grid.json','w'), indent=2)
print("Recharge grid saved — 10 cities × 25 years")
```

---

### Step 14 — Dashboard

```python
# pipeline/step14_dashboard.py
import json, pandas as pd, numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import dash
from dash import dcc, html, Input, Output

# ── Load all outputs ──────────────────────────────────────────────────────────
master      = pd.read_csv('data/processed/vegshift_master.csv')
koppen      = pd.read_csv('data/processed/koppen_annual.csv')
transitions = json.load(open('data/output/transition_report.json'))
cvle_events = pd.read_json('data/output/crop_viability_events.json')
trend_rep   = pd.read_json('data/output/viability_trend_report.json')
recharge    = json.load(open('data/output/groundwater_recharge_grid.json'))
linkage     = pd.read_json('data/output/transition_cvle_linkage.json')
shap_out    = json.load(open('data/output/shap_explanation.json'))

CITIES      = master['city'].unique().tolist()
CTRL        = ['Pune','Kolkata','Mumbai']
COLORS      = px.colors.qualitative.Set2

app = dash.Dash(__name__)
app.title = "VegShift — Vegetation Viability Monitor"

app.layout = html.Div([
    html.H1("VegShift — Vegetation Viability Loss Monitor",
            style={'fontFamily':'sans-serif','color':'#2c3e50','padding':'20px'}),

    dcc.Tabs([

        # ── Panel 1: Sowing Window Drift ──────────────────────────────────────
        dcc.Tab(label='Sowing Window Drift', children=[
            html.P("Monsoon onset day-of-year vs optimal sowing window. "
                   "Vertical dashed lines = climate zone transitions.",
                   style={'padding':'10px','fontFamily':'sans-serif'}),
            dcc.Dropdown(id='sow-city', options=[{'label':c,'value':c} for c in CITIES],
                         value='Delhi', clearable=False,
                         style={'width':'300px','margin':'10px'}),
            dcc.Graph(id='sow-chart'),
        ]),

        # ── Panel 2: Dual-Deficit Heatmap ─────────────────────────────────────
        dcc.Tab(label='Dual-Deficit Heatmap', children=[
            html.P("Red = atmospheric water deficit AND groundwater recharge failure same year.",
                   style={'padding':'10px','fontFamily':'sans-serif'}),
            dcc.Graph(id='dd-heatmap'),
        ]),

        # ── Panel 3: CVLE Timeline ────────────────────────────────────────────
        dcc.Tab(label='CVLE Timeline', children=[
            html.P("Total Crop Viability Loss Events per city across 2000–2024.",
                   style={'padding':'10px','fontFamily':'sans-serif'}),
            dcc.Graph(id='cvle-bar'),
        ]),

        # ── Panel 4: Transition-to-CVLE Table ────────────────────────────────
        dcc.Tab(label='Transition → CVLE', children=[
            html.P("Every detected climate zone transition with post-transition CVLE lag "
                   "and statistical significance.",
                   style={'padding':'10px','fontFamily':'sans-serif'}),
            dcc.Graph(id='linkage-table'),
        ]),

        # ── Panel 5: Recharge Efficiency Trend ───────────────────────────────
        dcc.Tab(label='Recharge Efficiency', children=[
            html.P("Annual groundwater recharge efficiency per city 2000–2022. "
                   "Falling line = aquifer losing ability to recover after monsoon.",
                   style={'padding':'10px','fontFamily':'sans-serif'}),
            dcc.Dropdown(id='rech-city', options=[{'label':c,'value':c} for c in CITIES],
                         value=CITIES[:3], multi=True,
                         style={'width':'500px','margin':'10px'}),
            dcc.Graph(id='rech-chart'),
        ]),

        # ── Panel 6: Koppen Zone History ─────────────────────────────────────
        dcc.Tab(label='Koppen Zone History', children=[
            html.P("Climate zone classification per city over 25 years. "
                   "Colour changes = zone transitions.",
                   style={'padding':'10px','fontFamily':'sans-serif'}),
            dcc.Graph(id='koppen-chart'),
        ]),

        # ── Panel 7: SHAP Feature Importance ─────────────────────────────────
        dcc.Tab(label='SHAP Importance', children=[
            html.P("Global and per-city SHAP feature importance from the Random Forest baseline.",
                   style={'padding':'10px','fontFamily':'sans-serif'}),
            dcc.Dropdown(id='shap-city',
                         options=[{'label':'Global','value':'global'}] +
                                 [{'label':c,'value':c} for c in CITIES],
                         value='global', clearable=False,
                         style={'width':'300px','margin':'10px'}),
            dcc.Graph(id='shap-chart'),
        ]),

        # ── Panel 8: Viability Trend Report ──────────────────────────────────
        dcc.Tab(label='Trend Report', children=[
            html.P("25-year linear trend in viability risk probability per city. "
                   "Red = statistically significant deterioration.",
                   style={'padding':'10px','fontFamily':'sans-serif'}),
            dcc.Graph(id='trend-chart'),
        ]),

    ])
], style={'fontFamily':'sans-serif','backgroundColor':'#f9f9f9'})


# ── Callbacks ─────────────────────────────────────────────────────────────────

@app.callback(Output('sow-chart','figure'), Input('sow-city','value'))
def update_sow(city):
    cdf     = master[master['city'] == city].sort_values('year')
    sow_doy = cdf['sow_doy'].iloc[0]
    fig     = go.Figure()

    # Monsoon onset line
    fig.add_trace(go.Scatter(
        x=cdf['year'], y=cdf['monsoon_onset_doy'],
        mode='lines+markers', name='Monsoon Onset DOY',
        line=dict(color='steelblue', width=2)
    ))

    # Optimal sowing window band (±14 days)
    fig.add_hrect(y0=sow_doy-14, y1=sow_doy+14,
                  fillcolor='green', opacity=0.15,
                  annotation_text='Optimal Sowing Window')

    # Transition markers
    for t in transitions:
        if t['city'] == city:
            fig.add_vline(x=t['transition_year'], line_dash='dash',
                          line_color='red', opacity=0.7,
                          annotation_text=f"{t['from_zone']}→{t['to_zone']}",
                          annotation_position='top right')

    fig.update_layout(title=f'Sowing Window Drift — {city}',
                      xaxis_title='Year', yaxis_title='Day of Year',
                      template='plotly_white')
    return fig


@app.callback(Output('dd-heatmap','figure'), Input('dd-heatmap','id'))
def update_dd(_):
    pivot = master.pivot_table(
        index='city', columns='year', values='dual_deficit', aggfunc='max'
    ).fillna(0)
    fig = px.imshow(pivot, color_continuous_scale=['white','crimson'],
                    labels={'color':'Dual Deficit'},
                    title='Dual-Deficit Heatmap (1 = atmospheric + groundwater failure)')
    fig.update_layout(template='plotly_white')
    return fig


@app.callback(Output('cvle-bar','figure'), Input('cvle-bar','id'))
def update_cvle(_):
    counts = master.groupby('city')['cvle_label'].sum().reset_index()
    counts = counts.sort_values('cvle_label', ascending=False)
    counts['color'] = counts['city'].apply(
        lambda c: 'lightgray' if c in CTRL else 'tomato'
    )
    fig = px.bar(counts, x='city', y='cvle_label',
                 color='color', color_discrete_map='identity',
                 title='Total CVLE Events per City (2000–2024)',
                 labels={'cvle_label':'CVLE Count','city':'City'})
    fig.update_layout(showlegend=False, template='plotly_white')
    return fig


@app.callback(Output('linkage-table','figure'), Input('linkage-table','id'))
def update_linkage(_):
    if len(linkage) == 0:
        return go.Figure()
    df_l = linkage.copy()
    df_l['significant'] = df_l['significant'].map({True:'✓ Yes', False:'✗ No'})
    df_l['lag_display'] = df_l['post_transition_cvle_lag'].apply(
        lambda x: f"{int(x)} yr" if x is not None and not pd.isna(x) else '—'
    )
    fig = go.Figure(data=[go.Table(
        header=dict(values=['City','Year','From','To','Pre Risk',
                            'Post Risk','Δ Risk','p-value','Sig?','CVLE Lag'],
                    fill_color='#2c3e50', font=dict(color='white',size=12)),
        cells=dict(values=[
            df_l['city'], df_l['transition_year'],
            df_l['from_zone'], df_l['to_zone'],
            df_l['pre_risk_mean'], df_l['post_risk_mean'],
            df_l['risk_delta'], df_l['p_value'],
            df_l['significant'], df_l['lag_display']
        ], fill_color='lavender', font=dict(size=11))
    )])
    fig.update_layout(title='Transition → CVLE Causal Linkage Table',
                      template='plotly_white')
    return fig


@app.callback(Output('rech-chart','figure'), Input('rech-city','value'))
def update_rech(cities_sel):
    fig = go.Figure()
    for city in (cities_sel if isinstance(cities_sel, list) else [cities_sel]):
        if city in recharge:
            years = sorted(recharge[city].keys())
            vals  = [recharge[city][y] for y in years]
            fig.add_trace(go.Scatter(
                x=[int(y) for y in years], y=vals,
                mode='lines+markers', name=city
            ))
    fig.update_layout(title='Groundwater Recharge Efficiency (2000–2022)',
                      xaxis_title='Year',
                      yaxis_title='Recharge Efficiency',
                      template='plotly_white')
    return fig


@app.callback(Output('koppen-chart','figure'), Input('koppen-chart','id'))
def update_koppen(_):
    kdf  = koppen.copy()
    zones = sorted(kdf['koppen_zone'].unique())
    z_map = {z: i for i, z in enumerate(zones)}
    kdf['zone_num'] = kdf['koppen_zone'].map(z_map)

    fig = px.scatter(kdf, x='year', y='city', color='koppen_zone',
                     title='Koppen Zone History per City (2000–2024)',
                     labels={'koppen_zone':'Zone'},
                     category_orders={'koppen_zone': zones})
    fig.update_traces(marker=dict(size=12, symbol='square'))
    fig.update_layout(template='plotly_white')
    return fig


@app.callback(Output('shap-chart','figure'), Input('shap-city','value'))
def update_shap(selection):
    if selection == 'global':
        data = pd.DataFrame(shap_out['global_importance'])
        fig  = px.bar(data.sort_values('mean_abs_shap'),
                      x='mean_abs_shap', y='feature', orientation='h',
                      title='Global SHAP Feature Importance',
                      labels={'mean_abs_shap':'Mean |SHAP|','feature':'Feature'})
    else:
        imp  = shap_out['city_importance'].get(selection, {})
        data = pd.DataFrame({'feature': list(imp.keys()),
                             'mean_abs_shap': list(imp.values())})
        fig  = px.bar(data.sort_values('mean_abs_shap'),
                      x='mean_abs_shap', y='feature', orientation='h',
                      title=f'SHAP Feature Importance — {selection}',
                      labels={'mean_abs_shap':'Mean |SHAP|','feature':'Feature'})
    fig.update_layout(template='plotly_white')
    return fig


@app.callback(Output('trend-chart','figure'), Input('trend-chart','id'))
def update_trend(_):
    t   = trend_rep.sort_values('slope', ascending=False).copy()
    t['color'] = t.apply(
        lambda r: 'tomato'    if r['trend'] == 'deteriorating'
             else 'steelblue' if r['trend'] == 'improving'
             else 'lightgray', axis=1
    )
    fig = go.Figure()
    for _, row in t.iterrows():
        fig.add_trace(go.Bar(
            x=[row['city']], y=[row['slope']],
            marker_color=row['color'],
            name=row['city'],
            text=f"p={row['p_value']} | {row['trend']}",
            textposition='outside'
        ))
    fig.add_hline(y=0, line_dash='dash', line_color='gray')
    fig.update_layout(title='25-Year Viability Risk Trend (slope of linear regression)',
                      xaxis_title='City', yaxis_title='Slope',
                      showlegend=False, template='plotly_white')
    return fig


if __name__ == '__main__':
    app.run(debug=True, port=8050)
```

---

### Step 15 — Crop Advisory Engine

**Role:** Forward-looking crop ranking that accounts for where the climate is heading, not just where it is today.

**Inputs:** `data/processed/vegshift_master.csv`, `data/output/viability_trend_report.json`

**Logic:**
A catalogue of 14 Indian crops (wheat, mustard, rice, cotton, sugarcane, groundnut, sorghum, ragi, chickpea, lentil, maize, sunflower, bajra, barley) is scored against each city's current conditions on five independent axes, each worth a fixed share of 100 points:

| Axis | Points | What is measured |
|------|--------|-----------------|
| Zone compatibility | 30 | Whether the city's current Koppen zone appears in the crop's viable zone list |
| Temperature stress | 20 | Margin between observed max temp and crop's upper thermal limit |
| Rainfall adequacy | 20 | Ratio of annual rainfall to crop water requirement |
| Groundwater stress | 15 | Pre-monsoon depth and depletion rate combined |
| Trajectory penalty | 15 | 5-year linear trends in rainfall, temperature, and GW depth — penalises crops whose future climate fit is worsening even if viable today |

The trajectory penalty is the key innovation: a crop that is borderline viable now but whose climate envelope is narrowing scores lower than a drought-tolerant alternative that is gaining headroom. Final scores are clipped to [0, 100] and sorted descending per city.

**Output:** `data/output/crop_advisory.json` — per-city ranked list of all 14 crops with score, zone-match flag, and season (kharif/rabi/annual).

```python
# pipeline/step15_crop_advisory.py
import json, pandas as pd, numpy as np

# 14 Indian crops with zone compatibility, resource requirements, and season
INDIAN_CROPS = {
    'wheat':     {'zones':['BSh','BSk','Cwa','Cwb','Cfa'], 'min_temp':5,  'max_temp':32, 'water_req':450,  'gdd_min':1200, 'season':'rabi'},
    'mustard':   {'zones':['BWh','BWk','BSh','BSk'],        'min_temp':5,  'max_temp':30, 'water_req':300,  'gdd_min':800,  'season':'rabi'},
    'rice':      {'zones':['Aw','Am','Af','Cwa'],           'min_temp':20, 'max_temp':38, 'water_req':1200, 'gdd_min':2000, 'season':'kharif'},
    'cotton':    {'zones':['BSh','BWh','Aw'],               'min_temp':18, 'max_temp':40, 'water_req':700,  'gdd_min':1800, 'season':'kharif'},
    'sugarcane': {'zones':['Cwa','Aw','Am'],                'min_temp':20, 'max_temp':38, 'water_req':1500, 'gdd_min':2500, 'season':'annual'},
    'groundnut': {'zones':['BSh','Aw','Cwa'],              'min_temp':20, 'max_temp':40, 'water_req':500,  'gdd_min':1600, 'season':'kharif'},
    'sorghum':   {'zones':['BSh','BWh','Aw','Cwa'],        'min_temp':18, 'max_temp':40, 'water_req':400,  'gdd_min':1400, 'season':'kharif'},
    'ragi':      {'zones':['Aw','BSh','Cwa'],              'min_temp':18, 'max_temp':38, 'water_req':350,  'gdd_min':1400, 'season':'kharif'},
    'chickpea':  {'zones':['BSh','BSk','Cwa'],             'min_temp':5,  'max_temp':30, 'water_req':250,  'gdd_min':900,  'season':'rabi'},
    'lentil':    {'zones':['BSk','Cwa','BSh'],             'min_temp':5,  'max_temp':28, 'water_req':200,  'gdd_min':700,  'season':'rabi'},
    'maize':     {'zones':['Cwa','Aw','BSh'],              'min_temp':18, 'max_temp':38, 'water_req':600,  'gdd_min':1600, 'season':'kharif'},
    'sunflower': {'zones':['BSh','Cwa','Aw'],              'min_temp':18, 'max_temp':35, 'water_req':400,  'gdd_min':1200, 'season':'rabi'},
    'bajra':     {'zones':['BWh','BSh','Aw'],              'min_temp':25, 'max_temp':42, 'water_req':300,  'gdd_min':1200, 'season':'kharif'},
    'barley':    {'zones':['BSh','BSk','Cwa'],             'min_temp':3,  'max_temp':30, 'water_req':300,  'gdd_min':900,  'season':'rabi'},
}

df     = pd.read_csv('data/processed/vegshift_master.csv')
trend  = pd.read_json('data/output/viability_trend_report.json')

trend_slope = dict(zip(trend['city'], trend['slope']))

advisory = {}
for city, cdf in df.groupby('city'):
    cdf    = cdf.sort_values('year')
    latest = cdf.iloc[-1]
    zone   = latest['koppen_zone']
    t_max  = latest['temp_max']
    rain   = latest['rainfall_annual']
    gw_dep = latest['pre_monsoon_depth_mbgl']
    depl   = latest['depletion_rate']

    # 5-year climate trajectory
    recent     = cdf[cdf['year'] >= cdf['year'].max() - 4]
    rain_trend = float(np.polyfit(recent['year'], recent['rainfall_annual'], 1)[0])
    temp_trend = float(np.polyfit(recent['year'], recent['temp_mean'], 1)[0])
    gw_trend   = float(np.polyfit(recent['year'], recent['pre_monsoon_depth_mbgl'], 1)[0])

    ranked = []
    for crop, spec in INDIAN_CROPS.items():
        score = 100.0

        # Zone compatibility (30 pts)
        score -= 0 if zone in spec['zones'] else 30

        # Temperature stress (20 pts)
        temp_margin = spec['max_temp'] - t_max
        score -= max(0, (5 - temp_margin) * 4) if temp_margin < 5 else 0

        # Rainfall adequacy (20 pts)
        water_ratio = rain / spec['water_req']
        score -= max(0, (1 - water_ratio) * 20)

        # Groundwater stress (15 pts)
        score -= min(15, gw_dep * 0.3 + max(0, depl) * 2)

        # Trajectory penalty — penalise crops whose future climate fit is deteriorating (15 pts)
        rain_pen = max(0, -rain_trend * 0.01 * (spec['water_req'] / 500))
        temp_pen = max(0, temp_trend * 2) if t_max > spec['max_temp'] - 3 else 0
        gw_pen   = max(0, gw_trend * 1.5)
        score -= min(15, rain_pen + temp_pen + gw_pen)

        score = max(0.0, round(score, 2))
        ranked.append({'crop': crop, 'season': spec['season'],
                       'score': score, 'zone_match': zone in spec['zones']})

    ranked.sort(key=lambda x: -x['score'])
    advisory[city] = {
        'current_zone':   zone,
        'rain_trend_5yr': round(rain_trend, 3),
        'temp_trend_5yr': round(temp_trend, 4),
        'gw_trend_5yr':   round(gw_trend, 3),
        'ranked_crops':   ranked,
    }

json.dump(advisory, open('data/output/crop_advisory.json', 'w'), indent=2)
print(f"Crop advisory generated for {len(advisory)} cities")
for city, adv in advisory.items():
    top3 = [f"{c['crop']}({c['score']})" for c in adv['ranked_crops'][:3]]
    print(f"  {city:<12} zone={adv['current_zone']}  top3={top3}")
```

---

### Step 16 — Irrigation and Groundwater-Aware Strategy Engine

**Role:** Translates raw groundwater stress into actionable farm-level water management prescriptions with government scheme links.

**Inputs:** `data/processed/vegshift_master.csv`, `data/processed/kaggle_climate.csv` (daily), `data/output/crop_advisory.json`

**Logic:**
Each city is classified into one of four **Recharge Stress Index (RSI)** levels using the latest year's `recharge_efficiency` and `pre_monsoon_depth_mbgl`:

| RSI Level | Condition | Irrigation Prescribed | Crops to Avoid |
|-----------|-----------|----------------------|----------------|
| Critical | efficiency < 0.002 OR depth > 20 mbgl | Drip only | Rice, sugarcane, cotton |
| Stressed | efficiency < 0.004 OR depth > 12 mbgl | Drip or sprinkler + rainwater harvesting | Rice, sugarcane |
| Moderate | efficiency < 0.006 | Sprinkler recommended | Sugarcane |
| Healthy | otherwise | Conventional acceptable | — |

Note: thresholds are calibrated to the actual data scale where `recharge_efficiency = depth_recovery_m / rainfall_annual_mm` (typical range 0.001–0.016).

**Optimal sowing window** is derived from the daily climate file: the kharif month (June–September) with the highest long-run average rainfall is identified per city, and the recommendation is to sow 2–3 weeks before that peak to exploit the moisture pulse without waterlogging risk.

**Recommended crops** are the top five from Step 15's ranked list after removing any crops on the avoid list for that RSI level, ensuring the agronomic advice is consistent with water availability.

**Government schemes** are statically mapped per RSI level — PMKSY and PM-KUSUM for critical zones (drip infrastructure subsidy + solar pumps), MGNREGS for water conservation structures in stressed zones, RKVY for diversification grants in moderate zones.

**Output:** `data/output/irrigation_strategy.json` — per-city RSI level, irrigation method, avoid-crop list, recommended crops, optimal sowing window, and applicable scheme descriptions.

```python
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
```

---

### Step 17 — Exploitation Risk and Investment Protection Engine

**Role:** Detect farmer economic vulnerability from climate predictors and surface the legal price floor before a distress sale can occur. No existing system does this.

**Inputs:** `data/processed/vegshift_master.csv`, `data/output/viability_trend_report.json`, `data/output/transition_cvle_linkage.json`, `data/output/crop_advisory.json`

**Exploitation Risk Index (ERI):**
A single scalar in [0, 1] computed as a weighted composite of five climate-derived signals:

| Component | Weight | Source |
|-----------|--------|--------|
| CVLE probability (5-yr rolling mean) | 0.30 | `cvle_label` from vegshift_master |
| Drought risk | 0.25 | `crop_water_deficit` (latest year) |
| Groundwater stress | 0.20 | `pre_monsoon_depth_mbgl` normalised to 25 mbgl ceiling |
| Viability trajectory risk | 0.15 | Linear trend slope from Step 11, normalised |
| Climate transition risk | 0.10 | Worst post-transition `risk_delta` from Step 10 |

**Alert threshold:** ERI ≥ 0.65. When breached, the system outputs:
- **MSP** (Minimum Support Price, 2024-25 rates) for the city's highest-ranked crop from Step 15
- **Distress price threshold** = 80% of MSP — any offer below this flags potential exploitation
- **Alternative crops** — top 3 from Step 15 advisory excluding the primary crop
- **State procurement center** URL — direct link to government mandated buyer
- **PMFBY** crop insurance scheme link

**Why 80%?** Indian agricultural market surveys consistently find distress sales 15–25% below MSP in drought years. 80% of MSP captures the lower bound of legitimate price variation while flagging the range where middlemen extract abnormal margins from climate-stressed farmers.

**Novelty:** All five ERI inputs are derived purely from climate and groundwater data collected in earlier pipeline steps. No market price feed, no survey data, no farm-level records are required. The exploitation vulnerability signal is inferred entirely from the physical climate trajectory — making this applicable to any Indian city with meteorological data.

**Output:** `data/output/exploitation_risk_report.json` — per-city ERI, alert flag, component breakdown, MSP, distress threshold, alternative crops, and procurement/insurance links.

```python
# pipeline/step17_exploitation_risk.py
import json, pandas as pd, numpy as np

# MSP 2024-25 (INR per quintal); sugarcane is FRP per quintal
MSP_2024 = {
    'wheat':     2275, 'mustard':   5650, 'rice':      2300,
    'cotton':    7121, 'sugarcane':  340, 'groundnut': 6783,
    'sorghum':   3371, 'ragi':      4290, 'chickpea':  5440,
    'lentil':    6425, 'maize':     2225, 'sunflower': 7280,
    'bajra':     2625, 'barley':    1735,
}
DISTRESS_RATIO = 0.80   # any offer below 80% of MSP = distress sale
ERI_THRESHOLD  = 0.65   # ERI above this triggers exploitation alert

PROCUREMENT_CENTERS = {
    'Delhi':     'Delhi State Civil Supplies Corp — procurement.delhi.gov.in',
    'Jaipur':    'RAJFED — rajfed.in',
    'Ahmedabad': 'GSCSC — gscsc.gujarat.gov.in',
    'Lucknow':   'UP Cooperative Federation — upagripardarshi.gov.in',
    'Hyderabad': 'MARKFED Telangana — markfed.telangana.gov.in',
    'Chennai':   'TN Cooperatives — tnpcb.gov.in',
    'Bangalore': 'HAFED Karnataka — ksfcltd.com',
    'Pune':      'MSAMB — msamb.com',
    'Kolkata':   'WBECSC — wbagri.gov.in',
    'Mumbai':    'MSAMB — msamb.com',
}

df       = pd.read_csv('data/processed/vegshift_master.csv')
trend    = pd.read_json('data/output/viability_trend_report.json')
linkage  = pd.read_json('data/output/transition_cvle_linkage.json')
advisory = json.load(open('data/output/crop_advisory.json'))

trend_slope = dict(zip(trend['city'], trend['slope']))

# Worst post-transition risk delta per city
trans_severity = {}
if len(linkage) > 0:
    for city, grp in linkage.groupby('city'):
        trans_severity[city] = float(grp['risk_delta'].max())

reports = {}
for city, cdf in df.groupby('city'):
    cdf    = cdf.sort_values('year')
    latest = cdf.iloc[-1]

    # Five ERI components, each normalised 0–1
    cvle_prob  = float(cdf['cvle_label'].tail(5).mean())
    drought    = float(latest['crop_water_deficit'])
    gw_stress  = float(min(1.0, latest['pre_monsoon_depth_mbgl'] / 25))
    slope      = trend_slope.get(city, 0)
    traj_risk  = float(min(1.0, max(0.0, slope * 50)))
    t_sev      = trans_severity.get(city, 0.0)
    trans_risk = float(min(1.0, max(0.0, t_sev)))

    eri = round(min(1.0,
        0.30 * cvle_prob  +
        0.25 * drought    +
        0.20 * gw_stress  +
        0.15 * traj_risk  +
        0.10 * trans_risk
    ), 4)

    top_crop     = advisory[city]['ranked_crops'][0]['crop']
    msp          = MSP_2024.get(top_crop)
    distress_thr = round(msp * DISTRESS_RATIO) if msp else None
    alt_crops    = [c['crop'] for c in advisory[city]['ranked_crops']
                    if c['crop'] != top_crop][:3]

    reports[city] = {
        'eri':   eri,
        'alert': eri >= ERI_THRESHOLD,
        'eri_components': {
            'cvle_prob_5yr':   round(cvle_prob, 4),
            'drought_risk':    round(drought, 4),
            'gw_stress':       round(gw_stress, 4),
            'trajectory_risk': round(traj_risk, 4),
            'transition_risk': round(trans_risk, 4),
        },
        'primary_crop':             top_crop,
        'msp_inr_per_quintal':      msp,
        'distress_price_threshold': distress_thr,
        'alternative_crops':        alt_crops,
        'procurement_center':       PROCUREMENT_CENTERS.get(city, 'Contact state agriculture dept'),
        'crop_insurance_scheme':    'PMFBY — pmfby.gov.in',
    }

json.dump(reports, open('data/output/exploitation_risk_report.json', 'w'), indent=2)
print(f"\nExploitation Risk Index (ERI) — {len(reports)} cities:")
for city, r in sorted(reports.items(), key=lambda x: -x[1]['eri']):
    flag = '⚠ ALERT' if r['alert'] else '  OK   '
    print(f"  {flag}  {city:<12} ERI={r['eri']:.3f}  crop={r['primary_crop']:<12} "
          f"MSP=Rs{r['msp_inr_per_quintal']}/q  distress<Rs{r['distress_price_threshold']}/q")
```

---

## 5. Pipeline Runner

```python
# run_vegshift.py
import subprocess, sys

STEPS = [
    ('Master Index',                  'pipeline/step0_master_index.py'),
    ('Preprocess Datasets',           'pipeline/step0b_preprocess_datasets.py'),
    ('Koppen Classification',         'pipeline/step1_koppen_classification.py'),
    ('Transition Detection',          'pipeline/step1b_transition_detection.py'),
    ('Climate Feature Aggregation',   'pipeline/step2_climate_aggregate.py'),
    ('Groundwater Aggregation',       'pipeline/step3_groundwater_aggregate.py'),
    ('FAO GAEZ Extraction',           'pipeline/step4_gaez_extract.py'),
    ('Three-Way Join + CVLE Labels',  'pipeline/step5_join_and_features.py'),
    ('TFT Training',                  'pipeline/step6_tft_train.py'),
    ('TFT Prediction + Attention',    'pipeline/step7_tft_predict.py'),
    ('Baselines RF + LR + LSTM',      'pipeline/step8_baselines.py'),
    ('SHAP Explainability',           'pipeline/step9_shap_explainability.py'),
    ('Causal Linkage M3',             'pipeline/step10_causal_linkage.py'),
    ('Trend Regression M2',           'pipeline/step11_trend_regression.py'),
    ('Control City Validation',       'pipeline/step12_control_validation.py'),
    ('Recharge Grid Export',          'pipeline/step13_recharge_grid.py'),
    ('Crop Advisory Engine',          'pipeline/step15_crop_advisory.py'),
    ('Irrigation Strategy Engine',    'pipeline/step16_irrigation_strategy.py'),
    ('Exploitation Risk Engine',      'pipeline/step17_exploitation_risk.py'),
]

DASHBOARD = ('Dashboard', 'pipeline/step14_dashboard.py')

for label, script in STEPS:
    print(f"\n{'='*60}\n{label}\n{'='*60}")
    r = subprocess.run([sys.executable, script])
    if r.returncode != 0:
        print(f"ERROR in {script}. Halting.")
        sys.exit(1)

# Dashboard runs last in the background so it doesn't block the pipeline
subprocess.Popen([sys.executable, DASHBOARD[1]])
print("\n✓ VegShift complete. Dashboard launching at http://localhost:8050")
print("  Advisory: data/output/crop_advisory.json")
print("  Irrigation: data/output/irrigation_strategy.json")
print("  Exploitation risk: data/output/exploitation_risk_report.json")
```

---

## 6. Output Files

| File | Produced By | Contents |
|------|-------------|----------|
| `transition_report.json` | Step 1b | All detected Koppen transitions — city, year, from/to zone |
| `crop_viability_events.json` | Step 7 | All CVLE instances — city, year, crop, triggering features |
| `tft_attention_weights.json` | Step 7 | Per-city TFT attention weights over 5-year lookback |
| `shap_explanation.json` | Step 9 | Global + per-city SHAP feature importance (RF) |
| `transition_cvle_linkage.json` | Step 10 | Pre/post viability risk, Wilcoxon p-value, CVLE lag |
| `viability_trend_report.json` | Step 11 | 25-year regression slope, R², p-value, trend label |
| `groundwater_recharge_grid.json` | Step 13 | Annual recharge efficiency — 10 cities × 25 years |
| `crop_advisory.json` | Step 15 | Per-city ranked crop suitability with trajectory penalty scores |
| `irrigation_strategy.json` | Step 16 | RSI-based irrigation method, avoid-crops list, optimal sowing window, government schemes |
| `exploitation_risk_report.json` | Step 17 | ERI score, alert flag, MSP, distress price threshold, alternative crops per city |

---

## 7. File Structure

```
vegshift/
├── data/
│   ├── raw/
│   │   ├── climate/
│   │   │   └── india_2000_2024_daily_weather.csv   ← original DS1 download
│   │   ├── cgwb/
│   │   │   └── CGWB_India_quality_controlled_GWLs_ref_sy_2000_2022.csv
│   │   └── gaez/
│   │       ├── whe_suit_class_r_hist_cruts32_7clim.tif
│   │       ├── cot_suit_class_r_hist_cruts32_7clim.tif
│   │       ├── rcw_suit_class_r_hist_cruts32_7clim.tif
│   │       ├── suc_suit_class_r_hist_cruts32_7clim.tif
│   │       ├── srg_suit_class_r_hist_cruts32_7clim.tif
│   │       └── pig_suit_class_r_hist_cruts32_7clim.tif
│   ├── processed/
│   │   ├── kaggle_climate.csv              ← standardized DS1 (output of step0b)
│   │   ├── master_index.csv
│   │   ├── koppen_annual.csv
│   │   ├── zone_map.json
│   │   ├── climate_annual.csv
│   │   ├── groundwater_annual.csv
│   │   ├── gaez_baseline.csv
│   │   └── vegshift_master.csv
│   └── output/
│       ├── transition_report.json
│       ├── crop_viability_events.json
│       ├── tft_attention_weights.json
│       ├── shap_explanation.json
│       ├── transition_cvle_linkage.json
│       ├── viability_trend_report.json
│       ├── groundwater_recharge_grid.json
│       ├── crop_advisory.json
│       ├── irrigation_strategy.json
│       └── exploitation_risk_report.json
├── pipeline/
│   ├── step0_master_index.py
│   ├── step1_koppen_classification.py
│   ├── step1b_transition_detection.py
│   ├── step2_climate_aggregate.py
│   ├── step3_groundwater_aggregate.py
│   ├── step4_gaez_extract.py
│   ├── step5_join_and_features.py
│   ├── step6_tft_train.py
│   ├── step7_tft_predict.py
│   ├── step8_baselines.py
│   ├── step9_shap_explainability.py
│   ├── step10_causal_linkage.py
│   ├── step11_trend_regression.py
│   ├── step12_control_validation.py
│   ├── step13_recharge_grid.py
│   ├── step14_dashboard.py
│   ├── step15_crop_advisory.py
│   ├── step16_irrigation_strategy.py
│   └── step17_exploitation_risk.py
├── models/
│   ├── tft/
│   │   └── vegshift-tft-best.ckpt
│   └── baselines/
│       ├── rf_baseline.pkl
│       ├── lr_baseline.pkl
│       ├── lstm_baseline.pt
│       └── scaler.pkl
└── run_vegshift.py
```

---

## 8. Requirements

```txt
# requirements.txt
pandas>=2.0
numpy>=1.24
scipy>=1.10
scikit-learn>=1.3
shap>=0.44
rasterio>=1.3
pytorch-forecasting>=1.0
pytorch-lightning>=2.0
torch>=2.0
joblib>=1.3
plotly>=5.18
dash>=2.14
```

---

## 9. Complete Pipeline Summary

| Step | Script | What It Does |
|------|--------|-------------|
| 0 | step0 | Build 250-row master index |
| 0b | step0b | Standardize DS1 columns; derive humidity; output `kaggle_climate.csv` |
| 1 | step1 | Koppen-Geiger classify every city-year; encode zone as integer |
| 1b | step1b | Detect persistent zone transitions (3+ yr confirmation) → transition_report.json |
| 2 | step2 | Aggregate daily climate → annual city features + monsoon onset + GDD |
| 3 | step3 | Haversine 50km spatial median of CGWB wells → city-level groundwater features |
| 4 | step4 | Extract FAO GAEZ suitability class per city from GeoTIFF rasters |
| 5 | step5 | Three-way join + Koppen encoding + dual-deficit flag + CVLE labels |
| 6 | step6 | Train Temporal Fusion Transformer — 5-yr lookback, Koppen as time-varying categorical |
| 7 | step7 | Predict CVLE probabilities + extract per-city attention weights |
| 8 | step8 | Train RF + LR + LSTM baselines for comparison against TFT |
| 9 | step9 | SHAP explainability on RF — global + per-city feature importance |
| 10 | step10 | M3: Wilcoxon test pre/post viability risk + compute CVLE lag per transition |
| 11 | step11 | M2: Linear trend regression on 25-yr viability risk per city |
| 12 | step12 | Control city validation — assert Pune/Kolkata/Mumbai are stable |
| 13 | step13 | Export groundwater recharge grid (10 cities × 25 years) |
| 14 | step14 | 11-panel interactive Dash dashboard (launched in background after step 17) |
| 15 | step15 | Rank 14 Indian crops per city by suitability score — current zone + climate trajectory penalty |
| 16 | step16 | RSI-level irrigation prescription, avoid-crop list, optimal sowing window, government schemes |
| 17 | step17 | ERI composite score → distress alert with MSP, distress price threshold, alt crops, procurement links |

**SDGs:** SDG 2 (Zero Hunger) · SDG 6 (Clean Water) · SDG 13 (Climate Action)

---

*VegShift — Complete Standalone Pipeline | April 2026*
