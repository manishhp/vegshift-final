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
    # TIFFs use values 1-10 (8-10 = irrigated-potential categories); clip to 1-7 rainfed scale
    suit_class = min(suit_class, 7)
    rec = {'city': city, 'gaez_baseline_class': suit_class}
    rec.update(ECOCROP[city])
    records.append(rec)

gaez = pd.DataFrame(records)
gaez.to_csv('data/processed/gaez_baseline.csv', index=False)
print(gaez[['city','crop','gaez_baseline_class','gdd_min','water_req']])
