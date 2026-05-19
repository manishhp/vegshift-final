# VegShift Evidence Sources Component - Complete Architecture

## Overview
The **"Add verified source"** feature displays evidence items (research papers, news articles, government reports) per city. The component spans the entire stack: frontend UI → backend API → data pipeline → JSON storage.

---

## 1. DATA LAYER (Source of Truth)

### Primary Data File
**Location:** `docs/evidence_sources.json`

**Structure:**
```json
{
  "Ahmedabad": [
    {
      "title": "Ahmedabad Heat Action Plan",
      "source": "Ahmedabad Municipal Corporation / Natural Resources Defense Council",
      "date": "2013-01-01",
      "url": "",
      "summary": "India's first city-level heat action plan, developed after the 2010 heat wave...",
      "is_placeholder": false
    },
    {
      "title": "Effect of Heat Waves on Mortality in Ahmedabad, India",
      "source": "Epidemiology (journal) – Azhar et al.",
      "date": "2014-01-01",
      "url": "",
      "summary": "Peer-reviewed study documenting excess mortality...",
      "is_placeholder": false
    }
  ],
  "Bangalore": [...],
  "Chennai": [...],
  ...
}
```

**Key Fields:**
- `title`: Evidence document title
- `source`: Authoring institution/publication
- `date`: Publication date (YYYY-MM-DD)
- `url`: Direct link to source (can be empty = "Source pending")
- `summary`: One-line evidence summary
- `is_placeholder`: Boolean flag (true = not yet verified)

**Data Ownership:** Manual curation—human experts add verified research/reports per city.

---

## 2. PAYLOAD BUILD PIPELINE

### Build Script
**Location:** `tools/build_frontend_payload.py` (CLI entry point)

**Actual Work:** `tools/frontend_payload.py` (core logic)

### Build Flow

```
docs/evidence_sources.json
        ↓
tools/frontend_payload.py::build_payload()
        ↓
    • Load evidence JSON
    • Cross-reference with crop_advisory.json (per city)
    • Cross-reference with irrigation_strategy.json (per city)
    • Cross-reference with exploitation_risk_report.json (per city)
    • Load all other pipeline outputs (transitions, CVLE, shap, etc.)
    • Nest evidence inside city_detail[city]['evidence']
        ↓
tools/frontend_payload.py::write_payload()
        ↓
data/output/frontend_payload.json
```

### Build Command
```bash
python tools/build_frontend_payload.py \
  --data-dir data/output \
  --evidence docs/evidence_sources.json \
  --output data/output/frontend_payload.json \
  [--strict]  # Fail if any city missing evidence
```

### Key Logic (frontend_payload.py)

```python
evidence = _load_json(paths.evidence_path)  # Load docs/evidence_sources.json

# ... load all other JSON outputs ...

for city in cities:
    city_detail[city] = {
        "advisory": adv,
        "irrigation": irr,
        "eri": eri,
        "transitions": city_transitions,
        "transition_linkage": city_linkage,
        "cvle_events": city_cvle,
        "trend": trend,
        "recharge": recharge.get(city, {}),
        "shap": { ... },
        "evidence": evidence.get(city, []),  # ← Evidence nested here
    }
```

### Payload Structure Generated
```json
{
  "meta": {
    "version": "1.0",
    "last_updated": "2026-05-14T..."
  },
  "summary": [ ... ],
  "city_detail": {
    "Ahmedabad": {
      "advisory": { ... },
      "irrigation": { ... },
      "eri": { ... },
      "transitions": [ ... ],
      "transition_linkage": [ ... ],
      "cvle_events": [ ... ],
      "trend": { ... },
      "recharge": { ... },
      "shap": { ... },
      "evidence": [
        { "title": "...", "source": "...", "date": "...", "url": "", "summary": "...", "is_placeholder": false },
        { "title": "...", "source": "...", "date": "...", "url": "", "summary": "...", "is_placeholder": false }
      ]
    },
    "Bangalore": { ... },
    ...
  }
}
```

**Output Location:** `data/output/frontend_payload.json`

---

