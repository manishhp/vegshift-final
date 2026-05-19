# VegShift UI Components Guide
**For your presentation** — A complete walkthrough of each page and what it shows

---

## 🌍 **LANDING PAGE** (`/`)
**What it shows**: Overview of VegShift + invitation to start

**Key components:**
- **Hero section**: Big title + tagline explaining the mission
- **Quick stats**: How many cities monitored, years of data, number of crops
- **Value proposition cards**: 3 cards explaining what VegShift does (detect climate changes, recommend crops, protect farmers)
- **CTA button**: "Start Analysis" → takes you to Intake Form

**What you see**: 
- Beautiful visual with farm imagery or iconography
- Clear explanation of what the system does
- No data loading yet (pure static content)

---

## 📋 **INTAKE FORM** (`/intake`)
**What it does**: Collects farmer profile to personalize the dashboard

**User fills in:**
- ✅ **City** (dropdown): Select from 10 Indian cities
- ✅ **Desired crop**: What they want to grow
- ✅ **Budget**: Farm budget in INR (helps with irrigation recommendations)
- ✅ **Land size**: Area in hectares
- ✅ **Water access**: Well, borewell, canal, rainwater, other
- ✅ **Irrigation type**: Manual, sprinkler, drip, micro-irrigation, rainfed
- ✅ **Season**: Kharif (monsoon), Rabi (winter), Summer, annual

**Flow**:
1. User fills form
2. Clicks "Analyze" 
3. Data saved to browser storage
4. Redirected to `/dashboard` for that city

**Key insight for presentation**: This personal data is **not sent anywhere** — it stays in the browser and just personalizes what they see.

---

## 📊 **DASHBOARD** (`/dashboard`)
**What it shows**: Farmer's personalized climate risk analysis for their city + actionable guidance

### **Section 1: Farm Profile Summary**
Shows back what the farmer entered in the intake form (like a recap card)

---

### **Section 2: Key Metrics Row** (4 metric cards)

#### **1️⃣ Climate Zone**
- **What is it**: Koppen-Geiger classification (global standard for climate classification)
- **Example values**: "Aw" (tropical savanna), "BSh" (semi-arid hot), "Cwa" (humid subtropical)
- **Why it matters**: Tells you what crops can grow there + what to expect weather-wise
- **For presentation**: "This tells us the fundamental climate regime of the city"

#### **2️⃣ CVLE Events (5 yr)**
- **What is it**: "Crop Viability Loss Events" — years in the last 5 when crops couldn't be grown anymore
- **Example**: If it shows "2", it means 2 years in the last 5 years where the selected crop became unviable
- **Why it matters**: Quantifies agricultural risk
- **For presentation**: "Higher numbers = more climate stress = farmer at risk"

#### **3️⃣ Trend Slope**
- **What is it**: Is farm viability getting better or worse? (linear trend over 25 years)
- **How to read it**: 
  - **Negative slope (red)** = Getting worse (climate becoming unfavorable) 🔴
  - **Positive slope (green)** = Getting better (climate becoming favorable) 🟢
  - **R² value** = How strong/reliable the trend is (closer to 1.0 = very strong trend)
- **Example**: "-0.0025" slope with "R² = 0.65" = viability is slowly declining but trend is moderate
- **For presentation**: "This is the most important metric — it shows if agriculture is becoming harder or easier"

#### **4️⃣ Transitions Detected**
- **What is it**: Has the city's climate zone shifted? (e.g., from Aw → BSh)
- **Example**: "Latest: Aw → BSh" = Tropical becoming Semi-arid
- **Why it matters**: Zone transitions = new crops viable, old crops risky
- **For presentation**: "A transition means the city's entire climate envelope has shifted — this is permanent change"

---

### **Section 3: Trend Strip Chart**
- **Visual**: A simple trend line showing slope direction over time
- **What it means**: Confirms if viability is up or down
- **For presentation**: Use this as visual proof of the trend

