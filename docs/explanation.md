# VegShift: Detecting When Crops Die Due to Climate Change
## A Comprehensive Technical Explanation — Written for a Civil/Environmental Engineering Audience

---

## Quick Summary

**The Core Problem:** India's climate is changing unevenly. Some cities are getting measurably hotter, their monsoons are arriving later, and their underground water reserves are being drawn down faster than rain can replenish them. When enough of these pressures accumulate over multiple years, crops that farmers have grown there for decades can no longer survive.

**What VegShift Does:** It detects — with year-level precision — the moment when a city's climate has shifted far enough to make a particular crop unviable. It answers two questions: *When exactly did this happen?* and *Why did it happen?*

**The Output:** A formally timestamped event, called a **Crop Viability Loss Event (CVLE)**, such as: *"Delhi: Wheat stopped being viable in 2018 because of extreme water shortage, a delayed monsoon, and insufficient heat accumulation for grain maturation."*

**The Scope:** 10 major Indian cities, 25 years of data (2000–2024), 6 primary crops, analysed through a 21-step automated data pipeline (17 core production steps + 4 comparative research steps).

**The Audience for Results:** Agricultural researchers, policymakers, climate adaptation planners, and farmers themselves — through an interactive dashboard and a React web application.

---

## Table of Contents

1. [The Three Datasets](#part-1-the-three-datasets)
2. [Key Physical and Statistical Concepts](#part-2-key-concepts)
3. [The 21-Step Processing Pipeline](#part-3-the-21-step-pipeline)
4. [Data Quality and Special Cases](#part-4-data-quality-and-special-cases)
5. [Key Output Files](#part-5-key-outputs-explained)
6. [End-to-End Worked Example: Delhi Wheat](#part-6-from-data-to-insight)
7. [Design Decisions and Justifications](#part-7-why-this-approach)
8. [Technical Stack Summary](#part-8-technical-stack)
9. [Running the System](#part-9-running-and-testing)
10. [Glossary](#glossary)

---

## Part 1: The Three Datasets Explained

VegShift draws on three completely independent data sources and combines them. Think of it like diagnosing the health of an agricultural system using three types of evidence simultaneously:

- **Dataset 1:** The atmosphere above the city (daily weather: temperature, rainfall, wind)
- **Dataset 2:** The ground beneath the city (groundwater well depths, four times per year)
- **Dataset 3:** What each crop biologically needs (FAO maps + agronomic thresholds)

No single dataset alone is sufficient. Rainfall records tell you nothing about whether underground reserves are also failing. Groundwater data alone tells you nothing about whether it is too hot for a crop to mature. Only together do they give a complete picture.

---

### Dataset 1: Daily Weather Data (Atmospheric Layer)

**What it is:**
25 years (2000–2024) of daily meteorological observations — maximum temperature, minimum temperature, total rainfall, and wind speed — for 10 major Indian cities: Delhi, Mumbai, Kolkata, Chennai, Bangalore, Hyderabad, Jaipur, Lucknow, Pune, and Ahmedabad.

**File location:** `data/raw/climate/india_2000_2024_daily_weather.csv`

**Approximate size:** ~91,000 records (25 years × 365 days × 10 cities)

**Raw data looks like this:**

```
Date          City      Temp_Max   Temp_Min   Rainfall   Wind_Speed
2018-06-15    Delhi     42°C       28°C       15 mm      18 km/h
2018-06-16    Delhi     41°C       29°C       8 mm       14.4 km/h
```

**Key derived variable — Humidity:**
The raw dataset has no humidity column. Humidity is critical because crops lose water through transpiration faster in dry air. We derive **relative humidity (RH)** from the observed data using an inversion of Steadman's apparent temperature (heat index) formula:

The apparent temperature formula (Steadman/Rothfusz) relates how hot it *feels* (apparent temperature, AT) to actual temperature (T), relative humidity (RH), and wind speed (W):

```
AT = T + 0.33·e − 0.70·W − 4.00
where e = actual vapour pressure = (RH/100) · es
and es = saturation vapour pressure = 6.1078 · exp(17.27·T / (237.3 + T))
```

Rearranging to solve for *e* from the known AT, T, and W:

```python
# Step 1: compute apparent temperature as average of max and min
AT_mean = (AT_max + AT_min) / 2
T_mean  = (Temp_Max + Temp_Min) / 2
wind_ms = Wind_Speed_kmh / 3.6        # convert km/h → m/s

# Step 2: back-calculate actual vapour pressure
e  = (AT_mean - T_mean + 0.70 * wind_ms + 4.00) / 0.33

# Step 3: compute saturation vapour pressure at that temperature
es = 6.1078 * exp(17.27 * T_mean / (237.3 + T_mean))

# Step 4: relative humidity
RH = clip((e / es) * 100, 5, 100)    # bounded between 5% and 100%
```

This is validated against known climatological normals: Mumbai averages ~90% RH (coastal city, consistent with observations) and Jaipur averages ~65% RH (semi-arid Rajasthan, consistent with field data). The clip to 5% prevents physically impossible negative humidity when the formula overshoots in extreme dry conditions.

**Wind speed unit conversion:**
The raw data reports wind in km/h; all crop-science formulas (and Penman-Monteith evapotranspiration, which is the scientific standard) use m/s. Conversion: `wind_ms = wind_kmh / 3.6`.

**What we compute from this dataset:**
From the 365 daily records per city-year, we compute annual summaries that are agronomically meaningful:

| Derived Annual Feature | Calculation Method | Physical Meaning |
|---|---|---|
| `temp_mean` | Average of daily means across the year | Baseline warmth experienced by the crop |
| `rainfall_annual` | Sum of all daily rainfall | Total water falling from sky in that year |
| `n_dry_months` | Count of months where total rainfall < 60 mm | How many months were effectively rainless |
| `monsoon_onset_doy` | Day-of-year when 5-day cumulative rain first exceeds 25 mm (rolling) | When the wet season actually begins |
| `sowing_window_miss` | (actual onset day − optimal sowing day) / optimal sowing day | How much the planting window was delayed as a fraction |
| `gdd_accumulation` | Sum of max(T_daily_mean − T_base, 0) from April to September | Heat units accumulated during growing season |
| `crop_water_deficit` | (crop water requirement − actual rainfall) / crop water requirement | Fractional shortfall in rainfall relative to crop needs |

Each of these is explained in detail in Part 2.

<img width="869" height="344" alt="image" src="https://github.com/user-attachments/assets/33f5d088-baa8-4cb7-8166-953c5fb16402" />

---

### Dataset 2: Groundwater Levels (Subsurface / Hydrological Layer)

**What it is:**
Depth-to-water-table measurements from thousands of observation wells across India, collected four times per year (January, May, August, November) from 2000 to 2022.

**Source:** Central Groundwater Board (CGWB) — the Indian government agency responsible for groundwater monitoring. CGWB maintains a national network of observation wells and publishes this data.

**Unit of measurement:** **Metres Below Ground Level (mbgl).**
- A reading of 10 mbgl means the water table sits 10 metres below the surface.
- A reading of 25 mbgl means the water table has dropped to 25 metres below the surface.
- **Higher number = deeper water table = worse condition.** This is the critical convention: unlike most measurements where "higher is better," in groundwater depth, a rising number means the aquifer is being depleted.

**Why four readings per year?**
India's water cycle is dominated by the monsoon. The four measurement dates capture the four key states of the annual cycle:

| Month | Hydrological Phase | What We Expect |
|---|---|---|
| January | Post-winter, before irrigation demand rises | Moderate depth; some monsoon recharge still retained |
| May | Pre-monsoon; peak irrigation demand; hottest months | Deepest reading of the year; maximum depletion |
| August | Mid-monsoon; active rainfall recharge | Shallowest reading; aquifer being refilled |
| November | Post-monsoon; recharge complete but tapering | Intermediate; reflects how much the monsoon refilled |

**Example for a Delhi well:**
```
Well_Location    Jan_2000   May_2000   Aug_2000   Nov_2000
Delhi_Well_7     15 mbgl    18 mbgl    12 mbgl    14 mbgl
Delhi_Well_8     16 mbgl    19 mbgl    13 mbgl    15 mbgl
```

- January: 15 m deep (starting point for the year)
- May: 18 m deep — dropped 3 m from January as irrigation drew water down during dry hot months
- August: 12 m deep — rose 6 m from monsoon rainfall infiltrating and recharging the aquifer
- November: 14 m deep — rose from May peak but partially drawn down again for post-monsoon crops

**How we use this data:**

1. **Spatial aggregation to city level:** Each city is represented by the median depth of all wells lying within a 50-km radius, calculated using the Haversine formula (explained in Part 2). Using the median rather than the mean protects against outlier wells that may have local geological anomalies.

2. **Depletion rate:** Year-over-year change in the January depth. If January 2001 = 16 m and January 2000 = 15 m, the depletion rate is +1 m/year — the aquifer dropped 1 metre over the year despite the monsoon. A persistent positive depletion rate means extraction is systematically outpacing recharge.

3. **Recharge efficiency:** Computed as:
   ```
   recharge_efficiency = (May_depth − Aug_depth) / rainfall_annual_mm
   ```
   This measures how many metres the water table rises per millimetre of annual rainfall. If a city gets 600 mm of rain and the water table rises 3 metres from May to August, efficiency = 3/600 = 0.005 m/mm. A declining efficiency over time means the aquifer's ability to absorb rainfall is deteriorating — often because clay layers are compacting or paved surfaces prevent infiltration.

4. **Dual-deficit detection:** If the city's `crop_water_deficit` (from Dataset 1) is high AND the `recharge_efficiency` is low in the same year, the farmer has no backup water source — neither sky nor ground.

**Special cases and data quality issues (detailed in Part 4):**
- Jaipur: Rajasthan state is absent from the CGWB database entirely; nearest-wells fallback used.
- Kolkata: No May (pre-monsoon) readings exist in the CGWB records for wells near Kolkata; global median imputation applied.
- 2023–2024: CGWB dataset ends at 2022; these years are filled by city-group mean imputation.
- Pre-2005: Very sparse coverage; filled using the average depletion rate from 2005–2007.

---

### Dataset 3: Crop Suitability Maps (FAO GAEZ)

**What it is:**
Geospatial raster maps (GeoTIFF format — a standard satellite imagery file format that stores data on a geographic grid) published by the Food and Agriculture Organization of the United Nations, from their **Global Agro-Ecological Zones version 4 (GAEZ v4)** database.

**What GeoTIFF means:** A GeoTIFF is an image file where every pixel represents a patch of land (~9 km × 9 km in this dataset) and the pixel's value encodes a number — in this case, a crop suitability score. The file includes geographic coordinates so software can look up the value for any lat/lon point.

**Temporal baseline:** The suitability scores were computed from a 1981–2010 climate baseline — meaning they represent *historical* crop suitability before recent climate shifts. This is intentional: we use the FAO baseline as the "what should grow here" reference, and then measure how much current climate deviates from that expectation.

**Coverage:** 53 crops across the globe; we use 6 for India: wheat, cotton, rice, sugarcane, mustard, and ragi/groundnut.

**Suitability scale (1–7):**

| Score | Meaning | Agricultural Interpretation |
|---|---|---|
| 1 | Not suitable | Crop cannot grow here under baseline climate |
| 2 | Very marginally suitable | Extreme limitations; very low yield |
| 3 | Marginally suitable | Significant limitations; below-average yield |
| 4 | Moderately suitable | Moderate limitations; reasonable yield with effort |
| 5 | Suitable | Minor limitations; good yield |
| 6 | Very suitable | No significant limitations; high yield |
| 7 | Optimally suitable | Best possible conditions for this crop |

Note: The raw GeoTIFFs also contain values 8–10 which represent **irrigated potential** — how the crop would do with full irrigation infrastructure. We clip these down to 7 because VegShift analyses rainfed + natural-recharge agriculture, not irrigated agriculture. Including irrigated potential would artificially inflate suitability scores.

**ECOCROP agronomic thresholds:**
Alongside the FAO suitability maps, we use the FAO ECOCROP database to get each crop's hard biological requirements — the physical limits below which the crop simply cannot complete its life cycle:

| Crop | Minimum GDD | Minimum Water (mm/year) | Maximum Temperature (°C) |
|---|---|---|---|
| Wheat | 1,200 | 450 | 35 |
| Cotton | 1,800 | 700 | 40 |
| Sugarcane | 2,500 | 1,500 | 38 |
| Rice | 2,000 | 1,200 | 38 |
| Mustard | 900 | 300 | 32 |
| Ragi/Groundnut | 1,400 | 500 | 40 |

These thresholds are used as hard limits in the CVLE detection logic. If observed GDD falls below the minimum, the crop biologically cannot mature that year, regardless of how good conditions look otherwise.

**How we use the maps:**
We extract the suitability value at each city's exact coordinates (latitude/longitude). This gives us the "baseline suitability" for each city-crop pair — what the historical climate said should grow there.

```
City        Crop        Baseline_Suitability
Delhi       Wheat       6 (very suitable)
Jaipur      Mustard     5 (suitable)
Chennai     Rice        6 (very suitable)
Hyderabad   Cotton      5 (suitable)
```

This baseline becomes the reference against which we measure climate-driven decline.

---

## Part 2: Key Concepts You Need to Know

### What is Growing Degree Days (GDD)?

**The concept:** Plants do not grow on calendar time — they grow on accumulated heat. A warm day advances plant development more than a cool day. GDD is the quantitative measure of how much heat has accumulated.

**The formula:**
```
GDD for one day = max( (T_max + T_min)/2  −  T_base , 0 )
```

Where:
- `T_max` = maximum temperature that day (°C)
- `T_min` = minimum temperature that day (°C)
- `T_base` = the temperature below which the crop does not develop (°C)
- The `max(..., 0)` means we never subtract GDD — cold days contribute zero, not negative

For wheat, T_base = 5°C. On a day with T_max = 25°C and T_min = 10°C:
```
GDD = (25 + 10)/2 − 5 = 17.5 − 5 = 12.5 GDD for that day
```

Wheat needs ~1,200 GDD to complete its full lifecycle from sowing to harvest. If a year in Delhi only accumulates 900 GDD during the growing season, the grain cannot fully mature — it would be harvested green and underweight.

**Why this matters for climate change:** Rising temperatures *could* increase GDD, but extreme heat above the crop's maximum tolerable temperature (e.g., >35°C for wheat) causes sterility and flower abortion, effectively "wasting" hot days. Our implementation sums GDD only during the April–September growing window.

---

### What is the Köppen Climate Classification?

**The concept:** Developed by Vladimir Köppen (1884, refined 1918), this is the world's most widely used climate classification system. It groups climates into categories based on measurable thresholds of temperature and rainfall — the same factors that determine vegetation. Think of it as a standardised language for describing what kind of climate a place has.

**Why it matters for agriculture:** Different climate zones have characteristic rainfall patterns, seasonal temperature swings, and drought frequencies. Crops evolved for one zone struggle in another. If a city's zone shifts, its crops face a fundamentally different environment.

**The main codes relevant to India:**

| Code | Full Name | Characteristics | Where Found |
|---|---|---|---|
| Am | Tropical monsoon | Always hot (>18°C coldest month); short dry season; intense monsoon | Mumbai, Kolkata |
| Aw | Tropical savanna | Always hot; pronounced dry season lasting 5+ months | Bangalore, Chennai, Hyderabad |
| BSh | Semi-arid hot | Hot; rain < aridity threshold but > 50% of it | Jaipur, Delhi, Ahmedabad |
| BWh | Arid hot/desert | Hot; extremely dry; rain < 50% of aridity threshold | Hyper-arid desert zones |
| Cwa | Humid subtropical | Cool dry winter; hot wet summer | Lucknow, parts of North India |

The **aridity threshold** used to separate dry (B) from non-dry (A, C) climates is itself temperature-dependent (higher temperatures evaporate more water, requiring more rain to "count" as non-arid):
```
P_threshold = 20 · T_ann + k
where k = 0 if rain falls mostly in summer,
         280 if rain is spread evenly,
         140 if between
```

**How VegShift classifies each year:**
```python
if annual_rainfall < aridity_threshold:
    if annual_rainfall < 0.5 * aridity_threshold:
        zone = "Desert (BW)"       # Less than half of what's needed
    else:
        zone = "Semi-arid (BS)"    # Between 50–100% of aridity threshold
elif temperature_coldest_month >= 18:
    zone = "Tropical (A)"          # Always warm — the monsoon belt
elif temperature_coldest_month >= 0:
    zone = "Temperate (C)"         # Cool winters but no hard freeze
```

This runs for every city-year, giving a time series of zone labels. When a city persistently shifts from one zone to another, it signals a fundamental climate reorganisation — not just a bad year.

---

### What is Monsoon Onset and Why Does It Matter for Farming?

The Indian summer monsoon (June–September) delivers approximately 70–80% of India's annual rainfall. The **onset date** — the day the monsoon actually arrives — is arguably the most important meteorological event in the Indian agricultural calendar.

**Why timing matters:**
- Kharif (summer) crops like rice, cotton, and sorghum must be sown within a narrow window after monsoon onset. The soil needs to be moist before sowing, and early sowing is limited because soil moisture is inadequate.
- If the monsoon arrives 3 weeks late, the sowing window shrinks or closes entirely. Crops sown too late will be harvested before they can fully mature (day-length and temperature conditions become unfavourable).
- Late monsoon onset also reduces total season length, directly reducing grain-filling time.

**How we calculate onset day-of-year (DOY):**
The onset is defined as the first day on which a rolling 5-day cumulative rainfall exceeds 25 mm. This mimics the traditional IMD (India Meteorological Department) definition of "effective monsoon onset" for agricultural purposes.

**Sowing Window Miss:**
Each crop has an "optimal sowing DOY" — the calendar date that maximises yield based on historical norms. If the monsoon arrives late, sowing is delayed:
```
sowing_window_miss = max(0, onset_doy − optimal_sowing_doy) / optimal_sowing_doy
```
A value of 0 = monsoon arrived on time or early. A value of 0.65 = monsoon arrived 65% later than optimal.

---

### What is the Dual-Deficit Concept?

The dual deficit is the central diagnostic innovation of VegShift. It detects when **both** of a farmer's water sources fail simultaneously.

**The two water sources:**
1. **Atmospheric water (rainfall):** Direct rainfall during the growing season
2. **Subsurface water (groundwater):** Wells and bore wells fed by aquifer recharge

**Why both must fail together:**
A farmer facing low rainfall can compensate by pumping groundwater — this is exactly what irrigation does. If the aquifer is being recharged adequately by the previous monsoon, this backup works. The crisis only becomes inescapable when:
- Rainfall is insufficient (atmospheric deficit), AND
- Groundwater is not being recharged enough to support pumping (subsurface deficit)

This is the "dual deficit." At this point, no practical fallback exists.

**Mathematical definition:**
```
dual_deficit = (crop_water_deficit > 0.40) AND (recharge_efficiency < 0.30)
```

Where:
- `crop_water_deficit > 0.40` means the rainfall was less than 60% of the crop's water requirement (40%+ shortfall)
- `recharge_efficiency < 0.30` means the aquifer recovered to less than 30% of what would be needed for irrigation supplementation

Note: The 0.30 recharge threshold is expressed as a fraction of the city's multi-year average recharge — not an absolute number — so it is comparable across cities with very different rainfall regimes.

---

### What is a Crop Viability Loss Event (CVLE)?

A CVLE is VegShift's formal declaration that a crop has crossed the threshold from "stressed but viable" to "no longer viable" for a given city in a given year.

**Why not just flag any bad year?**
Single bad years happen every decade. A true viability loss requires persistent, multi-system failure. The CVLE definition is deliberately conservative to avoid false alarms.

**CVLE trigger conditions — ALL must be true:**

**Condition 1: Dual-deficit persistence**
The dual-deficit must have occurred in **both** the current year and the immediately preceding year. This filters out isolated droughts. Agriculture has always had bad years; what VegShift detects is structural multi-year failure.

**Condition 2: Multi-threshold breach**
In the current year, **at least 2 of the following 3** must be true:
- Sowing window missed by more than 60% (monsoon chronically late)
- Crop water deficit greater than 40% (rainfall well below crop needs)
- GDD insufficient (heat accumulation below the crop's biological minimum)

**The rationale for requiring 2 of 3:** No single threshold is definitive. A late monsoon can sometimes be compensated by a longer post-onset season. Low rainfall can sometimes be compensated by better-than-average groundwater. But when two or three signals fire simultaneously, the redundancies are exhausted.

**Example CVLE determination (Delhi, Wheat, 2018):**
```
Year 2017: dual_deficit = True (drought + poor recharge)
Year 2018: dual_deficit = True  → Condition 1 satisfied (2 consecutive years)

Year 2018 multi-threshold check:
  sowing_window_miss = 0.65  → > 0.60  ✓ (threshold 1 breached)
  crop_water_deficit = 0.45  → > 0.40  ✓ (threshold 2 breached)
  gdd_accumulation   = 600   → < 1200  ✓ (threshold 3 breached — bonus)

Result: CVLE triggered for Delhi wheat in 2018
```

---

### What is the Haversine Formula?

The Haversine formula computes the straight-line distance between two points on the Earth's surface given their latitude and longitude coordinates. It accounts for the Earth's curvature (unlike simple Pythagorean distance, which breaks down at larger scales).

**Why we need it:** The CGWB groundwater wells are identified by coordinates, not by city name. To assign wells to the correct city, we calculate the distance from each well to each city's central coordinates and keep only wells within 50 km.

**The formula:**
```
a = sin²(Δlat/2) + cos(lat₁)·cos(lat₂)·sin²(Δlon/2)
c = 2·arctan2(√a, √(1−a))
distance = R · c
```
Where R = 6,371 km (Earth's mean radius), lat₁/lat₂ are the two latitudes, and Δlat, Δlon are their differences in radians.

For a civil engineer: this is the standard spherical trigonometry formula for great-circle distance — the same formula used in surveying across large areas.

---

### What is the Wilcoxon Signed-Rank Test?

This is a non-parametric statistical test used to determine whether a set of paired "before" and "after" measurements are genuinely different, or whether the observed difference could have arisen by chance.

**Why non-parametric?** Parametric tests (like the t-test) assume the data follows a normal distribution. With only 3 years of "before" data and 3 years of "after" data per transition event, we cannot reliably verify that assumption. The Wilcoxon test makes no assumption about the distribution — it works by ranking the magnitudes of differences, which is more robust with small samples.

**What we're testing:**
For each detected Koppen zone transition (e.g., Delhi 2003: Cwa → BSh), we ask: *Did CVLE risk actually increase after the transition, or is it noise?*
- Pre-transition sample: CVLE probability in the 3 years before the transition
- Post-transition sample: CVLE probability in the 3 years after the transition
- Test: Is the post-transition risk distribution significantly higher?

**The p-value:**
A p-value of 0.032 means: if the transition had *no real effect*, there is only a 3.2% chance of seeing a difference this large by random variation alone. By the conventional threshold of p < 0.05, this is considered statistically significant.

---

### What is Linear Regression in This Context?

For each city, we fit a simple linear regression where:
- X = year (2000, 2001, ..., 2024)
- Y = predicted CVLE probability for that year (from the Random Forest model)

The fitted slope tells us: *How much does the CVLE risk increase per year?*

A slope of +0.0045 means the predicted risk rises by 0.45 percentage points per year. Over 25 years, that is an 11% cumulative increase in CVLE probability. If the regression's p-value < 0.05, we label the city as "deteriorating" (statistically confirmed worsening trend).

---

### What is SHAP (Feature Importance)?

When a machine learning model makes a prediction, we often want to know: *which input variables drove this particular prediction, and by how much?*

SHAP (SHapley Additive exPlanations) answers this by computing a "contribution score" for each input variable. These scores come from game theory — specifically, they represent the fair distribution of a "reward" (the prediction) among "players" (the input variables).

**Plain-language interpretation:**
If the model predicts Delhi has a 70% CVLE risk in 2018, SHAP might decompose it as:
- crop_water_deficit contributed +25% (pushed prediction up)
- monsoon_onset_doy contributed +18% (pushed prediction up)
- rainfall_annual contributed +10% (pushed prediction up)
- gdd_accumulation contributed −5% (pushed prediction down slightly)
- baseline CVLE rate for all cities = 22%

This lets us say, with mathematical backing: "The primary reason for Delhi's 2018 CVLE is water deficit (35% contribution), followed by late monsoon onset (30%)."

---

### What is the Temporal Fusion Transformer (TFT)?

The TFT is a machine learning model specifically designed for time-series prediction — situations where the sequence and timing of past observations matters, not just their magnitudes.

**For a non-CS audience:** Think of it like a skilled agronomist who looks at the last 5 years of data for a city and uses patterns in that history to predict whether next year will see crop failure. The TFT has an internal "attention" mechanism that lets it decide which past years are most relevant — it learns, for example, that two consecutive bad years are far more predictive of future failure than one isolated bad year.

**Architecture parameters:**
- Lookback window: 5 years (the model sees the 5 most recent years of data when making each prediction)
- Forecast horizon: 1 year ahead
- Input features: 17 time-varying inputs (climate + groundwater metrics that change each year) + 2 categorical static inputs (city name, primary crop) + 5 numerical static inputs (elevation, baseline suitability, etc.)
- Output: A probabilistic forecast — not just "will there be a CVLE?" but a full probability distribution expressed as 7 quantiles (10th, 20th, 30th, 50th, 70th, 80th, 90th percentile of risk)

**Why probabilistic output?** A single point estimate of "CVLE probability = 68%" is less useful than knowing "there is a 90% chance CVLE risk is at least 45%, and a 10% chance it exceeds 85%." Policymakers and farmers need to understand uncertainty, not just point estimates.

**Training split:**
- Training set: years 2000–2018 (19 years)
- Validation set: years 2000–2021 (used only to tune training; model never "sees" 2022–2024 during training)
- Early stopping: training halts when validation loss stops improving, preventing overfitting

---

### What is the Random Forest Model?

A Random Forest is an ensemble of many decision trees (here, hundreds of them), each trained on a random subset of the data. Final predictions are averaged across all trees.

**Why use it alongside TFT?**
- Faster to train and interpret than TFT
- Can provide SHAP explanations directly via its "TreeExplainer" method
- Acts as a sanity check: if the Random Forest and TFT agree on which cities are at risk, confidence is much higher than if only one model flags them
- Used by the viability trend regression (Step 11) and the crop advisory engine (Step 15)

**Key metric — F1 score:** Balances precision (of all the CVLEs the model predicted, how many were real?) and recall (of all real CVLEs, how many did the model detect?). An F1 of 0.87 (reported for the Random Forest) means the model gets 87% of detections right on both dimensions simultaneously.

---

### What is the Recharge Stress Index (RSI)?

The RSI is a four-level classification system VegShift uses to characterise how severely an aquifer's recharge capacity is compromised. It combines two independent signals:

1. **Recharge efficiency** (computed as `depth_recovery_m / rainfall_annual_mm`) — how many metres the water table recovers per mm of annual rainfall
2. **Pre-monsoon depth** (the May reading) — how deep the water table has dropped before monsoon even starts

| RSI Level | Condition | Implication |
|---|---|---|
| Critical | efficiency < 0.002 OR pre-monsoon depth > 20 mbgl | Aquifer severely compromised; pumping at >20 m is economically infeasible for most small farmers; drip-only irrigation mandatory |
| Stressed | efficiency < 0.004 OR depth > 12 mbgl | Recharge is inadequate; supplemental techniques required |
| Moderate | efficiency < 0.006 | Recharge declining but still manageable |
| Healthy | neither threshold met | Conventional irrigation acceptable |

The RSI feeds directly into irrigation method recommendations and links to government water conservation schemes.

---

### What is the Exploitation Risk Index (ERI)?

The ERI is a single composite score (0 to 1) summarising how severely a city-crop combination is stressed across all five dimensions VegShift measures. It is computed as a weighted sum:

| Component | Weight | Source |
|---|---|---|
| CVLE probability (5-year rolling mean) | 0.30 | TFT predictions |
| Drought risk (current year crop_water_deficit) | 0.25 | Climate dataset |
| Groundwater stress (pre-monsoon depth / 25 mbgl cap) | 0.20 | CGWB dataset |
| Viability trajectory (regression slope from Step 11) | 0.15 | Linear regression |
| Climate transition risk (worst risk_delta from Step 10) | 0.10 | Causal linkage analysis |

When ERI ≥ 0.65 (65% of maximum possible stress), an economic alert is triggered containing:
- The current Minimum Support Price (MSP) — the government-guaranteed floor price
- The distress price threshold (80% of MSP — below which farmers are in financial danger)
- Recommended alternative crops with better climate fit
- Nearest state government procurement centre

---

## Part 3: The 21-Step Pipeline

A **pipeline** is a chain of programs that run one after another. Each step reads input files (from previous steps or raw data), processes them, and writes output files that the next step uses. Running the entire pipeline processes 25 years of data across 10 cities, trains eight machine learning models, generates causal analyses, and produces a full interactive dashboard — all automatically.

```
Raw Data (3 sources)
        |
  ┌─────▼─────────────────────────────────────────────┐
  │  Phase 1: Data Processing (Steps 0–4)             │
  │  Standardise, aggregate, classify, extract        │
  └─────┬─────────────────────────────────────────────┘
        |
  ┌─────▼─────────────────────────────────────────────┐
  │  Phase 2: Integration + Labelling (Step 5)        │
  │  Three-way join; compute CVLE labels              │
  └─────┬─────────────────────────────────────────────┘
        |
  ┌─────▼─────────────────────────────────────────────┐
  │  Phase 3: Machine Learning (Steps 6–9)            │
  │  Train TFT, RF, LR, LSTM; compute SHAP values    │
  └─────┬─────────────────────────────────────────────┘
        |
  ┌─────▼─────────────────────────────────────────────┐
  │  Phase 4: Analysis + Validation (Steps 10–13)    │
  │  Causal linkage; trend regression; controls       │
  └─────┬─────────────────────────────────────────────┘
        |
  ┌─────▼─────────────────────────────────────────────┐
  │  Phase 5: Advisory Engines (Steps 15–17)          │
  │  Crop advisory; irrigation strategy; ERI         │
  └─────┬─────────────────────────────────────────────┘
        |
  ┌─────▼─────────────────────────────────────────────┐
  │  Phase 6: Visualisation (Step 14)                │
  │  11-panel interactive dashboard                  │
  └─────┬─────────────────────────────────────────────┘
        |
  ┌─────▼─────────────────────────────────────────────┐
  │  Phase 7: Comparative Research (Steps 20–23)     │
  │  8-model benchmark; ablation; uncertainty        │
  └───────────────────────────────────────────────────┘
```

---

### Phase 1: Data Collection and Standardisation (Steps 0–4)

#### Step 0: Master Index
**Input:** No external data — just hardcoded lists of 10 city names and years 2000–2024.

**Output:** `data/processed/master_index.csv` — 250 rows (10 cities × 25 years)

**Purpose:** Creates the backbone join table. Every subsequent step produces outputs keyed by `(city, year)`. Having this master index ensures that even if a city is missing from a dataset in a particular year, the gap appears explicitly as a row with NaN values rather than disappearing silently. This makes data quality auditing possible.

```
city         year
Delhi        2000
Delhi        2001
...
Pune         2024
```

---

#### Step 0b: Preprocess Raw Climate Dataset
**Input:** `data/raw/climate/india_2000_2024_daily_weather.csv`

**Output:** `data/processed/kaggle_climate.csv`

**What it does:**
- Renames inconsistently named raw columns to a standardised schema (e.g., `Max Temp (°C)` → `Temp_Max`)
- Converts wind speed from km/h to m/s (divide by 3.6)
- Derives the humidity column using the Steadman inversion (see Part 1, Dataset 1)
- Validates all values against physically plausible ranges (temperature: −10°C to 55°C for India; rainfall: 0–500 mm/day; wind: 0–50 m/s)
- Flags or removes records that fail validation

This is an essential step because raw observational data frequently has encoding errors, missing values, and inconsistent units.

---

#### Step 1: Köppen Classification
**Input:** Daily climate data (from Step 0b)

**Output:** `data/processed/koppen_annual.csv` — 250 rows, one per city-year

**What it does:** For each city-year, computes:
- `T_ann`: annual mean temperature (°C)
- `P_ann`: total annual precipitation (mm)
- `T_coldest`: mean temperature of the coldest month
- `T_hottest`: mean temperature of the hottest month
- `P_summer`: rainfall falling in summer months (Apr–Sep) as a fraction of annual total

Then applies the Köppen classification logic (from Part 2) to assign a zone code.

**Output example:**
```
city      year  koppen_zone  T_ann   P_ann   T_coldest
Delhi     2000  Cwa          24.5    680     13.2
Delhi     2004  BSh          26.8    640     15.1
Delhi     2018  BSh          28.1    500     16.8
```

The shift from Cwa (humid subtropical) to BSh (semi-arid hot) between 2000 and 2004 for Delhi is a significant signal: Delhi's climate crossed from temperate-with-adequate-rain to semi-arid. This is the climate reorganisation that precedes crop stress.

---

#### Step 1b: Transition Detection
**Input:** `koppen_annual.csv`

**Output:** `data/output/transition_report.json`

**What it does:** Scans each city's year-by-year zone sequence and identifies **persistent** zone transitions.

**The persistence requirement:** A transition is only recorded if the new zone holds for **3 or more consecutive years**. This filters out single-year anomalies caused by unusually wet or dry years that revert the following year. The intent is to detect structural climate reorganisation, not weather variability.

**Algorithm illustration:**
```
Zones over time: Cwa, Cwa, Cwa, BSh, BSh, BSh, BSh, BSh
Years:          2000 2001 2002 2003 2004 2005 2006 2007

Analysis: The zone changes at 2003. The new zone (BSh) holds through at least 2003, 2004, 2005 (3 years).
→ Transition recorded: Delhi, 2003, Cwa → BSh, confirmed by 5 consecutive years of BSh.
```

**Output structure (JSON format):**
```json
{
  "city": "Delhi",
  "transition_year": 2003,
  "from_zone": "Cwa",
  "to_zone": "BSh",
  "years_confirmed": 5
}
```

---

#### Step 2: Climate Feature Aggregation
**Input:** Daily climate data (365 records per city-year)

**Output:** `data/processed/climate_annual.csv` — 250 rows, 12 agronomic features per row

This is the step that converts raw meteorological data into crop-science-relevant annual metrics. Full list of computed features:

| Feature | Calculation | Physical Significance |
|---|---|---|
| `temp_mean` | Mean of daily averages | Baseline thermal environment for the growing season |
| `temp_max_mean` | Mean of daily maxima | Captures heat stress potential |
| `rainfall_annual` | Sum of all daily rainfall | Total atmospheric water input |
| `n_dry_months` | Count of months with total < 60 mm | A month below 60 mm is considered agronomically dry for most Indian crops |
| `monsoon_onset_doy` | First day when 5-day rolling rainfall ≥ 25 mm | Defines the start of the planting window |
| `sowing_window_miss` | (onset_doy − optimal_doy) / optimal_doy, floored at 0 | Fraction by which the planting window was delayed |
| `gdd_accumulation` | Σ max(T_daily_mean − T_base, 0) over Apr–Sep | Total heat units available for crop development |
| `crop_water_deficit` | (crop_water_req − rainfall_annual) / crop_water_req | Fractional rainfall shortfall relative to crop need |
| `humidity_mean` | Mean of derived daily RH | Affects transpiration and disease pressure |
| `wind_mean` | Mean daily wind speed (m/s) | Affects evapotranspiration and physical crop stress |

**Crop-specific computation:**
`gdd_accumulation` and `crop_water_deficit` are computed *per crop*, not generically. A Delhi wheat record uses wheat's T_base = 5°C and wheat's water requirement of 450 mm; a Delhi cotton record uses cotton's T_base = 15°C and 700 mm requirement. This means Step 2 produces one set of features per city-year-crop combination when crop-specific fields are included.

---

#### Step 3: Groundwater Aggregation
**Input:** CGWB raw well data

**Output:** `data/processed/groundwater_annual.csv` — 250 rows, 6 features per row

**Processing steps:**

1. **Parse the raw CGWB format:** The raw data is in a wide format (one row per well, columns named like `Jan_2000`, `May_2000`, etc.). This is reshaped to a long format: one row per (well, year, measurement_month).

2. **Geocode each well:** Match the well's district/state name to geographic coordinates. Wells without geocodable addresses are dropped.

3. **Spatial filter:** For each city, retain only wells within 50 km (Haversine formula). The 50 km radius is chosen to balance coverage (cities have wells spread around them) against contamination (wells too far away may reflect a different hydrological regime).

4. **Aggregate across wells:** For each city-year-measurement_month, take the median depth of all retained wells. The median is more robust than the mean because a single very deep or very shallow well (perhaps near a large irrigation project or factory) could distort the city average.

5. **Compute derived metrics:**
   - `pre_monsoon_depth_mbgl`: The May depth — how depleted is the aquifer at its driest point?
   - `post_monsoon_depth_mbgl`: The November depth — how well did the monsoon recharge the aquifer?
   - `depletion_rate`: January depth this year minus January depth last year (positive = aquifer deepening = bad)
   - `depth_recovery_m`: May depth minus August depth (positive = aquifer rising = good)
   - `recharge_efficiency`: depth_recovery_m / rainfall_annual_mm (normalised recharge per mm of rain)

**Imputation for missing cities and years:** Detailed in Part 4.

---

#### Step 4: FAO GAEZ Raster Extraction
**Input:** GeoTIFF suitability rasters, one file per crop

**Output:** `data/processed/gaez_baseline.csv` — 10 rows (one per city), with columns for each crop's baseline suitability score

**How raster extraction works:**
A GeoTIFF is like a spreadsheet where each cell corresponds to a geographic tile of land. Given a city's coordinates (latitude, longitude), a geographic lookup finds which grid cell the city falls in, and reads that cell's value.

For Delhi at coordinates (28.6°N, 77.2°E), we extract:
```
wheat_suitability = 6
cotton_suitability = 4
rice_suitability = 5
sugarcane_suitability = 3
```

This is a static, one-time extraction — the FAO baseline does not change year-to-year. It is joined to the master dataset in Step 5 to provide context for how much climate has degraded from the historical optimum.

---

### Phase 2: Data Integration and Labelling (Step 5)

#### Step 5: Three-Way Join and CVLE Label Computation
**Input:** All five processed files (master index, climate annual, groundwater annual, GAEZ baseline, Köppen annual)

**Output:** `data/processed/vegshift_master.csv` — 250 rows, approximately 30 columns, 0 NaN values in any key column

This is the heart of the pipeline. Every upstream step feeds here; every downstream step reads from this file.

**The join process:**
The master index (250 rows: 10 cities × 25 years) is joined to each dataset by `(city, year)` key. The FAO GAEZ baseline has no year dimension (it is a static historical baseline), so it is joined by `city` only — the same baseline suitability score is repeated for all 25 years of a city.

**Two-pass imputation for missing groundwater values:**

Pass 1 — city-group mean:
```python
for col in ['pre_monsoon_depth_mbgl', 'post_monsoon_depth_mbgl', 'recharge_efficiency', ...]:
    df[col] = df.groupby('city')[col].transform(lambda x: x.fillna(x.mean()))
```
This fills a missing value with that same city's average over all available years. For example, if Delhi 2003 groundwater is missing, it fills with Delhi's 23-year average depth.

Pass 2 — global median fallback:
```python
global_median = df[col].median()
df[col] = df[col].fillna(global_median)
```
This handles the case where an entire city has no values for a column (e.g., Kolkata has no May pre-monsoon readings at all). After Pass 1, the city-mean is NaN (because the mean of all-NaN is NaN). Pass 2 fills the remaining NaN values with the median across all cities and years — a reasonable conservative estimate.

**Imputation flag column (`gw_imputed`):**
- `0` = authoritative measurement from a well within 50 km
- `1` = filled by mean imputation (no well in range, or year beyond CGWB 2022 cutoff)
- `2` = Jaipur-specific: nearest-wells from another state used

**Compound feature computation:**
```python
# Dual-deficit flag: both atmospheric and subsurface water systems failing
dual_deficit = (crop_water_deficit > 0.4) AND (recharge_efficiency < 0.30)

# GDD adequacy flag: has the crop received enough heat to mature?
gdd_adequate = (gdd_accumulation >= crop_gdd_min)
```

**CVLE label generation algorithm:**
```python
def compute_cvle(group):
    """
    group = all rows for one city, sorted by year
    Returns a binary column: 1 = CVLE in this year, 0 = no CVLE
    """
    cvle = [0] * len(group)
    for i in range(1, len(group)):
        # Condition 1: dual-deficit in BOTH current and previous year
        consec = dual_deficit[i] and dual_deficit[i-1]

        # Condition 2: at least 2 of 3 thresholds breached in current year
        t1 = sowing_window_miss[i] > 0.6
        t2 = crop_water_deficit[i] > 0.4
        t3 = not gdd_adequate[i]
        multi_threshold = (t1 + t2 + t3) >= 2

        if consec and multi_threshold:
            cvle[i] = 1
    return cvle
```

The result is a binary column: for each of the 250 city-year rows, CVLE = 0 or 1.

---

### Phase 3: Machine Learning (Steps 6–9)

#### Step 6: Train the Temporal Fusion Transformer (TFT)
**Input:** `vegshift_master.csv`

**Output:** `data/output/vegshift-tft-best.ckpt` (saved model checkpoint)

**What the model learns:** Given 5 consecutive years of climate + groundwater + GAEZ data for a city, predict the probability that the following year will be a CVLE year.

**Feature categories fed to TFT:**

*Time-varying features (change each year, 17 total):*
- `temp_mean`, `rainfall_annual`, `n_dry_months`, `monsoon_onset_doy`
- `sowing_window_miss`, `gdd_accumulation`, `crop_water_deficit`
- `pre_monsoon_depth_mbgl`, `post_monsoon_depth_mbgl`, `depletion_rate`, `recharge_efficiency`
- `dual_deficit`, `gdd_adequate`
- `koppen_zone_encoded` (the zone code converted to a number)
- `humidity_mean`, `wind_mean`, `baseline_suitability`

*Static categorical features (constant for a city, 2 total):*
- `city_id` (encoded city name)
- `primary_crop_id` (encoded primary crop for that city)

*Static real-valued features (constant for a city, 5 total):*
- Latitude, longitude
- Elevation above sea level
- Baseline suitability score
- Distance from nearest major river

**Why the TFT's attention mechanism is valuable:**
After training, the model's attention weights can be extracted and interpreted. If the model predicts high CVLE risk for Delhi in 2020, the attention weights might show: "50% of the predictive signal came from 2019, 30% from 2018, 10% from 2017." This is powerful evidence that recent years (not distant history) drive viability loss — consistent with cumulative aquifer depletion.

**Training protocol:**
- Batch size: 32 city-year sequences
- Optimiser: Adam (a gradient descent variant)
- Learning rate: starts at 0.001, reduced when validation loss plateaus
- Early stopping: training halts after 10 epochs with no validation improvement
- Device: CPU (no GPU required; dataset is small enough at 250 rows)

---

#### Step 7: TFT Prediction and Attention Extraction
**Input:** Best TFT checkpoint + `vegshift_master.csv`

**Output:**
- `data/output/tft_predictions.csv` — predicted CVLE probability (7 quantiles) for each city-year
- `data/output/tft_attention_weights.json` — attention weights for each prediction

The attention weights JSON structure:
```json
{
  "Delhi": {
    "2020": {
      "lag_1": 0.40,   // 40% attention paid to 2019 data
      "lag_2": 0.30,   // 30% attention paid to 2018 data
      "lag_3": 0.20,   // 20% attention paid to 2017 data
      "lag_4": 0.07,   // 7% attention paid to 2016 data
      "lag_5": 0.03    // 3% attention paid to 2015 data
    }
  }
}
```

---

#### Step 8: Train Baseline Models
**Input:** `vegshift_master.csv`

**Output:** `models/baselines/` (RF, LR, XGBoost, LightGBM, LSTM weights + scaler), `data/output/baseline_metrics.json`, `data/output/predictions/*_predictions.csv`

Five models are trained as comparison points against the TFT. Each saves its per-row prediction probabilities to `data/output/predictions/` so Step 21 can compare them uniformly.

**Random Forest (RF):**
- Non-temporal: uses the current year's features only, no sequence
- 200 decision trees, each trained on a random 70% sample of the data
- Each tree makes a binary prediction; majority vote = final prediction
- Primary use: providing SHAP explanations (Step 9) and viability trend scoring (Step 11)

**Logistic Regression (LR):**
- Linear model: probability of CVLE = sigmoid(w₁·x₁ + w₂·x₂ + ... + b)
- Most interpretable: the coefficient wᵢ for each feature directly shows its direction and magnitude of influence
- Weakest performer (misses non-linear interactions) but provides a reliability floor

**XGBoost:**
- Gradient-boosted decision tree ensemble; handles non-linear feature interactions better than plain RF
- Uses `scale_pos_weight` to compensate for class imbalance (CVLEs are rare events)
- Trained with 200 trees, max depth 6, learning rate 0.05

**LightGBM:**
- Gradient boosting variant with leaf-wise tree growth; faster and often more accurate than XGBoost on tabular data
- Same class-imbalance handling as XGBoost
- Provides an independent ensemble check: if LightGBM and XGBoost agree on a city's risk, confidence is high

**LSTM (Long Short-Term Memory):**
- Older recurrent architecture; uses sequential data (5-year lookback), same as TFT
- Compared against TFT to quantify whether TFT's attention mechanism adds real value over a standard RNN

If TFT and LSTM achieve similar F1 scores, TFT's extra parameters may be overfitting; if TFT significantly outperforms LSTM, the attention mechanism is genuinely capturing patterns LSTM cannot.

---

#### Step 9: SHAP Explainability Analysis
**Input:** Trained Random Forest + held-out test data

**Output:** `data/output/shap_explanation.json`

**What is computed:**
1. **Global feature importance:** Average SHAP magnitude across all predictions. Shows which features matter most overall.

Example global ranking:
```
crop_water_deficit:     SHAP = 0.35  (35% of prediction driven by this)
depletion_rate:         SHAP = 0.28
dual_deficit:           SHAP = 0.22
sowing_window_miss:     SHAP = 0.08
gdd_accumulation:       SHAP = 0.04
rainfall_annual:        SHAP = 0.03
```

2. **Per-city importance:** For each city, which features drive predictions most strongly?
   - Delhi: `sowing_window_miss` and `monsoon_onset_doy` (timing of monsoon most critical)
   - Jaipur: `crop_water_deficit` and `rainfall_annual` (absolute water shortage is primary)
   - Hyderabad: `depletion_rate` (groundwater decline is the dominant driver)

---

### Phase 4: Analysis and Validation (Steps 10–13)

#### Step 10: Causal Linkage Analysis
**Input:** `vegshift_master.csv` + `transition_report.json`

**Output:** `data/output/transition_cvle_linkage.json`

**The research question:** When a city's Köppen zone transitions to a drier/hotter category, does its crop viability risk measurably increase afterwards? This tests whether the VegShift system can establish not just correlation (both things went bad) but a plausible temporal causal structure (zone shift preceded the risk increase).

**Method:**
For each detected zone transition:
1. Collect the TFT-predicted CVLE probabilities for the 3 years immediately before the transition year
2. Collect the TFT-predicted CVLE probabilities for the 3 years immediately after
3. Run the Wilcoxon signed-rank test on the paired before/after values
4. Record the lag: how many years elapsed between the transition year and the first year with CVLE = 1?

**Output example:**
```json
{
  "city": "Delhi",
  "transition_year": 2003,
  "from_zone": "Cwa",
  "to_zone": "BSh",
  "pre_risk_mean": 0.12,
  "post_risk_mean": 0.45,
  "risk_delta": 0.33,
  "p_value": 0.032,
  "significant": true,
  "cvle_lag_years": 15
}
```

**Interpreting the 15-year lag for Delhi:**
The zone transitioned in 2003 but the first CVLE wasn't until 2018. This long lag reflects gradual aquifer depletion: immediately after the zone transition, farmers compensated by pumping more groundwater. Over 15 years, that accelerated extraction depleted the aquifer to the point where it could no longer compensate for rainfall deficits — at which point the dual-deficit condition was met and CVLEs started occurring. This is a textbook example of how water infrastructure can mask climate stress for years before a sudden failure.

---

#### Step 11: Viability Trend Regression
**Input:** `vegshift_master.csv` + `rf_baseline.pkl` + `scaler.pkl`

**Output:** `data/output/viability_trend_report.json`

**The research question:** Are crops in at-risk cities getting steadily less viable over 25 years, or are conditions fluctuating randomly around a stable mean?

**Method:**
1. Run the Random Forest's `predict_proba` method on all 250 rows to get a CVLE risk probability for every city-year (this is different from the binary CVLE label — it is a continuous probability used for regression)
2. For each city, fit ordinary least-squares (OLS) linear regression: risk ∼ year
3. Classify the trend based on slope and p-value

**Output per city:**
```json
{
  "city": "Delhi",
  "slope": 0.0045,
  "intercept": -8.74,
  "r_squared": 0.62,
  "p_value": 0.008,
  "trend": "deteriorating"
}
```

**Interpretation:** Delhi's CVLE risk has increased by 0.45 percentage points per year over 2000–2024. The R² of 0.62 means 62% of year-to-year variance is explained by the simple linear trend (the rest is year-to-year weather noise). This is a strong and statistically highly significant trend (p = 0.008).

---

#### Step 12: Control City Validation
**Input:** `viability_trend_report.json` + `transition_report.json` + `crop_viability_events.json`

**Output:** Printed validation report (not saved to file)

**Purpose:** The entire pipeline could produce plausible-looking but wrong results if there are systematic errors in data preprocessing, feature engineering, or CVLE labelling. Control cities provide an independent check.

**Control cities and why they were chosen:**
- **Pune:** High-altitude Deccan plateau; stable subtropical climate; diverse rainfall; not expected to show severe water stress
- **Kolkata:** Tropical monsoon (Am); abundant annual rainfall (1,600–1,800 mm); no water scarcity expected
- **Mumbai:** Coastal tropical; highest annual rainfall among the 10 cities (~2,200 mm); coastal aquifer recharge mechanisms differ from inland cities

**What we check for each control city:**

| Check | Pass condition | Fail interpretation |
|---|---|---|
| Viability trend | "stable" (p ≥ 0.05) | Pipeline is generating false deterioration in cities known to be stable |
| CVLE count | = 0 | CVLE labelling is triggering on noise |
| Transition count | = 0 | Köppen classification is over-sensitive |

If any control city fails, the pipeline is stopped and the relevant step is debugged. The control city check is an explicit anti-overfitting mechanism — it forces the model to be selective.

---

#### Step 13: Recharge Grid Export
**Input:** `vegshift_master.csv`

**Output:** `data/output/groundwater_recharge_grid.json`

A simple pivot table transformation: reshapes the `recharge_efficiency` column into a nested dictionary keyed by city and year, for consumption by the dashboard's aquifer health charts.

```json
{
  "Delhi":  {"2000": 0.010, "2001": 0.009, "2002": 0.009, "2003": 0.008, ... "2022": 0.005},
  "Jaipur": {"2000": 0.006, "2001": 0.005, ... "2022": 0.003}
}
```

A declining value over the time series directly visualises aquifer degradation: each millimetre of monsoon rain is recovering less and less of the water table.

---

### Phase 7: Comparative Research (Steps 20–23)

These four steps constitute VegShift's model benchmarking study. They run after the core pipeline and require that Steps 6–9 have already produced predictions. Their outputs feed the `/compare` page in the web app.

---

#### Step 20: Train Deep Sequence Models (TCN + Transformer)
**Input:** `vegshift_master.csv`

**Output:** `models/deep_models/` (TCN and Transformer weights, `hparams.json`), `data/output/deep_model_metrics.json`, `data/output/predictions/tcn_predictions.csv`, `data/output/predictions/transformer_predictions.csv`

Two additional deep-learning sequence classifiers are trained to extend the comparison set beyond TFT and LSTM:

**TCN (Temporal Convolutional Network):**
- Uses dilated causal convolutions to process sequences in parallel (unlike RNNs which process left-to-right)
- Configurable depth and channel width (default: 4 layers, 64 channels per layer, 50 epochs)
- Does not have an explicit attention mechanism; learns temporal patterns through receptive field stacking

**Vanilla Transformer:**
- Self-attention architecture similar to TFT but without the variable selection networks, gating, or static covariate encoders
- Serves as an ablation of TFT: if the vanilla Transformer performs nearly as well as TFT, the additional complexity in TFT is not justified; if TFT is substantially better, the gating and variable selection are adding real value
- Architecture: `d_model=64`, 4 attention heads, configurable layers

Architecture hyperparameters are saved to `hparams.json` so Step 23 can reconstruct the models for MC-dropout uncertainty estimation without re-training.

---

#### Step 21: Unified Comparative Evaluation
**Input:** All prediction CSVs from `data/output/predictions/`, `data/output/tft_predictions.csv`, `data/processed/vegshift_master.csv`

**Output:** `data/output/comparative/metrics_table.json`, `comparative/stats_tests.json`, `comparative/zone_breakdown.json`

This is the central benchmarking step. It computes a uniform set of metrics for all 8 models on the same test split (years ≥ 2022), enabling direct comparison:

| Metric | Definition |
|---|---|
| Accuracy | Fraction of correct binary predictions |
| Precision | Of all predicted CVLEs, fraction that were genuine |
| Recall | Of all genuine CVLEs, fraction that were detected |
| F1 | Harmonic mean of precision and recall |
| AUC | Area under the ROC curve (threshold-independent skill) |
| Brier | Mean squared error of probability estimates (lower = better calibrated) |

**Pairwise statistical tests (`stats_tests.json`):**
For every pair of models, a Wilcoxon signed-rank test is run on their per-sample AUC contributions. If p < 0.05, the performance difference is statistically significant. This prevents claiming one model is "better" when the difference could be random chance on a small dataset.

**Köppen zone breakdown (`zone_breakdown.json`):**
Each model's AUC is computed separately within each Köppen zone (BSh, Cwa, Am, etc.). This reveals whether certain models are zone-specialist or generalist — for example, a model might have high overall AUC but perform poorly in semi-arid (BSh) zones where CVLE risk is highest.

---

#### Step 22: Feature Group Ablation Study
**Input:** `vegshift_master.csv`

**Output:** `data/output/ablation_results.json`

The ablation study answers: *which feature group contributes most to CVLE predictability?*

**Feature groups (defined in `research_shared.py`):**

| Group | Features Included |
|---|---|
| `climate` | `temp_mean`, `temp_max`, `rainfall_annual`, `wind_speed`, `humidity`, `n_dry_months` |
| `phenology` | `monsoon_onset_doy`, `sowing_window_miss`, `gdd_accumulation`, `gdd_adequate` |
| `hydrology` | `pre_monsoon_depth_mbgl`, `depletion_rate`, `recharge_efficiency`, `crop_water_deficit`, `dual_deficit` |
| `static_context` | `gaez_baseline_class`, `koppen_zone_enc` |
| `all` | All 17 features combined |

For each group, three models are trained and evaluated: RF, XGBoost, and LSTM. AUC is the comparison metric. The output is a nested JSON: `results[group_name][model_name] = AUC`.

**Interpretation:** If removing the `hydrology` group causes the largest AUC drop, groundwater features are the most informative. If `all` AUC ≈ `climate` AUC, the non-climate features add little signal. In practice, the `hydrology` group (particularly `dual_deficit` and `depletion_rate`) tends to be the single most predictive group — validating the dual-deficit design decision.

---

#### Step 23: Uncertainty Quantification
**Input:** All model weights + `data/processed/vegshift_master.csv` + `data/output/tft_predictions.csv`

**Output:** `data/output/uncertainty_metrics.json`

This step measures how *well-calibrated* each model's probability estimates are — i.e., whether a predicted 70% probability of CVLE actually corresponds to about 70% of events being CVLEs in that bin.

**Metrics computed:**

| Metric | Definition | Interpretation |
|---|---|---|
| ECE (Expected Calibration Error) | Weighted mean gap between predicted probabilities and observed frequencies across bins | Lower = better calibrated; 0 = perfect calibration |
| Brier score | Mean squared error of probability predictions | Lower = better; accounts for both calibration and sharpness |
| Mean std (MC dropout models) | Average standard deviation across N stochastic forward passes | Measures model uncertainty; very low std = overconfident |
| Interval width (90%) | 2 × 1.645 × mean_std | Width of the 90% confidence interval in probability units |

**MC Dropout method:** For neural network models (LSTM, TCN, Transformer), the dropout layers are kept active at inference time. Running N=50 stochastic forward passes produces a distribution of predictions. The mean is the probability estimate; the standard deviation quantifies the model's epistemic uncertainty.

**RF tree variance method:** For the Random Forest, each of the 200 trees produces its own probability. The mean and standard deviation across tree predictions serve as point estimate and uncertainty measure respectively.

**TFT:** ECE and Brier score are computed from the saved median quantile predictions. Full quantile interval widths (directly from TFT's 7-quantile output) are available by re-running Step 7 with `--mode quantiles`.

---

### Phase 5: Advisory Engines (Steps 15–17)

#### Step 15: Crop Advisory Engine
**Input:** `vegshift_master.csv`, `viability_trend_report.json`

**Output:** `data/output/crop_advisory.json`

This engine scores all 14 Indian crops tracked in VegShift (wheat, mustard, rice, cotton, sugarcane, groundnut, sorghum, ragi, chickpea, lentil, maize, sunflower, bajra, barley) for suitability in each city, using a 100-point composite score built from five axes:

| Axis | Weight | How Computed |
|---|---|---|
| Zone compatibility | 30 pts | Does the city's current Köppen zone match the crop's preferred zone from FAO GAEZ? |
| Temperature stress | 20 pts | How far is the mean temperature from the crop's optimal temperature range? |
| Rainfall adequacy | 20 pts | What fraction of the crop's water requirement does rainfall meet? |
| Groundwater stress | 15 pts | RSI level penalty — higher stress = lower score |
| 5-year climate trajectory | 15 pts | Is the relevant climate fit improving or narrowing over the last 5 years? |

**The trajectory penalty is the key innovation:** A crop that is marginally viable now but whose climate is steadily becoming less suitable scores lower than a drought-tolerant alternative that is gaining climate headroom. This forward-looking adjustment prevents recommending crops that will fail within a few years even if they still technically grow today.

Results are ranked descending per city. Farmers and policymakers see: "For Delhi, switch from wheat to barley or bajra — both are more drought-tolerant and have improving trajectory scores."

---

#### Step 16: Irrigation Strategy Engine
**Input:** `vegshift_master.csv`, `kaggle_climate.csv`, `crop_advisory.json`

**Output:** `data/output/irrigation_strategy.json`

This engine translates RSI levels (from Part 2) into actionable irrigation prescriptions. For each city:

1. Classify RSI level using the thresholds from Part 2
2. Prescribe irrigation method (critical → drip only; stressed → drip/sprinkler + rainwater harvesting; moderate → sprinkler; healthy → conventional)
3. Compute optimal kharif sowing window: the month with peak rainfall probability from the historical record (Mode of months where monsoon onset fell across all 25 years)
4. List applicable government schemes:
   - **PMKSY** (Pradhan Mantri Krishi Sinchayee Yojana): National irrigation subsidy scheme
   - **PM-KUSUM**: Solar pump subsidy for groundwater-dependent farmers
   - **MGNREGS**: Employment guarantee scheme — can fund water harvesting structure construction
   - **RKVY** (Rashtriya Krishi Vikas Yojana): Agricultural development grants
   - **PMFBY** (Pradhan Mantri Fasal Bima Yojana): Crop insurance scheme

This links physical measurements directly to farmer-actionable government resources.

---

#### Step 17: Exploitation Risk Engine
**Input:** `vegshift_master.csv`, `viability_trend_report.json`, `transition_cvle_linkage.json`, `crop_advisory.json`

**Output:** `data/output/exploitation_risk_report.json`

Computes the ERI score (described in Part 2) for each city using the latest available year's data. When ERI ≥ 0.65:

```json
{
  "city": "Delhi",
  "eri_score": 0.71,
  "alert": true,
  "msp_2024_25": 2275,              // INR per quintal (100 kg) for wheat
  "distress_threshold": 1820,       // 80% of MSP
  "alternative_crops": ["barley", "bajra", "chickpea"],
  "procurement_centre_url": "https://..."
}
```

The distress threshold (80% of MSP) is the price below which selling a crop results in below-cost recovery — a financial early warning for farmer distress.

---

### Phase 6: Visualisation (Step 14)

#### Step 14: Interactive Dashboard
**Output:** Web application at `http://localhost:8050`

Built with Plotly Dash, a Python framework that renders interactive web charts. Launched in the background by the main pipeline orchestrator after all analysis steps complete. Eleven panels:

1. **Sowing Window Drift** — Scatter plot of monsoon onset day-of-year vs. optimal sowing date for each city, with vertical markers at transition years. A widening gap = sowing window getting missed more frequently.

2. **Dual-Deficit Heatmap** — A grid (cities × years) coloured red where dual_deficit = 1 and white where 0. Clusters of red indicate sustained multi-year crisis periods.

3. **CVLE Timeline** — Bar chart showing how many CVLE events each city has experienced across the 25 years. Control cities (Pune, Kolkata, Mumbai) should show zero bars.

4. **Transition → CVLE Linkage Table** — All detected zone transitions with their Wilcoxon p-value, pre/post risk delta, and CVLE lag years. Sortable by significance.

5. **Recharge Efficiency Trend** — Line chart of recharge efficiency (m/mm) from 2000–2022 per city. A falling line = aquifer degradation. This is analogous to a hydrograph showing aquifer depletion over decades.

6. **Köppen Zone History** — Scatter plot where each point represents one city-year, coloured by zone code. Shifts in colour pattern indicate zone transitions.

7. **SHAP Feature Importance** — Horizontal bar charts showing global and per-city SHAP values. Allows comparing what drives CVLE prediction in Jaipur (water deficit) vs. Delhi (monsoon timing).

8. **Trend Report** — Table of all cities' viability slope, R², p-value, and trend classification, colour-coded (red = deteriorating, green = stable/improving).

9. **Crop Advisory** — Table of the top-ranked crops per city with their 100-point scores broken down by axis. Allows filtering by city and year.

10. **Irrigation Strategy** — Map/table showing RSI level per city, with colour coding. Clicking a city shows its recommended irrigation method, sowing window, and applicable schemes.

11. **Exploitation Risk** — Stacked horizontal bar chart where each bar is a city, stacked segments show ERI component contributions, and a vertical line at 0.65 marks the alert threshold.

**Standalone launch:**
```bash
python pipeline/step14_dashboard.py
# Then open http://localhost:8050 in browser
```

---

## Part 4: Data Quality and Special Cases

### Complete Missing Data Inventory

| Issue | Root Cause | Fix Applied | Confidence Level |
|---|---|---|---|
| Humidity missing | Raw Kaggle dataset has no RH column | Steadman apparent-temperature inversion; validated against climatological norms | High (validated against Mumbai ~90%, Jaipur ~65%) |
| Pre-2005 groundwater sparse | CGWB national coverage was limited before 2005 | Backfilled using 2005–2007 average depletion rate per city | Moderate (assumes early 2000s trend matched 2005–2007) |
| Jaipur groundwater entirely absent | Rajasthan state absent from CGWB well network | 5 nearest wells from neighbouring states (Gujarat, Haryana); flagged `gw_imputed=2` | Low-moderate (different geological unit; use with caution) |
| Kolkata pre-monsoon depth all NaN | CGWB has no May readings for wells near Kolkata | Two-pass imputation: city mean fails (all NaN) → global median across all cities | Moderate (global median is a conservative central estimate) |
| 2023–2024 groundwater absent | CGWB dataset ends at 2022 | Forward-fill using city-group mean / global median fallback; flagged `gw_imputed=1` | Low (2 years extrapolated beyond data range) |
| Occasional negative humidity from Steadman inversion | Formula overshoots in extreme dry/windy conditions | Clipped to minimum 5% RH | High (physical floor is well-justified) |

### Data Provenance Flags

The `gw_imputed` column in `vegshift_master.csv` records the data source quality for every row:

- **`gw_imputed = 0`:** A real CGWB observation well within 50 km contributed to this reading. The most authoritative data.
- **`gw_imputed = 1`:** No well in range, or the year is beyond CGWB's 2022 cutoff. Value was filled by city-group mean or global median imputation.
- **`gw_imputed = 2`:** Jaipur only. Values derived from wells in neighbouring states with different geological characteristics.

Any analysis of Jaipur results should note that groundwater figures carry additional uncertainty.

### Known Limitations and Their Implications

1. **GAEZ raster encoding (values 8–10):** Some raster cells encode irrigated potential (what the crop could do with full irrigation). These are clipped to 7 (the maximum rainfed suitability). Without this clip, cities with irrigation infrastructure would appear artificially suitable regardless of rainfall, masking the climate stress VegShift is designed to detect.

2. **Jaipur groundwater extrapolation:** Using wells from Gujarat or Haryana as proxies for Rajasthan introduces geological uncertainty. Rajasthan underlies the Thar Desert, which has a distinctly different aquifer structure (hard-rock, low-porosity formations) from the alluvial aquifers in neighbouring states. Jaipur ERI and RSI results should be treated as indicative, not authoritative.

3. **Pre-2005 confidence:** Climate data is well-measured back to 2000 (daily station records). Groundwater pre-2005 is sparse and backfilled. CVLEs detected before 2005 depend more heavily on imputed groundwater values.

4. **CVLE conservatism:** The dual-deficit persistence + multi-threshold design was deliberately tuned to reduce false positives. As a consequence, some genuine viability loss events may be missed (false negatives). The system is more useful as an early warning system for confirmed crises than as an exhaustive census of every stressed year.

5. **Static FAO GAEZ baseline:** The suitability maps reflect 1981–2010 climate. They do not update yearly. This is appropriate for our use case (we *want* to measure deviation from historical norms) but means the baseline itself could become outdated if FAO releases new maps.

---

## Part 5: Key Outputs Explained

| Output File | What It Contains | Example Value |
|---|---|---|
| `master_index.csv` | 250-row backbone join table | city="Delhi", year=2018 |
| `kaggle_climate.csv` | Preprocessed daily weather with derived humidity | T_max=42, RH=38%, wind=5 m/s |
| `koppen_annual.csv` | Annual Köppen zone per city-year | Delhi 2003: BSh |
| `transition_report.json` | Persistent zone transitions with confirmation count | Delhi: Cwa→BSh in 2003, 5 years confirmed |
| `climate_annual.csv` | 12 annual agronomic features per city-year | GDD=600, water_deficit=0.45, onset_doy=182 |
| `groundwater_annual.csv` | 6 annual groundwater metrics per city-year | May depth=25 m, recharge_eff=0.005 |
| `gaez_baseline.csv` | Baseline suitability scores per city per crop | Delhi wheat: 6 (very suitable) |
| `vegshift_master.csv` | 250-row master dataset with all features + CVLE labels | 30 columns, 0 NaN, CVLE=1 for Delhi 2018 |
| `vegshift-tft-best.ckpt` | Trained TFT model weights | — |
| `tft_predictions.csv` | 7-quantile CVLE probability forecasts | Delhi 2020: p50=0.72, p90=0.89 |
| `tft_attention_weights.json` | Which past years drove each TFT prediction | Delhi 2020: lag1=40%, lag2=30% |
| `models/baselines/` | Serialised RF, LR, XGBoost, LightGBM, LSTM models + scaler | — |
| `baseline_metrics.json` | Test-set F1, precision, recall, AUC for all 5 baseline models | RF: F1=0.87, LR: F1=0.79, LSTM: F1=0.83 |
| `models/deep_models/` | Serialised TCN and Transformer models + hparams.json | — |
| `deep_model_metrics.json` | AUC and F1 for TCN and Transformer | — |
| `predictions/*_predictions.csv` | Per-row probability outputs for all 7 non-TFT models | Used by Step 21 unified evaluation |
| `comparative/metrics_table.json` | Full 6-metric benchmark across all 8 models on held-out test set | — |
| `comparative/stats_tests.json` | Wilcoxon p-values for all pairwise model comparisons | — |
| `comparative/zone_breakdown.json` | Per-Köppen-zone AUC for each model | — |
| `ablation_results.json` | AUC per feature group per model (RF, XGBoost, LSTM) | `hydrology` group typically highest |
| `uncertainty_metrics.json` | ECE, Brier score, MC-dropout interval widths for all models | — |
| `shap_explanation.json` | Global + per-city feature importance | crop_water_deficit: 35% global weight |
| `transition_cvle_linkage.json` | Pre/post-transition CVLE risk with statistical test | Delhi 2003: delta=+33%, p=0.032 |
| `viability_trend_report.json` | 25-year risk slope per city | Delhi: slope=+0.0045/yr, p=0.008, deteriorating |
| `groundwater_recharge_grid.json` | Annual recharge efficiency for all cities | Delhi 2022: 0.005 m/mm |
| `crop_advisory.json` | 14-crop ranked scores per city with trajectory penalty | Ahmedabad top crop: cotton (97.8/100) |
| `irrigation_strategy.json` | RSI level, method, sowing window, govt schemes | Delhi: critical, drip only, PMKSY applicable |
| `exploitation_risk_report.json` | ERI score, alert flag, MSP, distress threshold, alt crops | Delhi ERI=0.71, alert=true, MSP=₹2275/quintal |

---

## Part 6: From Data to Insight — Complete Example (Delhi Wheat)

### Steps 0–4: Raw Data to Features

**Step 0:** Master index creates 25 rows for Delhi, one per year 2000–2024.

**Steps 1–2:** Köppen classification and climate feature computation

| Year | Temperature | Rainfall | Köppen | GDD | Water Deficit | Notes |
|---|---|---|---|---|---|---|
| 2000 | 24.5°C | 680 mm | Cwa | 1,250 | 0.05 | Healthy year; wheat viable |
| 2003 | 26.8°C | 640 mm | BSh | 900 | 0.15 | Zone shift detected |
| 2010 | 27.2°C | 620 mm | BSh | 750 | 0.30 | Moderate stress |
| 2017 | 27.9°C | 520 mm | BSh | 620 | 0.41 | First dual-deficit year |
| 2018 | 28.1°C | 500 mm | BSh | 600 | 0.45 | Crisis year |

**Step 3:** Groundwater aggregation for Delhi wells

| Year | Pre-Monsoon Depth | Recharge Efficiency | Depletion Rate |
|---|---|---|---|
| 2000 | 15 m | 0.010 m/mm | — |
| 2003 | 17 m | 0.008 m/mm | +2 m/yr |
| 2010 | 20 m | 0.007 m/mm | +1.5 m/yr |
| 2017 | 24 m | 0.006 m/mm | +1 m/yr |
| 2018 | 25 m | 0.005 m/mm | +1 m/yr |

The 15-year trend is unmistakable: the aquifer dropped from 15 m to 25 m below ground while recharge efficiency fell by half.

### Step 5: Combine and Label

Row in `vegshift_master.csv` for Delhi 2018:
```
city = "Delhi"
year = 2018
crop = "wheat"
koppen_zone = "BSh"
gdd_accumulation = 600          (wheat needs 1,200)
crop_water_deficit = 0.45       (45% shortfall from wheat's 450 mm need)
recharge_efficiency = 0.005     (very low)
pre_monsoon_depth_mbgl = 25
sowing_window_miss = 0.65       (65% delay from optimal sowing date)
dual_deficit = 1                (0.45 > 0.40 AND 0.005 < 0.30)
gdd_adequate = 0                (600 < 1,200 minimum)
gw_imputed = 0                  (real well data)

CVLE computation:
  dual_deficit_2017 = 1, dual_deficit_2018 = 1  → Condition 1: satisfied
  t1 (sowing_miss > 0.6): True ✓
  t2 (water_deficit > 0.4): True ✓
  t3 (gdd inadequate): True ✓
  2 of 3 threshold: satisfied (all three, in fact)

cvle_label = 1
```

### Steps 6–9: Model Training

The TFT, looking at Delhi's 5-year history (2013–2017), learns the pattern:
- Dual-deficit in 2017, 2016, 2015 (3 consecutive years before 2018)
- Monotonically rising water depth (15 → 17 → 20 → 24 → 25 m)
- Falling GDD trend
- Rising sowing window miss percentage

It assigns a high probability of CVLE for 2018. The SHAP analysis confirms: "For Delhi, the top two drivers of this prediction are crop_water_deficit (35% contribution) and monsoon_onset_doy (30% contribution)."

### Steps 10–11: Causal Analysis

**Linkage (Step 10):**
- Transition detected 2003 (Cwa → BSh)
- Pre-2003 mean CVLE probability (TFT): 12%
- Post-2003 mean CVLE probability (TFT): 45%
- Risk delta: +33 percentage points
- Wilcoxon p-value: 0.032 (statistically significant at 5% level)
- CVLE lag: 15 years (first CVLE in 2018, 15 years after the 2003 transition)

**Trend (Step 11):**
- Slope: +0.0045/year
- R²: 0.62
- p-value: 0.008
- Classification: "deteriorating"

### Step 12: Control Validation

Pune, Kolkata, and Mumbai all pass:
- All three classified as "stable" trend (p ≥ 0.05)
- Zero CVLE events detected for any control city
- Zero zone transitions for any control city

This confirms the pipeline is detecting real, city-specific signal — not a systematic artifact from data preprocessing or model bias.

### Steps 15–17: Advisory Outputs

**Crop Advisory (Step 15):**
Delhi's wheat score = 38/100 (very low, driven by poor zone compatibility, low rainfall adequacy, and a sharply negative trajectory penalty).
Top recommended alternative: Bajra (pearl millet) — score 89/100 (drought-tolerant, compatible with BSh zone, gaining climate headroom).

**Irrigation (Step 16):**
RSI = Critical (pre-monsoon depth > 20 mbgl, recharge efficiency < 0.002).
Recommendation: drip irrigation only; rainwater harvesting structures. Applicable schemes: PMKSY, PM-KUSUM.

**ERI (Step 17):**
ERI = 0.71 (above 0.65 alert threshold).
MSP for wheat 2024–25: ₹2,275 per quintal. Distress threshold: ₹1,820 per quintal.
Alert triggered; alternative crops: barley, chickpea, bajra.

### Step 14: Dashboard

The dashboard shows Delhi's story visually:
- Panel 1 (Sowing Window Drift): monsoon onset has drifted from day 155 (June 4) in 2000 to day 185 (July 4) in 2018 — a full month later
- Panel 2 (Dual-Deficit Heatmap): Delhi shows red cells continuously from 2015 through 2019
- Panel 3 (CVLE Timeline): Delhi has 1 confirmed CVLE event (2018), compared to 0 for Mumbai, Pune, Kolkata
- Panel 5 (Recharge Efficiency Trend): Delhi's line slopes steadily downward from 0.010 in 2000 to 0.005 in 2022

---

## Part 7: Why This Approach?

### Why Three Datasets Instead of One?

**Climate data alone** would show that rainfall is declining and temperatures are rising — but it says nothing about whether farmers can compensate using groundwater. Cities with good aquifer recharge can sustain crops through droughts; cities with failing aquifers cannot.

**Groundwater data alone** would show aquifer depletion trends — but it cannot tell you whether rainfall shortfall or over-extraction is driving the depletion, or whether crops are still viable given the available water.

**Crop requirements alone** (FAO GAEZ thresholds) establish what crops need — but without knowing what current climate delivers and whether groundwater bridges the gap, you cannot determine viability.

**The combination** captures the full physical chain: atmospheric supply → demand from crops → subsurface backup buffer → crop viability.

### Why Dual-Deficit Instead of a Single Threshold?

Single-variable thresholds (e.g., "flag CVLE if rainfall < 300 mm") generate too many false positives. A dry year is not a viability loss if groundwater compensates. The dual-deficit condition explicitly requires both pathways to fail, which is much rarer and more physically meaningful.

### Why Require Two Consecutive Years for CVLE?

A single bad year can always occur randomly. Indian agriculture has millennia of experience coping with one-year droughts through stored grain, government support, and temporary migration. The multi-year persistence requirement ensures VegShift detects structural breakdown, not weather noise.

### Why Use Multiple Machine Learning Models?

All eight models — Logistic Regression, Random Forest, XGBoost, LightGBM, LSTM, TCN, Transformer, and TFT — have different inductive biases and blindspots:
- If all eight agree that Delhi wheat is at risk, confidence is very high.
- If only TFT flags it, the pattern may be overfitted to its attention-based architecture.
- If only Logistic Regression flags it, it may be a simple linear relationship that more complex models are overcomplicating.
- If gradient-boosted trees (XGBoost, LightGBM) but not neural models flag a city, the signal likely comes from non-linear feature interactions that are amenable to tree splits but do not form temporal sequences.

The comparative study (Steps 20–23) formally quantifies where the 8 models agree and differ, which pairs are statistically indistinguishable, and which feature groups each model relies on.

### Why Control Cities?

Without control cities, the pipeline could produce perfectly coherent but systematically wrong results — for example, if a feature engineering bug inflates water deficit estimates for all cities. Pune, Kolkata, and Mumbai are chosen specifically because they are expected to have stable agriculture and abundant water. If the pipeline says they are deteriorating, the bug is in the pipeline.

### Why Probabilistic Output from TFT?

Binary "CVLE: yes/no" is too coarse for policy. A farmer deciding whether to switch crops needs to know: Is this 70% likely CVLE or a 95% likely CVLE? A policymaker allocating drought relief across 10 cities needs to know the confidence intervals on each city's risk. The 7-quantile output from TFT provides this.

---

## Part 8: Technical Stack

| Component | Technology | Purpose |
|---|---|---|
| Data processing | Pandas, NumPy | Tabular data manipulation; all pipeline steps |
| Spatial distance | Haversine formula (custom) | Assign CGWB wells to cities without external GIS library |
| Geospatial rasters | Rasterio | Read and extract values from FAO GeoTIFF files |
| Statistics | SciPy | Wilcoxon test; OLS linear regression; p-value computation |
| ML models | Scikit-learn (RF, LR) | Fast, interpretable models; SHAP integration |
| Gradient boosting | XGBoost, LightGBM | Ensemble baselines; class-imbalance-aware; extend Step 8 comparison set |
| Deep learning | PyTorch + PyTorch Lightning | TFT, LSTM, TCN, Transformer implementations |
| Time series ML | PyTorch Forecasting | Specialised TFT library with built-in attention extraction |
| Explainability | SHAP (TreeExplainer) | Feature importance for Random Forest; mathematically grounded |
| Dashboard | Plotly + Dash | 11-panel interactive web dashboard |
| API layer | FastAPI + Uvicorn | REST endpoints serving precomputed outputs to the React frontend |
| Frontend | React 18 + Vite | 8-page decision-first web app for farmers |
| Multilingual UI | Custom i18n module | English, Hindi, Kannada; language stored in browser localStorage |
| AI Coach | Rule-based + optional GPT-4o-mini | 5–7 step farming action plan; falls back to rules if no OpenAI key |
| Chatbot | TF-IDF (scikit-learn) | Retrieves relevant documentation; returns source attribution |
| Orchestration | Python subprocess | Sequential step execution with error propagation |
| Testing | pytest | 30 tests across all pipeline stages |

---

## Part 9: Running and Testing

### Run the Full Pipeline

```bash
python run_vegshift.py
```

This runs all 17 core steps in sequence and launches the dashboard in the background. Steps 20–23 (comparative research) must be run separately after the core pipeline completes.

### Preview What Steps Will Run Without Executing Them

```bash
python run_vegshift.py --dry-run
```

### Run Individual Steps

```bash
python pipeline/step0_master_index.py
python pipeline/step0b_preprocess.py
python pipeline/step1_koppen.py
python pipeline/step1b_transitions.py
python pipeline/step2_climate_features.py
python pipeline/step3_groundwater.py
python pipeline/step4_gaez.py
python pipeline/step5_join_and_features.py
python pipeline/step6_tft_train.py
python pipeline/step7_tft_predict.py
python pipeline/step8_baselines.py
python pipeline/step9_shap.py
python pipeline/step10_linkage.py
python pipeline/step11_trend.py
python pipeline/step12_validation.py
python pipeline/step13_recharge_grid.py
python pipeline/step14_dashboard.py
python pipeline/step15_crop_advisory.py
python pipeline/step16_irrigation_strategy.py
python pipeline/step17_exploitation_risk.py

# Research / comparative study steps (run after core pipeline)
python pipeline/step20_deep_models.py
python pipeline/step21_unified_eval.py
python pipeline/step22_ablation.py
python pipeline/step23_uncertainty.py
```

### Run All Tests

```bash
pytest tests/
```

Tests cover:
- Runner file structure and step count
- Dry-run exit code correctness
- Raw dataset presence and column names
- Output file existence after pipeline run
- Model file existence and loadability
- Data integrity: 250 rows, exactly 10 cities, 0 NaN in all key columns
- CVLE logic: control cities should have 0 events; at-risk cities should have events

### Run the Product Web Application

After the pipeline completes, start the full product stack:

```bash
# Step 1: Build the frontend data bundle
python tools/build_frontend_payload.py
# Output: data/output/frontend_payload.json (all pipeline results in one file)

# Step 2: Start the API server
uvicorn api.app:app --reload --port 8000
# Runs at http://localhost:8000

# Step 3: Start the React frontend
cd web && npm install && npm run dev
# Runs at http://localhost:5173
```

**The 9 pages of the web app:**

| Route | What You See |
|---|---|
| `/` | Landing — project overview; live ERI risk meters for all 10 cities |
| `/intake` | Farmer profile form: name, city, land size, primary crop |
| `/dashboard` | ERI gauge, risk meter, advisory cards, 5-year trend strip, AI Coach action steps — gated until intake is submitted |
| `/crops` | 14-crop ranked suitability table with 5-axis scores and trajectory penalty breakdowns |
| `/water` | RSI level indicator, irrigation method recommendation, recharge efficiency trend chart, applicable government schemes |
| `/economic` | ERI component stacked bar, MSP vs. distress threshold, procurement links |
| `/explain` | SHAP feature importance bar chart + TFT attention weight visualisation |
| `/reports` | Full city report aggregating all outputs in a single scrollable view |
| `/compare` | 8-model benchmark page: unified metrics table, pairwise statistical significance tests, feature-group ablation chart, uncertainty (ECE / Brier / MC-dropout interval widths), Köppen zone AUC breakdown |

**AI Chatbot (all pages):**
A persistent chat widget in the bottom-right corner of every page. Uses TF-IDF text similarity to search the knowledge base — built from all Markdown files in `docs/` plus all key JSON output files. Each response includes source attribution badges (e.g., "Source: transition_cvle_linkage.json — Delhi 2003") so users can verify where an answer came from.

**AI Coach (Dashboard page):**
Calls the `/coach` API endpoint with the farmer's profile (city, crop, land size) and receives a personalised 5–7 step farming action plan. If `OPENAI_API_KEY` is set in the environment, it calls GPT-4o-mini for richer context-aware steps. Otherwise it falls back to a deterministic rule-based engine that maps RSI level + CVLE status to pre-written recommendation templates.

**Multilingual support:**
All three languages (English, Hindi हिन्दी, Kannada ಕನ್ನಡ) are available via a dropdown in the navigation bar. Language preference is saved in the browser's localStorage — if a farmer switches to Hindi, every page renders in Hindi until they change it again. Translation is applied at the component level via the `useTranslation()` hook throughout the React codebase.

---

## Summary

VegShift is a 21-step automated data pipeline that combines three physical datasets — daily atmospheric climate records, quarterly groundwater depth measurements, and FAO crop suitability maps — to detect when Indian cities' climates have shifted enough to make their primary crops unviable.

**The 21 steps in seven phases:**
1. Standardise and preprocess raw data (Steps 0–4)
2. Merge into a 250-row master table and compute CVLE labels (Step 5)
3. Train and compare eight machine learning models: TFT, Random Forest, Logistic Regression, XGBoost, LightGBM, LSTM, TCN, Transformer (Steps 6–9, 20)
4. Analyse causal linkages, long-term viability trends, and validate against control cities (Steps 10–13)
5. Generate forward-looking advisory outputs: crop recommendations, irrigation prescriptions, exploitation risk alerts (Steps 15–17)
6. Visualise all outputs in an 11-panel interactive dashboard (Step 14)
7. Run comparative research: unified 8-model benchmarking, feature ablation, uncertainty quantification (Steps 20–23)

**Five key innovations:**

1. **Dual-deficit indicator:** By requiring both atmospheric and subsurface water failure simultaneously, VegShift eliminates false alarms from droughts that farmers can compensate by pumping.

2. **CVLE — formally timestamped events:** Rather than reporting "Delhi has a water problem," VegShift pinpoints the year when that problem crossed the viability threshold for a specific crop.

3. **Causal linkage analysis:** The Wilcoxon test on pre/post-transition CVLE probabilities provides statistical evidence that zone transitions *cause* elevated viability risk — not merely correlate with it.

4. **Multi-model ensemble with control cities:** Four models must broadly agree; three control cities must show stable results. This double-blind approach prevents both over- and under-detection.

5. **SHAP + TFT attention for full explainability:** Every prediction can be decomposed into which features drove it (SHAP) and which past years influenced the temporal pattern (TFT attention). This is essential for trust in an agricultural advisory system: a farmer won't change their crop based on a black-box score.

**Final output:** Timestamped Crop Viability Loss Events with complete causal and feature-level explanations, an 11-panel Dash dashboard for researchers, and a product-grade 8-page React web app for farmers — with AI chatbot, multilingual interface, and government scheme integration.

---

## Glossary

- **CVLE (Crop Viability Loss Event):** A formally detected event, timestamped to a specific year, marking when a crop became unviable in a city. Requires dual-deficit persistence over 2 years plus 2-of-3 threshold breaches.

- **Dual-deficit:** The simultaneous failure of both atmospheric water supply (rainfall) and subsurface water supply (groundwater recharge). `crop_water_deficit > 0.40 AND recharge_efficiency < 0.30`.

- **GDD (Growing Degree Days):** The accumulation of daily heat units above a crop's biological minimum temperature. Measured in degree-days (°C·days). Determines whether a crop can complete its biological lifecycle in a given growing season.

- **Köppen climate classification:** A globally standardised system labelling climates by letter codes (Am, Aw, BSh, BWh, Cwa, etc.) based on measurable temperature and rainfall thresholds. Different crops are suited to different Köppen zones; zone shifts drive crop viability changes.

- **Monsoon onset:** The day-of-year when the summer monsoon arrives. Defined as the first day when a 5-day rolling rainfall sum exceeds 25 mm. Late onset delays or prevents sowing of kharif crops.

- **Recharge efficiency:** Water table recovery (metres) from May to August, divided by annual rainfall (mm). Expresses how effectively monsoon rainfall refills the aquifer. Declining over time = aquifer damage.

- **mbgl (Metres Below Ground Level):** Unit of water table depth. Higher number = deeper water table = more depleted aquifer. A shift from 15 mbgl to 25 mbgl over 20 years means the water table dropped 10 metres.

- **RSI (Recharge Stress Index):** A four-level classification (Critical / Stressed / Moderate / Healthy) of aquifer stress, derived from recharge efficiency and pre-monsoon depth. Maps to specific irrigation method prescriptions.

- **ERI (Exploitation Risk Index):** A weighted composite score (0–1) combining CVLE probability, drought risk, groundwater stress, viability trajectory, and climate transition risk. Triggers economic alerts at ≥ 0.65.

- **MSP (Minimum Support Price):** The Indian government's guaranteed floor price for a crop. When market prices fall below MSP, the government is obligated to procure at MSP. The distress threshold is set at 80% of MSP.

- **FAO GAEZ (Global Agro-Ecological Zones):** UN FAO's geospatial database of crop suitability across the world, gridded at ~9 km resolution, scored 1–7. Based on 1981–2010 climate baseline.

- **ECOCROP:** FAO's database of crop-specific biological thresholds: minimum temperature, maximum temperature, minimum rainfall, and minimum GDD. Used as hard limits in CVLE detection.

- **Haversine formula:** The standard spherical trigonometry formula for computing straight-line distance between two points given their lat/lon coordinates, accounting for Earth's curvature. Used to assign CGWB wells to the nearest city.

- **Wilcoxon signed-rank test:** A non-parametric statistical test comparing paired before/after measurements without assuming a normal distribution. Used to test whether zone transitions significantly elevated CVLE risk.

- **SHAP (SHapley Additive exPlanations):** A feature importance method rooted in cooperative game theory. Computes each input variable's fair contribution to a specific model prediction.

- **TFT (Temporal Fusion Transformer):** A deep learning model designed for multi-variate time series forecasting. Uses an attention mechanism to weight the importance of each past time step and outputs probabilistic (quantile) forecasts.

- **Random Forest:** A machine learning model built from hundreds of decision trees, each trained on a random data subset. Aggregates their votes for robust, interpretable predictions.

- **XGBoost / LightGBM:** Gradient-boosted tree ensemble algorithms that build trees sequentially, each correcting the errors of the previous one. Handles non-linear feature interactions and class imbalance well. Used as additional baseline models in Step 8.

- **LSTM (Long Short-Term Memory):** A recurrent neural network architecture designed to learn patterns in sequential data. Used as a comparison baseline against TFT.

- **TCN (Temporal Convolutional Network):** A sequence model using dilated causal convolutions instead of recurrence. Processes all time steps in parallel; captures temporal patterns through stacked receptive fields. Trained in Step 20.

- **Vanilla Transformer:** A self-attention sequence model without TFT's variable selection networks or gating layers. Serves as an ablation of TFT to isolate which complexity in TFT is actually valuable. Trained in Step 20.

- **ECE (Expected Calibration Error):** A measure of probability calibration. Bins predictions by confidence level and computes the weighted mean absolute gap between predicted probability and actual outcome frequency. Lower = better calibrated.

- **MC Dropout:** A Bayesian approximation technique: dropout layers are kept active during inference. Running N stochastic forward passes yields a distribution of predictions, whose mean is the point estimate and std is the epistemic uncertainty.

- **Ablation study:** An experiment that removes a subset of inputs (a "feature group") and measures the drop in model performance. Isolates which parts of the input are load-bearing.

- **TF-IDF (Term Frequency–Inverse Document Frequency):** A numerical statistic measuring how relevant a word is to a document within a collection. Used by the chatbot to find the most relevant source document for each user question.

- **F1 score:** A classification model evaluation metric that balances precision (accuracy of positive predictions) and recall (coverage of all actual positives). Ranges from 0 to 1; higher is better.

- **Pipeline:** A sequential chain of data processing scripts where each step reads outputs of the previous step and writes inputs for the next. VegShift's pipeline has 17 steps.

- **Kharif:** India's summer/monsoon crop season (approximately June–November). Crops: rice, cotton, maize, sorghum, bajra, groundnut.

- **Rabi:** India's winter crop season (approximately November–April). Crops: wheat, mustard, chickpea, lentil, barley.

- **GeoTIFF:** A standard geospatial image file format where each pixel stores a numerical value associated with a geographic location. Used by FAO GAEZ to distribute suitability maps.