## 3. BACKEND API LAYER

### FastAPI Server
**Location:** `api/app.py`

### Data Store (Cache)
**Location:** `api/data_store.py`

**How it works:**
```python
# data_store.py
DATA_PATH = Path("data/output/frontend_payload.json")

def load_payload() -> Dict[str, Any]:
    # Reads frontend_payload.json from disk
    with DATA_PATH.open("r") as handle:
        return json.load(handle)

def get_payload() -> Dict[str, Any]:
    # Thread-safe cache with lazy loading
    global _payload_cache
    if _payload_cache is None:
        with _lock:
            if _payload_cache is None:
                _payload_cache = load_payload()
    return _payload_cache
```

### API Endpoints

#### 1. **GET /evidence/{city}**
```python
@app.get("/evidence/{city}")
def evidence(city: str) -> list:
    payload = get_payload()
    key = _normalize_city(city, payload)  # Handle case sensitivity
    return payload["city_detail"][key]["evidence"]
```

**Example Request:**
```
GET http://127.0.0.1:8000/evidence/Ahmedabad
```

**Example Response:**
```json
[
  {
    "title": "Ahmedabad Heat Action Plan",
    "source": "Ahmedabad Municipal Corporation / NRDC",
    "date": "2013-01-01",
    "url": "",
    "summary": "India's first city-level heat action plan...",
    "is_placeholder": false
  },
  {
    "title": "Effect of Heat Waves on Mortality in Ahmedabad, India",
    "source": "Epidemiology – Azhar et al.",
    "date": "2014-01-01",
    "url": "",
    "summary": "Peer-reviewed study documenting excess mortality...",
    "is_placeholder": false
  }
]
```

#### 2. **GET /city/{city}** (Returns full city detail including evidence)
```python
@app.get("/city/{city}")
def city(city: str) -> dict:
    payload = get_payload()
    key = _normalize_city(city, payload)
    return payload.get("city_detail", {}).get(key, {})
```

**Includes nested evidence array.**

#### 3. **GET /summary** (Returns summary list, includes evidence_missing flag)
```python
@app.get("/summary")
def summary() -> list:
    payload = get_payload()
    return payload.get("summary", [])
```

**Each summary item includes:**
```json
{
  "city": "Ahmedabad",
  "risk_level": "high",
  "top_crops": [...],
  "irrigation": {...},
  "eri": {...},
  "trend": {...},
  "recent_cvle_count": 2,
  "current_zone": "BSh",
  "evidence_missing": false  // ← Flag if city not in evidence JSON
}
```

### CORS Configuration
```python
CORSMiddleware(
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        # ... dev ports
    ],
    allow_methods=["GET", "POST"],
)
```

---

## 4. FRONTEND LAYER

### API Type Definitions
**Location:** `web/src/api/types.ts`

```typescript
export interface EvidenceItem {
  title: string;
  source: string;
  date: string;
  url: string;
  summary: string;
  is_placeholder?: boolean;
}

export interface CityDetail {
  advisory: { ... };
  irrigation: { ... };
  eri: { ... };
  transitions: [ ... ];
  transition_linkage: [ ... ];
  cvle_events: [ ... ];
  trend: { ... };
  recharge: { ... };
  shap: { ... };
  evidence: EvidenceItem[];  // ← Evidence array
}

export interface CitySummary {
  city: string;
  risk_level: RiskLevel;
  top_crops: CropScore[];
  irrigation: { ... };
  eri: { ... };
  trend: { ... };
  recent_cvle_count: number;
  current_zone?: string;
  evidence_missing?: boolean;  // ← Flag
}
```

### API Client
**Location:** `web/src/api/client.ts`

```typescript
export async function fetchCityDetail(city: string): Promise<CityDetail> {
  return fetchJson<CityDetail>(`/city/${encodeURIComponent(city)}`);
}

export async function fetchSummary(): Promise<SummaryResponse> {
  const [summary, meta] = await Promise.all([
    fetchJson<SummaryResponse["summary"]>("/summary"),
    fetchJson<MetaInfo>("/meta"),
  ]);
  return { summary, meta };
}
```

