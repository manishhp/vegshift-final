# VegShift Presentation Quick-Start Guide

**Last updated:** May 14, 2026  
**Status:** ✅ Ready for presentation

---

## 🚀 QUICK START (Before Your Presentation)

### Step 1: Make sure both servers are running

**Terminal 1 — Backend (FastAPI):**
```powershell
python -m uvicorn api.app:app --host 127.0.0.1 --port 8000 --reload
```
Expected: `Uvicorn running on http://127.0.0.1:8000`

**Terminal 2 — Frontend (React/Vite):**
```powershell
cd web && npm run dev
```
Expected: `Local: http://localhost:5173/`

### Step 2: Test in browser
1. Open http://localhost:5173
2. See landing page
3. Click "Start Analysis"
4. Fill form → select Ahmedabad → click Analyze
5. Dashboard should load with all metrics

---

## 🔧 WHAT WE FIXED TODAY

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| Dashboard page crashed | `detail.trend` was undefined | Added optional chaining: `detail.trend?.slope ?? 0` |
| CityOverview page crashed | Same as above | Same fix applied |
| Evidence cards were empty | `frontend_payload.json` didn't include evidence | Rebuilt payload with evidence |
| Build script failed | Nested JSON structures not handled | Updated `build_frontend_payload.py` to detect nested structures |

---

## 📊 UNDERSTANDING THE KEY METRICS

### **1. Climate Zone (Köppen-Geiger)**
- **What**: Global climate classification system
- **In VegShift**: Shows current climate regime of the city
- **Example**: "Aw" = Tropical Savanna, "BSh" = Semi-Arid Hot
- **Why it matters**: Directly determines which crops CAN grow there

**For your presentation:**  
*"This is the foundational climate classification. Each zone has specific crops that are adapted to it. When a city's zone shifts, entire crops become unviable overnight."*

---

### **2. CVLE Events (5 yr)**
- **What**: Crop Viability Loss Events in last 5 years
- **How it's calculated**: Years where BOTH conditions held:
  1. Atmospheric water deficit > 40% + Groundwater recharge < 30%, PLUS
  2. At least 2 of: (a) sowing window missed, (b) insufficient rainfall, (c) GDD below minimum
- **Example**: "2" means 2 years where crops couldn't be grown
- **Green/Red**: < 2 is good (green), ≥ 2 is risky (red)

**For your presentation:**  
*"CVLE is our real-world ground truth. It's not a model output — it's a formal trigger event that marks when climate actually made crops unviable."*

---

### **3. Trend Slope**
- **What**: 25-year linear regression slope of viability risk probability
- **How to read it**:
  - **Negative slope (RED)**: Climate becoming LESS favorable ← WORSE
  - **Positive slope (GREEN)**: Climate becoming MORE favorable ← BETTER
  - **R² value**: How strong the trend (closer to 1 = very reliable)
  
- **Example**: "-0.0025 (R²=0.65)" = Viability declining at -0.0025 per year, with moderate reliability

**Math**: `viability_risk = m*year + b` where m = slope

**For your presentation:**  
*"This is the most important metric. It's literally the slope of climate fitness over a quarter century. Negative = the city is becoming harder to farm in. Positive = the city is becoming easier."*

---

### **4. Climate Zone Transitions**
- **What**: Has the city's climate zone shifted permanently?
- **Trigger**: New zone persists for ≥ 3 years
- **Example**: "Aw → BSh" = Tropical becoming Semi-Arid
- **Why permanent**: 3-year persistence rule filters out weather noise

**For your presentation:**  
*"A zone transition is climate change becoming irreversible in that city. It's not a bad year — it's a permanent regime shift."*

---

### **5. Exploitation Risk Index (ERI)**
- **What**: Composite score (0-1) measuring farmer vulnerability to middleman exploitation
- **5 components**:
  1. CVLE probability (5-yr rolling avg) — climate threat
  2. Drought stress (current year water deficit) — immediate stress
  3. Groundwater stress (depth + depletion rate) — subsurface failure
  4. Viability trajectory (is climate worsening?) — medium-term direction
  5. Transition shock (if zone changed recently) — regime shift impact

