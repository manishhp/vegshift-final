# pipeline/step15_crop_advisory.py
import json
import os
from pathlib import Path
import pandas as pd
import numpy as np

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

# Ideal/baseline crop yields in tons per hectare
BASELINE_YIELDS = {
    'wheat': 4.0, 'mustard': 2.0, 'rice': 4.5, 'cotton': 2.5,
    'sugarcane': 80.0, 'groundnut': 2.5, 'sorghum': 2.0, 'ragi': 2.5,
    'chickpea': 1.8, 'lentil': 1.5, 'maize': 5.0, 'sunflower': 2.0,
    'bajra': 1.8, 'barley': 3.0
}

df     = pd.read_csv('data/processed/vegshift_master.csv')
trend  = pd.read_json('data/output/viability_trend_report.json')

trend_slope = dict(zip(trend['city'], trend['slope']))

advisory = {}
dssat_runs_dir = Path("data/output/dssat_runs")

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
        zone_pen = 0 if zone in spec['zones'] else 30
        score -= zone_pen

        # Temperature stress (20 pts)
        temp_margin = spec['max_temp'] - t_max
        temp_pen = max(0, (5 - temp_margin) * 4) if temp_margin < 5 else 0
        score -= temp_pen

        # Rainfall adequacy (20 pts)
        water_ratio = rain / spec['water_req']
        water_pen = max(0, (1 - water_ratio) * 20)
        score -= water_pen

        # Groundwater stress (15 pts)
        gw_pen = min(15, gw_dep * 0.3 + max(0, depl) * 2)
        score -= gw_pen

        # Trajectory penalty (15 pts)
        rain_pen_traj = max(0, -rain_trend * 0.01 * (spec['water_req'] / 500))
        temp_pen_traj = max(0, temp_trend * 2) if t_max > spec['max_temp'] - 3 else 0
        gw_pen_traj   = max(0, gw_trend * 1.5)
        traj_pen = min(15, rain_pen_traj + temp_pen_traj + gw_pen_traj)
        score -= traj_pen

        # DSSAT crop simulation yield feedback (integrate pyDSSAT output)
        yield_file = dssat_runs_dir / f"{city.lower()}_{crop}_yield.json"
        dssat_yield = None
        dssat_water_stress = None
        dssat_temp_stress = None
        dssat_pen = 0.0

        if yield_file.exists():
            try:
                yield_data = json.loads(yield_file.read_text(encoding="utf-8"))
                dssat_yield = float(yield_data["simulated_yield_t_ha"])
                dssat_water_stress = float(yield_data["mean_water_stress"])
                dssat_temp_stress = float(yield_data["mean_temp_stress"])

                # Deduct score if yield drops below baseline potential
                base_yield = BASELINE_YIELDS.get(crop, 3.0)
                yield_ratio = min(1.0, dssat_yield / base_yield)
                dssat_pen = max(0.0, (1.0 - yield_ratio) * 20.0)
                score -= dssat_pen
            except Exception as e:
                print(f"Error reading DSSAT output for {city}/{crop}: {e}")

        score = max(0.0, round(score, 2))
        ranked.append({
            'crop': crop, 'season': spec['season'],
            'score': score, 'zone_match': zone in spec['zones'],
            'dssat_yield_t_ha': dssat_yield,
            'dssat_water_stress': dssat_water_stress,
            'dssat_temp_stress': dssat_temp_stress,
            'dssat_yield_deduction': round(-dssat_pen, 2) if dssat_pen > 0 else 0.0,
            'breakdown': {
                'zone':       round(-zone_pen, 2),
                'temp':       round(-temp_pen, 2),
                'water':      round(-water_pen, 2),
                'gw':         round(-gw_pen, 2),
                'trajectory': round(-traj_pen, 2),
            },
            'crop_spec': {
                'max_temp':  spec['max_temp'],
                'water_req': spec['water_req'],
                'zones':     spec['zones'],
            }
        })

    ranked.sort(key=lambda x: -x['score'])
    advisory[city] = {
        'current_zone':   zone,
        'rain_trend_5yr': round(rain_trend, 3),
        'temp_trend_5yr': round(temp_trend, 4),
        'gw_trend_5yr':   round(gw_trend, 3),
        'climate_context': {
            't_max':          round(float(t_max), 1),
            'rainfall_mm':    round(float(rain), 0),
            'gw_depth_mbgl':  round(float(gw_dep), 1),
            'depletion_rate': round(float(depl), 2),
        },
        'ranked_crops':   ranked,
    }

out_path = Path('data/output/crop_advisory.json')
out_path.parent.mkdir(parents=True, exist_ok=True)
json.dump(advisory, open(out_path, 'w'), indent=2)
print(f"Crop advisory generated for {len(advisory)} cities")
for city, adv in advisory.items():
    top3 = [f"{c['crop']}({c['score']})" for c in adv['ranked_crops'][:3]]
    print(f"  {city:<12} zone={adv['current_zone']}  top3={top3}")