**Base URL:** `http://127.0.0.1:8000` (or env var `VITE_API_BASE_URL`)

### Evidence Card Component
**Location:** `web/src/components/EvidenceCard.tsx`

```typescript
import React from "react";
import type { EvidenceItem } from "../api/types";

const EvidenceCard: React.FC<{ item: EvidenceItem }> = ({ item }) => {
  return (
    <article className={`card evidence-card ${item.is_placeholder ? "placeholder" : ""}`}>
      <div className="evidence-header">
        <h4>{item.title}</h4>
        <span>{item.source}</span>
      </div>
      <p>{item.summary}</p>
      <div className="evidence-footer">
        <span>{item.date}</span>
        {item.url ? (
          <a href={item.url} target="_blank" rel="noreferrer">
            View source
          </a>
        ) : (
          <span className="muted">Source pending</span>
        )}
      </div>
    </article>
  );
};

export default EvidenceCard;
```

**Visual Logic:**
- If `is_placeholder=true`: Apply `.placeholder` CSS class (greyed out)
- If `url` is empty: Show "Source pending" instead of link
- Displays: title, source, date, summary, link/pending status

### Pages Using Evidence

#### 1. **CityOverview.tsx**
**Location:** `web/src/pages/CityOverview.tsx`

```typescript
import { useCityDetail } from "../hooks/useCityDetail";
import EvidenceCard from "../components/EvidenceCard";

const CityOverview: React.FC = () => {
  const { detail, loading, error } = useCityDetail(selectedCity);

  return (
    <section className="page">
      {/* ... risk meter, metrics, transitions ... */}

      {detail && (
        <>
          {/* Evidence section */}
          <div className="section">
            <h2>Evidence from the ground</h2>
            <div className="card-grid">
              {detail.evidence.map((item, idx) => (
                <EvidenceCard key={`${item.title}-${idx}`} item={item} />
              ))}
            </div>
          </div>
        </>
      )}
    </section>
  );
};
```

**Flow:**
1. User selects city from dropdown
2. `useCityDetail(selectedCity)` hook fetches `/city/{city}` endpoint
3. Evidence array extracted from response
4. Map over evidence items → render `<EvidenceCard>` for each
5. Display in card grid

#### 2. **Dashboard.tsx**
**Location:** `web/src/pages/Dashboard.tsx`

```typescript
import EvidenceCard from "../components/EvidenceCard";

const Dashboard: React.FC = () => {
  const { cities } = useCityContext();

  return (
    <section className="page">
      {/* Summary cards, risk matrix, etc. */}

      {/* All evidence across selected cities */}
      <div className="section">
        <h2>Evidence library</h2>
        <div className="card-grid">
          {allEvidence.map((item, idx) => (
            <EvidenceCard key={`${item.title}-${idx}`} item={item} />
          ))}
        </div>
      </div>
    </section>
  );
};
```

### Hook: useCityDetail
**Location:** `web/src/hooks/useCityDetail.ts`

```typescript
export function useCityDetail(city: string) {
  const [detail, setDetail] = useState<CityDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCityDetail(city)
      .then(setDetail)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [city]);

  return { detail, loading, error };
}
```

---

## 5. COMPLETE DATA FLOW DIAGRAM

