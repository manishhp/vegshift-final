from __future__ import annotations

import math
from pathlib import Path
from typing import Any
import pandas as pd


# Crop parameters derived from ECOCROP / GAEZ
CROP_PARAMS = {
    "wheat": {
        "base_temp": 5.0,
        "opt_temp": 25.0,
        "max_temp": 32.0,
        "gdd_target": 1200.0,
        "kc_max": 1.15,
        "harvest_index": 0.40,
        "lue": 1.5,  # Light Use Efficiency (g/MJ)
        "max_sw": 150.0,  # Soil water capacity (mm)
    },
    "mustard": {
        "base_temp": 5.0,
        "opt_temp": 22.0,
        "max_temp": 30.0,
        "gdd_target": 800.0,
        "kc_max": 1.05,
        "harvest_index": 0.30,
        "lue": 1.2,
        "max_sw": 120.0,
    },
    "rice": {
        "base_temp": 10.0,
        "opt_temp": 30.0,
        "max_temp": 38.0,
        "gdd_target": 2000.0,
        "kc_max": 1.20,
        "harvest_index": 0.45,
        "lue": 2.0,
        "max_sw": 200.0,
    },
    "cotton": {
        "base_temp": 15.0,
        "opt_temp": 32.0,
        "max_temp": 40.0,
        "gdd_target": 1800.0,
        "kc_max": 1.15,
        "harvest_index": 0.35,
        "lue": 1.4,
        "max_sw": 180.0,
    },
    "sugarcane": {
        "base_temp": 10.0,
        "opt_temp": 32.0,
        "max_temp": 38.0,
        "gdd_target": 2500.0,
        "kc_max": 1.25,
        "harvest_index": 0.70,
        "lue": 2.2,
        "max_sw": 250.0,
    },
    "groundnut": {
        "base_temp": 10.0,
        "opt_temp": 30.0,
        "max_temp": 40.0,
        "gdd_target": 1600.0,
        "kc_max": 1.10,
        "harvest_index": 0.38,
        "lue": 1.3,
        "max_sw": 140.0,
    },
    "sorghum": {
        "base_temp": 10.0,
        "opt_temp": 32.0,
        "max_temp": 40.0,
        "gdd_target": 1400.0,
        "kc_max": 1.05,
        "harvest_index": 0.42,
        "lue": 1.6,
        "max_sw": 130.0,
    },
    "ragi": {
        "base_temp": 10.0,
        "opt_temp": 30.0,
        "max_temp": 38.0,
        "gdd_target": 1400.0,
        "kc_max": 1.00,
        "harvest_index": 0.38,
        "lue": 1.4,
        "max_sw": 120.0,
    },
}


class CropSimulation:
    def __init__(self, crop_name: str) -> None:
        name = crop_name.lower().split("/")[0].split("-")[0].strip()
        self.crop_name = name
        self.params = CROP_PARAMS.get(name, CROP_PARAMS["wheat"])

    def simulate(self, df: pd.DataFrame) -> dict[str, Any]:
        """Runs the daily crop growth simulation based on weather inputs."""
        p = self.params
        gdd_accum = 0.0
        biomass_accum = 0.0
        sw = p["max_sw"] * 0.75  # Start soil water at 75% capacity
        
        water_stress_vals = []
        temp_stress_vals = []
        active_days = 0
        matured = False

        for _, row in df.iterrows():
            tmax = float(row["tmax"])
            tmin = float(row["tmin"])
            srad = float(row["srad"])
            rain = float(row["rain"])
            tmean = (tmax + tmin) / 2.0

            # 1. GDD Accumulation
            daily_gdd = max(0.0, tmean - p["base_temp"])
            gdd_accum += daily_gdd
            active_days += 1

            # 2. Hargreaves Potential Evapotranspiration (PET)
            # PET (mm/day) = 0.0023 * (Tmean + 17.8) * (Tmax - Tmin)^0.5 * Ra (represented by srad)
            pet = 0.0023 * (tmean + 17.8) * math.sqrt(max(0.1, tmax - tmin)) * srad
            pet = max(0.1, min(15.0, pet))  # Clip to realistic bounds

            # 3. Dynamic Crop Coefficient (Kc)
            growth_fraction = gdd_accum / p["gdd_target"]
            if growth_fraction < 0.2:
                kc = 0.3
            elif growth_fraction < 0.6:
                kc = 0.3 + (p["kc_max"] - 0.3) * (growth_fraction - 0.2) / 0.4
            elif growth_fraction < 0.88:
                kc = p["kc_max"]
            else:
                kc = p["kc_max"] - (p["kc_max"] - 0.4) * min(1.0, (growth_fraction - 0.88) / 0.12)
            
            crop_demand = pet * kc

            # 4. Soil Water Water Balance
            sw = min(p["max_sw"], sw + rain)
            actual_et = min(sw, crop_demand)
            sw = max(0.0, sw - actual_et)

            # 5. Stress Factors (0 = high stress, 1 = no stress)
            # Water stress: ratio of actual water transpirated to demand
            w_stress = (actual_et / crop_demand) if crop_demand > 0 else 1.0
            water_stress_vals.append(w_stress)

            # Heat stress: penalty if temperature is above optimal or too cold
            if tmax > p["opt_temp"]:
                t_stress = max(0.0, 1.0 - (tmax - p["opt_temp"]) / (p["max_temp"] - p["opt_temp"]))
            elif tmean < p["base_temp"] + 5.0:
                t_stress = max(0.0, (tmean - p["base_temp"]) / 5.0)
            else:
                t_stress = 1.0
            temp_stress_vals.append(t_stress)

            # 6. Biomass Accumulation
            # biomass = Radiation * Light Use Efficiency * Water Stress * Temperature Stress
            daily_biomass = srad * p["lue"] * w_stress * t_stress
            biomass_accum += daily_biomass

            if gdd_accum >= p["gdd_target"]:
                matured = True
                break

        # Calculate crop yield in tons per hectare
        # Multiply by harvest index, scale factor to get tons/ha
        sim_yield = biomass_accum * p["harvest_index"] * 0.01

        mean_w_stress = sum(water_stress_vals) / len(water_stress_vals) if water_stress_vals else 1.0
        mean_t_stress = sum(temp_stress_vals) / len(temp_stress_vals) if temp_stress_vals else 1.0

        return {
            "crop": self.crop_name,
            "simulated_yield_t_ha": round(float(sim_yield), 3),
            "simulated_biomass_t_ha": round(float(biomass_accum * 0.01), 3),
            "mean_water_stress": round(mean_w_stress, 3),
            "mean_temp_stress": round(mean_t_stress, 3),
            "growing_days": active_days,
            "matured": matured,
        }


def run_simulation(wth_path: str | Path, crop_name: str) -> dict[str, Any]:
    wth_path = Path(wth_path)
    if not wth_path.exists():
        raise FileNotFoundError(f"Weather file not found: {wth_path}")

    # Parse WTH file (skip header lines starting with * or @)
    rows = []
    with wth_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("*") or line.startswith("@"):
                continue
            parts = line.split()
            if len(parts) >= 5:
                # date format yyyymmdd, srad, tmax, tmin, rain
                rows.append({
                    "date": parts[0],
                    "srad": float(parts[1]),
                    "tmax": float(parts[2]),
                    "tmin": float(parts[3]),
                    "rain": float(parts[4]),
                })

    df = pd.DataFrame(rows)
    sim = CropSimulation(crop_name)
    return sim.simulate(df)
