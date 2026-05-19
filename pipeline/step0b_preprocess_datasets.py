"""
Preprocessing step: standardize raw datasets into pipeline-expected formats.
Run once before Phase 1. Outputs:
  data/raw/kaggle_climate.csv   (DS1 - standardized columns + derived humidity)

DS2 and DS3 issues are handled at read-time in Steps 3 and 4 respectively
(see DATA_NOTES.md for details).
"""
import pandas as pd
import numpy as np

# ── DS1: Standardize climate columns ─────────────────────────────────────────
print("Processing DS1 - Climate...")

df = pd.read_csv(
    'data/raw/climate/india_2000_2024_daily_weather.csv',
    parse_dates=['date']
)

df['temp_max']  = df['temperature_2m_max']
df['temp_min']  = df['temperature_2m_min']
df['temp_mean'] = (df['temperature_2m_max'] + df['temperature_2m_min']) / 2.0
df['rainfall']  = df['precipitation_sum']

# wind_speed_10m_max is in km/h (Open-Meteo default); convert to m/s
df['wind_speed'] = df['wind_speed_10m_max'] / 3.6

# Derive relative humidity via Steadman's apparent temperature formula:
#   AT = T + 0.33*e - 0.70*ws - 4.00  =>  e = (AT - T + 0.70*ws + 4.00) / 0.33
#   es = 6.1078 * exp(17.27*T / (237.3+T))
#   RH = (e / es) * 100, clipped to [5, 100]
T   = (df['temperature_2m_max'] + df['temperature_2m_min']) / 2.0
AT  = (df['apparent_temperature_max'] + df['apparent_temperature_min']) / 2.0
WS  = df['wind_speed']  # m/s
e   = (AT - T + 0.70 * WS + 4.00) / 0.33
es  = 6.1078 * np.exp(17.27 * T / (237.3 + T))
df['humidity'] = (e / es * 100).clip(5, 100).round(1)

out = df[['city', 'date', 'temp_mean', 'temp_max', 'temp_min',
          'rainfall', 'wind_speed', 'humidity']].copy()
out.to_csv('data/processed/kaggle_climate.csv', index=False)
print(f"  Saved: data/processed/kaggle_climate.csv  shape={out.shape}")
print(f"  Humidity mean by city:")
print(out.groupby('city')['humidity'].mean().round(1).to_string())
print("Done.")