```
┌─────────────────────────────────────────────────────────────────┐
│ HUMAN CURATOR                                                   │
│ (Adds evidence via manual JSON edit or future UI form)          │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ↓
                   ┌───────────────────┐
                   │ docs/             │
                   │ evidence_         │
                   │ sources.json      │
                   └────────┬──────────┘
                            │
                            ↓
          ┌─────────────────────────────────────┐
          │ tools/build_frontend_payload.py     │
          │                                     │
          │ loads:                              │
          │ • evidence_sources.json             │
          │ • crop_advisory.json                │
          │ • irrigation_strategy.json          │
          │ • exploitation_risk_report.json     │
          │ • transition_report.json            │
          │ • ... (all pipeline outputs)        │
          │                                     │
          │ merges evidence into city_detail    │
          └──────────────┬──────────────────────┘
                         │
                         ↓
          ┌──────────────────────────────────┐
          │ data/output/                     │
          │ frontend_payload.json            │
          │                                  │
          │ {                                │
          │   "meta": {...},                 │
          │   "summary": [...],              │
          │   "city_detail": {               │
          │     "Ahmedabad": {               │
          │       "advisory": {...},         │
          │       "irrigation": {...},       │
          │       "evidence": [...]  ← HERE  │
          │     },                           │
          │     ...                          │
          │   }                              │
          │ }                                │
          └──────────────┬───────────────────┘
                         │
                         ↓
          ┌──────────────────────────────────┐
          │ api/data_store.py                │
          │                                  │
          │ Loads payload to cache:          │
          │ _payload_cache = load_payload()  │
          └──────────────┬───────────────────┘
                         │
                         ↓
          ┌──────────────────────────────────┐
          │ api/app.py                       │
          │                                  │
          │ Provides REST endpoints:         │
          │ • GET /evidence/{city}           │
          │ • GET /city/{city}               │
          │ • GET /summary                   │
          └──────────────┬───────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ↓               ↓               ↓
    HTTP/JSON       HTTP/JSON       HTTP/JSON
    (localhost:8000)
         │               │               │
         ↓               ↓               ↓
┌─────────────────┐ ┌──────────────┐ ┌──────────────┐
│ web/src/        │ │ web/src/     │ │ web/src/     │
│ api/client.ts   │ │ api/types.ts │ │ pages/       │
│                 │ │              │ │ CityOverview │
│ fetchCityDetail │ │ EvidenceItem │ │              │
│ fetchSummary    │ │ CityDetail   │ │ & Dashboard  │
└────────┬────────┘ └──────┬───────┘ └──────┬───────┘
         │                 │                 │
         └─────────┬───────┴─────────┬───────┘
                   │                 │
                   ↓                 ↓
            ┌──────────────────────────────────┐
            │ web/src/components/              │
            │ EvidenceCard.tsx                 │
            │                                  │
            │ Renders:                         │
            │ - Title                          │
            │ - Source                         │
            │ - Summary                        │
            │ - Date                           │
            │ - "View source" link or          │
            │   "Source pending" placeholder   │
            └────────────────────┬─────────────┘
                                 │
                                 ↓
                    ┌────────────────────────┐
                    │ BROWSER VIEW           │
                    │                        │
                    │ Evidence Cards Grid    │
                    │ in CityOverview or     │
                    │ Dashboard pages        │
                    └────────────────────────┘
```

---

## 6. FILE DEPENDENCIES & INTERACTIONS

```
EDIT (Manual)
  ↓
docs/evidence_sources.json
  ↓
tools/build_frontend_payload.py ← Depends on
  ├── tools/frontend_payload.py (core logic)
  └── All data/output/*.json files (crop_advisory, irrigation, eri, etc.)
  ↓
data/output/frontend_payload.json
  ↓
api/data_store.py ← Loads on server startup/reload
  ↓
api/app.py ← Provides endpoints
  ├── GET /evidence/{city}
  ├── GET /city/{city}
  └── GET /summary
  ↓
web/src/api/client.ts ← Calls endpoints
  ├── fetchCityDetail(city)
  └── fetchSummary()
  ↓
web/src/api/types.ts ← Type definitions
  ├── EvidenceItem
  ├── CityDetail
  └── CitySummary
  ↓
web/src/components/EvidenceCard.tsx ← Renders single item
  ↓
web/src/pages/CityOverview.tsx
web/src/pages/Dashboard.tsx
  ↓
Browser UI
```

---

## 7. KEY INTERACTIONS SUMMARY