---

### **Section 4: Top 3 Crop Recommendations**
Shows 3 ranked cards with:
- 🏆 **Rank** (1st, 2nd, 3rd)
- **Crop name** 
- **Score** (0-100): How suitable (30 pts = zone match, 20 = temp, 20 = rain, 15 = groundwater, 15 = future trajectory)
- **Season** label (Kharif/Rabi/Annual)

**How score is calculated**:
```
Zone compatibility (30 pts)    → Does the crop belong in this climate?
Temperature margin (20 pts)    → How much headroom before heat stress?
Rainfall adequacy (20 pts)     → Enough rain for the crop's water need?
Groundwater stress (15 pts)    → Can wells sustain it?
Climate trajectory (15 pts)    → Is climate going TOWARD or AWAY from crop suitability?
─────────────────────────────────
TOTAL (max 100 pts)
```

**For presentation**: "Our model scores crops not just on current conditions but on where the climate is HEADING"

---

### **Section 5: Economic Protection (ERI Card)**
Shows **Exploitation Risk Index** — a composite score measuring farmer vulnerability

#### **Circular gauge** (0-100%)
- **Color coded**:
  - 🟢 Green (0-33%): Low risk → farmer can negotiate prices fairly
  - 🟡 Yellow (34-65%): Medium risk → some price pressure expected
  - 🔴 Red (66-100%): High risk → farmer highly vulnerable to exploitative middlemen