- **Color coded**:
  - 🟢 Green (< 33%): Farmer can negotiate fairly
  - 🟡 Yellow (33-65%): Some price pressure
  - 🔴 Red (> 65%): Farmer highly vulnerable

- **Economic floor**: MSP × 80% = distress threshold
  - If middleman offers below this, it's exploitative

**For your presentation:**  
*"ERI is unique to VegShift. We've mapped climate stress to economic exploitation. When farmers are climate-vulnerable, they become targets for unfair pricing. Our system detects that moment and provides a price floor."*

---

## 📱 PRESENTING EACH PAGE

### **LANDING PAGE**
- Hero visual
- 3 value props (detect, recommend, protect)
- CTA button
- **Talk points**: "VegShift combines 25 years of climate data + groundwater measurements + crop science. We process all of this into one decision: what should you grow, and at what price are you being exploited?"

### **INTAKE FORM**
- Show the form fields
- Fill it out (e.g., Ahmedabad, wheat, etc.)
- **Talk point**: "This personal data never leaves your phone. It just helps us tailor the analysis to YOUR farm."

### **DASHBOARD** ← Most important page
- Start at the 4 metric cards
- **Trend slope**: "Look — negative slope means wheat is becoming harder to grow in Ahmedabad"
- **Crop recommendations**: "Our model scored all 14 major crops. These 3 are best for Ahmedabad's current AND future climate"
- **ERI card**: "This farmer is at medium risk. If someone offers below ₹1820/quintal, that's exploitation"
- **Irrigation section**: "Recharge efficiency is 0.45% — that's stressed. We recommend drip irrigation + rainwater harvesting"
- **Evidence cards**: "All of this is backed by real data — IMD reports, government studies, peer-reviewed papers"

### **CITY OVERVIEW**
- Deeper dive on climate history
- Zone transitions table (shows when zones shifted)
- SHAP importance (which factors drive risk the most)
- Recharge trend chart (falling = water table declining)

### **CHATBOT**
- Type a question: "What does CVLE mean?"
- Bot returns relevant passages from documentation
- **Benefit**: Self-service support for farmers

---

## 🎯 PRESENTATION NARRATIVE

### **Opening** (2 min)
*"Indian farmers are facing an unprecedented climate crisis. In the last 25 years, we've seen zone shifts, monsoon delays, groundwater collapse, and heat waves. But the data is fragmented — spread across IMD, CGWB, FAO databases. No farmer can access it."*

*"VegShift solves this. We unified 25 years of climate + groundwater + crop data. Then we built a simple UI that answers three questions for any farmer:*
1. *What should I grow here?*
2. *What's my water situation?*
3. *Am I being exploited on price?"*

### **Demo Section 1: Climate Reality** (3 min)
- Show Dashboard metrics
- **Trend slope**: "See this negative slope? Ahmedabad's climate is becoming less favorable for wheat."
- **Zone transition**: "In 2014, Ahmedabad shifted from tropical to semi-arid — permanent change"
- **CVLE events**: "That's why we saw 2 crop loss events in 5 years"

### **Demo Section 2: Recommendations** (2 min)
- Show crop rankings
- **Trajectory penalty**: "Our model didn't just rank crops by current conditions. It penalizes crops whose future climate fit is worsening — even if viable today"
- Click on recommended crops, show full advisory

### **Demo Section 3: Economic Protection** (2 min)
- Show ERI card
- **MSP & distress floor**: "Government sets ₹2275/quintal floor for wheat. But we're warning this farmer: below ₹1820 (80% of MSP) is a distress sale"
- **Why 80%?** "Real-world data shows drought-hit farmers sell 15-25% below MSP. We capture that range."