| Layer | Component | Function | Input | Output |
|-------|-----------|----------|-------|--------|
| **Data** | `docs/evidence_sources.json` | Source of truth | Human curation | JSON structured by city |
| **Pipeline** | `tools/frontend_payload.py` | Payload assembly | evidence.json + 9 other JSON files | `frontend_payload.json` with nested evidence |
| **Backend** | `api/data_store.py` | Lazy-load cache | `frontend_payload.json` | In-memory dict accessed by app |
| **Backend** | `api/app.py` (endpoints) | REST API | HTTP GET requests | JSON response arrays |
| **Frontend** | `web/src/api/client.ts` | Network calls | Endpoint URLs | Parsed TypeScript objects |
| **Frontend** | `web/src/api/types.ts` | Type contracts | TypeScript interfaces | Type safety in IDE + runtime validation |
| **Frontend** | `web/src/components/EvidenceCard.tsx` | Render single card | `EvidenceItem` object | HTML article element |
| **Frontend** | `web/src/pages/*.tsx` | Display grid | Array of `EvidenceItem` | Multiple `<EvidenceCard>` components |
| **Browser** | React/DOM | Render view | Component props | Visible UI |

---

## 8. Update Workflow (How to Add Evidence)

### Current Manual Process
1. **Edit** `docs/evidence_sources.json`
   ```json
   {
     "Ahmedabad": [
       {
         "title": "New verified report",
         "source": "Research org",
         "date": "2026-05-14",
         "url": "https://example.com",
         "summary": "One-line summary",
         "is_placeholder": false
       }
     ]
   }
   ```

2. **Run build script**
   ```bash
   python tools/build_frontend_payload.py \
     --data-dir data/output \
     --evidence docs/evidence_sources.json \
     --output data/output/frontend_payload.json
   ```

3. **Reload server** (or auto-reload on file change)
   ```bash
   uvicorn api.app:app --reload
   ```

4. **Frontend automatically fetches** new evidence via existing endpoints

### Future Enhancement: Form-Based UI
Could add a form in frontend (similar to the "Add verified source" UI shown in your attachment) that:
1. Submits POST request to new endpoint (e.g., `POST /evidence/{city}`)
2. Validates input
3. Appends to `docs/evidence_sources.json`
4. Triggers rebuild of `frontend_payload.json`
5. Cache reloads automatically
6. Frontend refetch shows new evidence

---

## 9. Testing & Validation

### Unit Tests
**Location:** `tests/test_frontend_payload.py`

```python
def test_evidence_exists_for_all_cities(payload):
    for city in payload["city_detail"].keys():
        assert "evidence" in payload["city_detail"][city]
        assert isinstance(payload["city_detail"][city]["evidence"], list)
```

### Integration Test
**Location:** `tests/test_runner.py`

```bash
# Run full pipeline + build payload + test
pytest tests/
```

---

## 10. Summary Table

| Aspect | Details |
|--------|---------|
| **Source file** | `docs/evidence_sources.json` |
| **Data format** | JSON dictionary: city → array of evidence items |
| **Pipeline build** | `tools/build_frontend_payload.py` |
| **Payload location** | `data/output/frontend_payload.json` |
| **Backend caching** | `api/data_store.py` (thread-safe, lazy-loaded) |
| **API endpoints** | `GET /evidence/{city}`, `GET /city/{city}` |
| **Frontend types** | `web/src/api/types.ts::EvidenceItem` |
| **Display component** | `web/src/components/EvidenceCard.tsx` |
| **Pages using it** | `CityOverview.tsx`, `Dashboard.tsx` |
| **Styling** | `.evidence-card`, `.placeholder` CSS classes in `styles.css` |
| **Placeholder handling** | `is_placeholder: true` → grey out, `url=""` → "Source pending" |
| **CORS** | Allowed from dev ports (5173–5175) |

---

## Conclusion

The evidence sources component is a **read-only, stateless data flow** from JSON file → pipeline build → backend cache → REST API → frontend fetch → React render. It touches **every layer** of the application:

- **Data layer:** `docs/evidence_sources.json`
- **Build layer:** `tools/frontend_payload.py`
- **Backend layer:** `api/data_store.py`, `api/app.py`
- **Frontend layer:** `web/src/api/`, `web/src/components/`, `web/src/pages/`

All connected via typed REST endpoints with CORS, lazy-loaded caching, and component-based rendering.
