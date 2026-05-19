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
        print(f"WARNING: No wells within {RADIUS_KM}km of {city} -- using {len(nearby)} nearest wells")

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