#### **Metrics shown**:
- **ERI score**: Composite of 5 climate factors
  - CVLE probability (5-year rolling average)
  - Drought stress (current year's water deficit)
  - Groundwater stress (depth + depletion rate)
  - Viability trajectory (is climate worsening?)
  - Climate transition shock (if zone changed recently)

- **MSP** (Minimum Support Price): Government's guaranteed floor price per quintal
  - Example: "₹2275/qtl" for wheat
  
- **Distress floor** (80% of MSP): RED FLAG if offer falls below this
  - Example: "₹1820" — if middleman offers ₹1800, it's exploitative
  - **Why 80%?** Real-world data shows distress sales in drought years run 15-25% below MSP; 80% captures that

**For presentation**: "When ERI is high AND a middleman offers low, we can prove it's exploitation using this floor price"

---

### **Section 6: Irrigation & Action Steps**
Shows **Recharge Stress Index (RSI)** — classifies groundwater urgency

| RSI Level | Condition | What to do | Crops to avoid |
|-----------|-----------|-----------|---|
| 🔴 **Critical** | Recharge < 0.2% OR depth > 20m | **Drip only** + solar | Rice, sugarcane, cotton |
| 🟠 **Stressed** | Recharge < 0.4% OR depth > 12m | **Drip + rainwater harvest** | Rice, sugarcane |
| 🟡 **Moderate** | Recharge < 0.6% | **Sprinkler ok** | Sugarcane |
| 🟢 **Healthy** | Otherwise | Conventional | None |

**Sowing window**: "Month X (sow 2-3 weeks before peak rainfall)"

**Government schemes** listed with links

---

### **Section 7: Local Evidence**
Shows **real-world news/research** backing up the climate analysis

Each evidence card displays:
- 📰 **Title**: e.g., "Delhi Records Hottest Day in History at 49.2°C"
- 🏢 **Source**: e.g., "India Meteorological Department (IMD)"
- 📅 **Date**: When reported
- 📄 **Summary**: 2-3 sentence explanation
- 🔗 **Link**: Clickable URL to source (if available)

**Why it matters**: Proves the climate analysis isn't theoretical — it's backed by official data

**For presentation**: "Every recommendation is grounded in observable climate shifts and government reports"

---

## 🗺️ **CITY OVERVIEW** (`/city/:city`)
**What it shows**: Deep-dive on a specific city's 25-year climate history

Displays:
1. **Same 4 metric cards** as dashboard
2. **Top recommended crops** (horizontal tags)
3. **Climate zone transition history** (table format)
   - Year | From Zone | To Zone | Confirmed over N years
4. **Transition-to-risk linkage** (statistics table)
   - Shows Wilcoxon test p-value proving zone change → risk increase
   - Post-transition CVLE lag (how many years until first loss event)
5. **SHAP feature importance** 
   - Which climate factors matter most for this city's risk?
   - Example: "Monsoon onset (0.15), rainfall adequacy (0.12), GW depth (0.10)"
6. **Groundwater recharge trend**
   - 25-year line chart of annual recharge efficiency
   - Falling line = aquifer losing recovery capacity
7. **Evidence cards** (same as dashboard)

---

## 💬 **CHATBOT** (Bottom right of all pages)
**What it does**: Q&A about the data, recommendations, concepts

**Knowledge base includes**:
- All documentation files
- All JSON output data (in readable format)
- Explanation files

**How to use**:
1. Type question: "What does ERI mean?" or "Why is wheat risky in Delhi?"
2. Bot uses TF-IDF search to find relevant sections
3. Returns most relevant passages + source document

**For presentation**: "Users can ask anything about the analysis and get instant answers"

---

## 🎨 **VISUAL DESIGN ELEMENTS**

### **Color coding**:
- 🟢 **Green**: Favorable (low risk, positive trend, good score)
- 🟡 **Yellow/Orange**: Caution (medium risk, deteriorating)
- 🔴 **Red**: Danger (high risk, negative trend, avoid)
- 🔵 **Blue**: Neutral (informational)

### **Card layout**:
- Title + tag at top
- Main metric in center (large number)
- Sub-text explanation below
- Consistent padding/borders across all cards

### **Typography**:
- **H1**: Page title (36px, bold)
- **H2**: Section head (24px, bold)
- **H3**: Card title (18px, bold)
- **Metric value**: 28px, bold, color-coded
- **Body text**: 14px, regular
- **Labels**: 12px, muted gray

---

## 📱 **RESPONSIVE BEHAVIOR**

- **Desktop (1200px+)**: 4 columns in metric cards, side-by-side layout
- **Tablet (768-1199px)**: 2 columns, 2-column grid
- **Mobile (< 768px)**: 1 column, stacked layout

---

## ✅ **WHAT EACH PAGE TELLS A FARMER**

| Page | Answer it provides |
|------|-------------------|
| Landing | What is VegShift? |
| Intake | Personalizes the analysis |
| **Dashboard** | **"What should I do on my farm RIGHT NOW?"** ← Most important |
| City Overview | **"What's the historical context for my city?"** |
| Evidence | **"Can I trust these recommendations?"** |
| Chatbot | **"What does X mean?"** |

---

## 🎯 **KEY POINTS FOR YOUR PRESENTATION**

1. **Trend slope is the star metric**: Shows if climate is becoming favorable or unfavorable
2. **Evidence section proves credibility**: Real news + government data backing recommendations
3. **Exploitation Risk Index is novel**: Combines climate data with economic protection
4. **Crop scoring is sophisticated**: Accounts for future climate, not just current conditions
5. **All 10 cities analyzed**: 25 years of daily weather × groundwater × crop suitability data
6. **Chatbot is self-serve support**: Farmers don't need to call anyone — they can explore themselves

---

## 🛠️ **IF SOMETHING IS EMPTY/MISSING**

| Component | If empty | Check... |
|-----------|----------|----------|
| Evidence cards | No local evidence shown | `docs/evidence_sources.json` exists? `frontend_payload.json` rebuilt? |
| Crop recommendations | No top 3 crops | `data/output/crop_advisory.json` exists? |
| ERI gauge | Shows 0% | `data/output/exploitation_risk_report.json` exists? |
| Trend chart | No line | `data/output/viability_trend_report.json` generated? |
| Chatbot | No responses | Check browser console for errors |