### **Demo Section 4: Evidence** (1 min)
- Show evidence cards
- "Every metric is grounded in real data — IMD heat wave reports, CGWB groundwater studies, peer-reviewed papers"
- "Farmers can see the SOURCE and read it themselves"

### **Closing** (1 min)
- "VegShift transforms climate data into farmer decisions"
- "10 cities, 25 years, 14 crops, 1 decision: 'What should I grow?'"
- "And our exploitation risk index ensures farmers aren't left vulnerable to middlemen"

---

## 🐛 TROUBLESHOOTING (During Presentation)

| Problem | Solution |
|---------|----------|
| Page shows "No city selected" | Make sure city is selected in header dropdown |
| Numbers show 0% / "—" | Server might not have reloaded. Refresh page (F5) |
| Evidence cards are blank | Run `python tools/build_frontend_payload.py` in terminal |
| Chatbot doesn't respond | Check browser console for errors. Might need server restart |
| Page is slow | Might be first load. Give it 5 seconds |
| Numbers are different from what you expected | Normal — different cities have different climate patterns. Use Ahmedabad or Delhi for consistent demo |

**Quick fix if anything breaks:**
```powershell
# Terminal 1: Rebuild payload
python tools/build_frontend_payload.py

# Terminal 2: Restart backend (Ctrl+C, then):
python -m uvicorn api.app:app --host 127.0.0.1 --port 8000 --reload

# Terminal 3: Refresh browser (F5)
```

---

## 📝 TALKING POINTS BY AUDIENCE

### **For Climate Scientists**
- "We use Köppen-Geiger classification with 3-year persistence rule"
- "Trend slopes computed via 25-year linear regression"
- "CVLE is formal event defined by dual-deficit trigger + 2/3 threshold metrics"
- "Evidence sourced from IMD, CGWB, FAO — all public data"

### **For Farmers**
- "What should I grow? (Ranked crops)"
- "Is my water running out? (Groundwater stress)"
- "Am I being cheated on price? (Exploitation risk)"
- "Can I read the science behind this? (Evidence links)"

### **For Policy Makers**
- "10 cities monitored continuously"
- "Early warning system for climate-induced crop failures"
- "Data-driven irrigation subsidy targeting (RSI levels)"
- "Price protection recommendations tie to MSP floors"

### **For Investors**
- "Solves $50B+ Indian agricultural crisis"
- "Scalable to all 600+ districts"
- "Monetization: Government contracts (early warning), Agri-fintech partnerships (pricing), Telecom tie-ups (SMS delivery)"

---

## ✅ PRE-PRESENTATION CHECKLIST

- [ ] Both servers running (backend on 8000, frontend on 5173)
- [ ] Browser opens to landing page
- [ ] Can fill intake form and select Ahmedabad
- [ ] Dashboard loads with all 4 metric cards
- [ ] Evidence cards are visible (not blank)
- [ ] Crop recommendation cards show scores
- [ ] ERI gauge shows percentage
- [ ] Chatbot responds to test question
- [ ] City dropdown works
- [ ] Can navigate between Dashboard and City Overview

---

## 🎤 LAST-MINUTE TIPS

1. **Practice the demo path**: Landing → Intake → Dashboard (Ahmedabad) → Show metrics → Show recommendations
2. **Know which city is "best" demo**: 
   - Ahmedabad: Clear zone shift (Aw → BSh), high ERI
   - Delhi: Hottest city, dramatic trend, famous heat stories
   - Chennai: Water crisis story (Day Zero 2019)
   - Bangalore: Current water shortage makes it topical
3. **Have a backup story**: If tech fails, you can still walk through the logic on a PDF or whiteboard
4. **Emphasize the innovation**: Not just predictions — but economic protection (ERI) + evidence grounding
5. **Answer the "so what" question**: "This is interesting data, but what does it MEAN for a farmer?" → "It means don't grow sugarcane in Jaipur. You'll lose money."

---

**Good luck with your presentation! 🌾**
