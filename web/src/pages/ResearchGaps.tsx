import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useCityContext } from "../state/CityContext";
import { useLanguage } from "../state/LanguageContext";

/* ─────────────────────────────────────────────────────────────────────────────
   ResearchGaps.tsx
   A dedicated page that surfaces the four literature gaps from the
   HYDROLOGY_GAP_ANALYSIS.md and shows — with live data and plain language —
   exactly how VegShift fills each one.
   ───────────────────────────────────────────────────────────────────────────── */

// ── Types ──────────────────────────────────────────────────────────────────
interface GapCard {
  id: number;
  tag: string;
  tagColor: string;
  icon: string;
  title: string;
  gapHeading: string;
  gapBody: string;
  citations: string[];
  solutionHeading: string;
  solutionBody: string;
  mechanic: string;
  navLabel: string;
  navTo: string;
  liveSignal: string;
}

// ── Gap definitions (sourced from HYDROLOGY_GAP_ANALYSIS.md §6 & §9) ──────
const GAPS: GapCard[] = [
  {
    id: 1,
    tag: "GAP 1 · Temporal Linkage",
    tagColor: "rgba(245,158,11,0.15)",
    icon: "⏱️",
    title: "When exactly does a climate shift destroy a crop?",
    gapHeading: "What existing research told us",
    gapBody:
      "Beck et al. (2018) confirmed that Köppen-Geiger climate zones in South Asia are shifting. " +
      "IPCC AR6 documents India's aridification trajectory. Crop failure events are reported by ICAR. " +
      "BUT — no study connected these three into a single temporal chain with a measurable delay. " +
      "Climate scientists, agronomists, and hydrologists each knew one piece; nobody had quantified the lag from transition to first crop failure.",
    citations: ["Beck et al. 2018, Sci. Reports", "IPCC AR6 Ch.10 (2021)", "CGWB Annual Reports"],
    solutionHeading: "How VegShift fills it",
    solutionBody:
      "Step 10 of the pipeline runs a Wilcoxon Signed-Rank Test on 3-year pre-transition vs. 3-year post-transition " +
      "CVLE probability distributions for every detected zone shift. The result is a statistically validated lag: " +
      "e.g. Delhi's 2016 BSh→BWh shift caused a CVLE 2 years later (p = 0.008). " +
      "This gives policymakers and farmers a measurable adaptation window — the first time this has been quantified for Indian cities.",
    mechanic: "Wilcoxon Signed-Rank · CVLE lag · transition_cvle_linkage.json",
    navLabel: "See Delhi's transition timeline →",
    navTo: "/reports",
    liveSignal:
      "Live: transition year, pre/post risk delta, p-value, and lag in years for all 10 cities",
  },
  {
    id: 2,
    tag: "GAP 2 · Dual Failure",
    tagColor: "rgba(178,58,36,0.12)",
    icon: "⛔",
    title: "What happens when both rain AND groundwater fail at once?",
    gapHeading: "What existing research told us",
    gapBody:
      "Lobell et al. (2011, Science) showed heat stress reduces yields. " +
      "Scanlon et al. (2012, Nature) showed groundwater depletion across major aquifers. " +
      "FAO Irrigation Paper 56 defines crop water deficits. " +
      "BUT — all studied in isolation. The implicit assumption: groundwater compensates for rainfall failure. " +
      "No study formally modelled what happens when both the atmospheric and subsurface water sources " +
      "cross their failure thresholds simultaneously — the 'single point of failure' assumption in prior literature.",
    citations: ["Lobell et al. 2011, Science", "Scanlon et al. 2012, Nature", "FAO Irrig. Paper 56"],
    solutionHeading: "How VegShift fills it",
    solutionBody:
      "Step 5 defines the Dual-Deficit trigger: a Boolean flag that is TRUE only when atmospheric " +
      "water deficit exceeds 40% AND groundwater recharge efficiency falls below 0.30 — simultaneously. " +
      "A CVLE is only labelled when this compound condition persists for 2+ consecutive years AND 2 of 3 " +
      "crop thresholds are also breached. The three-layer conservatism eliminates false positives. " +
      "Pune, Kolkata, and Mumbai (control cities) produce zero dual-deficit CVLEs — validating the model.",
    mechanic: "dual_deficit = (water_deficit > 0.4) AND (recharge_efficiency < 0.30)",
    navLabel: "See dual-deficit status for your city →",
    navTo: "/water",
    liveSignal:
      "Live: Sky Water gauge + Ground Water gauge shown as two linked indicators per city",
  },
  {
    id: 3,
    tag: "GAP 3 · Unified Risk Score",
    tagColor: "rgba(59,130,246,0.12)",
    icon: "📊",
    title: "Is there one number a farmer can check to know if they're at risk?",
    gapHeading: "What existing research told us",
    gapBody:
      "The Palmer Drought Severity Index (PDSI) covers atmospheric drought only. " +
      "The Standardized Precipitation Index (SPI) covers rainfall anomaly only. " +
      "CGWB Groundwater Stress Maps cover subsurface only. " +
      "NITI Aayog's CWMI covers policy level, not crop-specific. " +
      "None combined atmospheric, subsurface, agronomic, and market signals " +
      "into a single, city-specific, crop-specific, season-ready actionable risk number " +
      "tied to government safety nets like MSP and procurement centres.",
    citations: ["Palmer 1965 (PDSI)", "McKee et al. 1993 (SPI)", "NITI Aayog CWMI 2019"],
    solutionHeading: "How VegShift fills it",
    solutionBody:
      "Step 17 computes the Exploitation Risk Index (ERI) — a weighted composite of five " +
      "environment-derived signals: 5-year CVLE probability (30%), crop water deficit (25%), " +
      "groundwater stress (20%), 25-year viability slope (15%), and climate transition risk delta (10%). " +
      "When ERI ≥ 0.65, the system triggers an alert with the current Minimum Support Price, " +
      "distress floor threshold, and state procurement centre. The farmer gets one clear answer — " +
      "the first unified climate-to-market risk number ever built for Indian agricultural cities.",
    mechanic:
      "ERI = 0.30×CVLE_prob + 0.25×water_deficit + 0.20×GW_stress + 0.15×slope + 0.10×transition_delta",
    navLabel: "Check your city's ERI →",
    navTo: "/economic",
    liveSignal:
      "Live: ERI score, MSP, distress floor, and government schemes per city",
  },
  {
    id: 4,
    tag: "GAP 4 · Hydrological Mechanistics",
    tagColor: "rgba(63,122,74,0.12)",
    icon: "🧪",
    title: "How do we measure aquifer health without infiltration data?",
    gapHeading: "What existing research told us",
    gapBody:
      "Standard hydrology (Green-Ampt, SCS Curve Number, AquaCrop) partitions rainfall into " +
      "infiltration (α), runoff (C), evapotranspiration (ET), and groundwater recharge (R). " +
      "Scanlon et al. (2012) provides the global framework. Steduto et al. (2012, FAO AquaCrop) " +
      "provides the crop-water balance model. " +
      "BUT — applying these to Indian cities requires soil infiltration maps, " +
      "land-use rasters, calibrated ET data, and extraction volumes. " +
      "None of this is publicly available at city catchment scale in India. " +
      "Rajasthan has zero wells in the CGWB quality-controlled dataset at all.",
    citations: ["Scanlon et al. 2012, Nature", "Steduto et al. 2012 (AquaCrop)", "Green & Ampt 1911"],
    solutionHeading: "How VegShift addresses it",
    solutionBody:
      "Rather than fabricating mechanistic parameters, VegShift replaces the theoretical recharge " +
      "computation with an empirically observed recharge efficiency: " +
      "η = (pre-monsoon depth − post-monsoon depth) / annual rainfall. " +
      "This collapses all unknown losses (runoff, ET, extraction, deep percolation) into one net " +
      "outcome variable — the actual water table recovery measured by 2,759 physical CGWB sensors. " +
      "Delhi's observed 16.7% efficiency aligns with the ~14% a full mechanistic model predicts, " +
      "validating the empirical approach. The limitation is explicitly documented with three upgrade paths.",
    mechanic: "η_recharge = (h_pre − h_post) / P_annual  ·  Source: 2,759 CGWB quality-controlled wells",
    navLabel: "See groundwater recharge trend →",
    navTo: "/water",
    liveSignal:
      "Live: recharge efficiency metric, depletion rate, and aquifer depth per city-year",
  },
];

// ── Rainfall partitioning diagram (Gap 4 visual) ───────────────────────────
const RainfallDiagram: React.FC = () => (
  <div style={{
    background: "rgba(30,42,36,0.05)",
    border: "1px solid var(--border)",
    borderRadius: 12,
    padding: "18px 20px",
    fontFamily: "monospace",
    fontSize: "0.78rem",
    lineHeight: 1.8,
    color: "var(--muted)",
    marginTop: 14,
  }}>
    <div style={{ color: "var(--text)", fontWeight: 700, marginBottom: 8 }}>Standard hydrology (what's missing):</div>
    <div>Annual Rainfall (1000 mm)</div>
    <div style={{ paddingLeft: 16 }}>├─ <span style={{ color: "var(--risk-medium)" }}>Direct Runoff (C%)</span> → Rivers, lost</div>
    <div style={{ paddingLeft: 16 }}>├─ Infiltration (α%) → Soil</div>
    <div style={{ paddingLeft: 32 }}>├─ <span style={{ color: "var(--risk-medium)" }}>Evapotranspiration (ET)</span> → Atmosphere</div>
    <div style={{ paddingLeft: 32 }}>├─ Vadose zone storage → Shallow soil</div>
    <div style={{ paddingLeft: 32 }}>└─ <span style={{ color: "var(--risk-low)" }}>Groundwater recharge (α × R)</span> → Aquifer ✓</div>
    <div style={{ marginTop: 12, color: "var(--text)", fontWeight: 700 }}>VegShift empirical approach (what we use):</div>
    <div>Annual Rainfall (1000 mm)</div>
    <div style={{ paddingLeft: 16 }}>└─ <span style={{ color: "var(--risk-low)" }}>η = (h_pre − h_post) / P_annual</span> → Net aquifer recovery</div>
    <div style={{ paddingLeft: 32, color: "var(--risk-low)" }}>All losses collapsed into one observable outcome ✓</div>
  </div>
);

// ── Single gap card ────────────────────────────────────────────────────────
const GapCard: React.FC<{ gap: GapCard }> = ({ gap }) => {
  const [expanded, setExpanded] = useState(false);
  const navigate = useNavigate();

  return (
    <div
      id={`gap-${gap.id}`}
      className="card"
      style={{
        borderLeft: `4px solid ${gap.tagColor.replace("0.12", "0.6").replace("0.15", "0.6")}`,
        transition: "box-shadow 0.2s",
      }}
    >
      {/* Header row */}
      <div style={{ display: "flex", alignItems: "flex-start", gap: 16, flexWrap: "wrap" }}>
        <span style={{ fontSize: "2.2rem", lineHeight: 1 }}>{gap.icon}</span>
        <div style={{ flex: 1, minWidth: 240 }}>
          <div style={{
            display: "inline-block",
            background: gap.tagColor,
            borderRadius: 20,
            padding: "2px 12px",
            fontSize: "0.72rem",
            fontWeight: 700,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            marginBottom: 6,
          }}>
            {gap.tag}
          </div>
          <h3 style={{ margin: 0, fontSize: "1.05rem", lineHeight: 1.35 }}>{gap.title}</h3>
        </div>
        <button
          type="button"
          className="ghost"
          style={{ alignSelf: "center", fontSize: "0.8rem", padding: "4px 12px" }}
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? "▲ Less" : "▼ Details"}
        </button>
      </div>

      {/* Always-visible: two-column before/after */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "1fr auto 1fr",
        gap: 12,
        marginTop: 18,
        alignItems: "stretch",
      }}>
        {/* Before: the gap */}
        <div style={{
          background: "rgba(178,58,36,0.05)",
          border: "1px solid rgba(178,58,36,0.18)",
          borderRadius: 10,
          padding: "14px 16px",
        }}>
          <div style={{
            fontSize: "0.72rem",
            fontWeight: 700,
            textTransform: "uppercase",
            letterSpacing: "0.07em",
            color: "var(--risk-high)",
            marginBottom: 8,
          }}>
            ✗ What was missing
          </div>
          <p style={{ margin: 0, fontSize: "0.83rem", lineHeight: 1.6 }}>
            {gap.gapBody.split(". BUT —")[0] + "."}
          </p>
          <div style={{ marginTop: 10, display: "flex", flexWrap: "wrap", gap: 6 }}>
            {gap.citations.map((c) => (
              <span key={c} style={{
                fontSize: "0.68rem",
                background: "rgba(178,58,36,0.08)",
                borderRadius: 6,
                padding: "2px 8px",
                color: "var(--muted)",
                fontStyle: "italic",
              }}>{c}</span>
            ))}
          </div>
        </div>

        {/* Arrow */}
        <div style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "1.6rem",
          color: "var(--muted)",
          userSelect: "none",
        }}>→</div>

        {/* After: the solution */}
        <div style={{
          background: "rgba(63,122,74,0.06)",
          border: "1px solid rgba(63,122,74,0.25)",
          borderRadius: 10,
          padding: "14px 16px",
        }}>
          <div style={{
            fontSize: "0.72rem",
            fontWeight: 700,
            textTransform: "uppercase",
            letterSpacing: "0.07em",
            color: "var(--risk-low)",
            marginBottom: 8,
          }}>
            ✓ How VegShift solves it
          </div>
          <p style={{ margin: 0, fontSize: "0.83rem", lineHeight: 1.6 }}>
            {gap.solutionBody.split(". ")[0] + ". " + gap.solutionBody.split(". ")[1] + "."}
          </p>
        </div>
      </div>

      {/* Mechanic formula bar */}
      <div style={{
        marginTop: 12,
        background: "rgba(30,42,36,0.05)",
        borderRadius: 8,
        padding: "8px 14px",
        fontFamily: "monospace",
        fontSize: "0.77rem",
        color: "var(--muted)",
        border: "1px solid var(--border)",
      }}>
        ⚙️ {gap.mechanic}
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div style={{ marginTop: 16, borderTop: "1px solid var(--border)", paddingTop: 16 }}>
          <div style={{ display: "grid", gap: 10 }}>
            <div>
              <div style={{ fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.07em", color: "var(--muted)", marginBottom: 6 }}>
                Full Gap Description
              </div>
              <p style={{ margin: 0, fontSize: "0.855rem", lineHeight: 1.7 }}>
                {gap.gapBody.includes("BUT —") ? gap.gapBody.split("BUT —")[1] : gap.gapBody}
              </p>
            </div>
            <div>
              <div style={{ fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.07em", color: "var(--muted)", marginBottom: 6 }}>
                Full Solution Description
              </div>
              <p style={{ margin: 0, fontSize: "0.855rem", lineHeight: 1.7 }}>{gap.solutionBody}</p>
            </div>
            {/* Special: show rainfall diagram for gap 4 */}
            {gap.id === 4 && <RainfallDiagram />}
          </div>
        </div>
      )}

      {/* Live data link */}
      <div style={{
        marginTop: 14,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        flexWrap: "wrap",
        gap: 10,
      }}>
        <span style={{ fontSize: "0.78rem", color: "var(--muted)" }}>
          📡 {gap.liveSignal}
        </span>
        <button
          type="button"
          className="primary"
          style={{ fontSize: "0.8rem", padding: "6px 16px" }}
          onClick={() => navigate(gap.navTo)}
        >
          {gap.navLabel}
        </button>
      </div>
    </div>
  );
};

// ── Summary comparison table ───────────────────────────────────────────────
const SummaryTable: React.FC = () => (
  <div className="card" style={{ overflowX: "auto" }}>
    <h3 style={{ marginBottom: 16 }}>📋 All Four Gaps at a Glance</h3>
    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.83rem" }}>
      <thead>
        <tr style={{ borderBottom: "2px solid var(--border)" }}>
          {["Gap", "What was missing", "VegShift's answer", "Where to see it"].map((h) => (
            <th key={h} style={{
              textAlign: "left",
              padding: "8px 12px",
              fontWeight: 700,
              fontSize: "0.72rem",
              textTransform: "uppercase",
              letterSpacing: "0.07em",
              color: "var(--muted)",
            }}>{h}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {[
          ["1 · Timing", "How long after a climate zone shifts does crop failure occur?", "Wilcoxon causal test → CVLE lag quantified (2–3 yrs)", "Reports page"],
          ["2 · Dual Failure", "What if rainfall AND groundwater both fail simultaneously?", "Dual-deficit trigger → CVLE labelled only on compound failure", "Water page"],
          ["3 · Unified Risk", "One number combining all risk signals for a farmer?", "ERI score = 5 weighted signals → MSP alert threshold", "Economic page"],
          ["4 · Hydrology", "Aquifer recharge without soil infiltration maps?", "Empirical η = ΔGW / rainfall from 2,759 CGWB sensors", "Water page"],
        ].map(([gap, missing, answer, where], i) => (
          <tr key={i} style={{
            borderBottom: "1px solid var(--border)",
            background: i % 2 === 0 ? "transparent" : "rgba(30,42,36,0.02)",
          }}>
            <td style={{ padding: "10px 12px", fontWeight: 700 }}>{gap}</td>
            <td style={{ padding: "10px 12px", color: "var(--risk-high)", fontSize: "0.8rem" }}>{missing}</td>
            <td style={{ padding: "10px 12px", color: "var(--risk-low)", fontSize: "0.8rem" }}>{answer}</td>
            <td style={{ padding: "10px 12px", color: "var(--muted)", fontSize: "0.8rem" }}>{where}</td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

// ── Methodology note (from HYDROLOGY_GAP_ANALYSIS.md §8) ─────────────────
const MethodologyNote: React.FC = () => (
  <div className="card" style={{
    background: "rgba(245,158,11,0.05)",
    borderColor: "rgba(245,158,11,0.25)",
  }}>
    <div style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
      <span style={{ fontSize: "2rem" }}>📜</span>
      <div>
        <h4 style={{ margin: "0 0 8px" }}>Methodology Note — What VegShift Does Not Claim</h4>
        <p style={{ margin: 0, fontSize: "0.875rem", lineHeight: 1.7 }}>
          VegShift simplifies the standard hydrological rainfall partitioning (Scanlon et al. 2012)
          into an empirical recharge efficiency metric calculated from observation well data.
          This metric implicitly accounts for infiltration (α), runoff (C), evapotranspiration,
          and aquifer discharge without requiring soil infiltration maps or land-use classification,
          which are unavailable at city resolution for Indian aquifers. The empirical approach reduces
          propagation of modelling uncertainties at the cost of mechanistic interpretability.
          Future work integrating ICAR-SSOMIS soil texture data would enable separation of rainfall
          losses into their hydrological components, improving mechanistic understanding.
        </p>
        <div style={{ marginTop: 12, display: "flex", gap: 8, flexWrap: "wrap" }}>
          {["Scanlon et al. 2012", "CGWB 2000–2022", "ICAR-SSOMIS (future)"].map((ref) => (
            <span key={ref} style={{
              fontSize: "0.72rem",
              background: "rgba(245,158,11,0.1)",
              borderRadius: 6,
              padding: "3px 10px",
              color: "var(--muted)",
              fontStyle: "italic",
            }}>{ref}</span>
          ))}
        </div>
      </div>
    </div>
  </div>
);

// ── Main page ──────────────────────────────────────────────────────────────
const ResearchGaps: React.FC = () => {
  const { cities } = useCityContext();
  const { lang: _lang } = useLanguage();

  return (
    <section className="page">
      {/* ── Hero ── */}
      <div className="page-header">
        <div>
          <h1>Research Foundation & Methodology Gaps</h1>
          <p style={{ maxWidth: 680 }}>
            Four things no existing system could tell a farmer or policymaker — and the exact
            mechanisms VegShift built to answer each one. Every gap is filled with live data
            from {cities.length} Indian cities spanning 25 years.
          </p>
        </div>
        <span className="tag">HYDROLOGY_GAP_ANALYSIS.md</span>
      </div>

      {/* ── Quick-jump anchors ── */}
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 8 }}>
        <span style={{ fontSize: "0.78rem", color: "var(--muted)", alignSelf: "center" }}>Jump to:</span>
        {GAPS.map((g) => (
          <a
            key={g.id}
            href={`#gap-${g.id}`}
            style={{
              fontSize: "0.78rem",
              padding: "4px 12px",
              borderRadius: 20,
              background: g.tagColor,
              textDecoration: "none",
              color: "var(--text)",
              fontWeight: 600,
              border: "1px solid var(--border)",
            }}
          >
            {g.tag.split(" · ")[1]}
          </a>
        ))}
      </div>

      {/* ── Summary table ── */}
      <SummaryTable />

      {/* ── Individual gap cards ── */}
      <div style={{ display: "grid", gap: 24, marginTop: 4 }}>
        {GAPS.map((gap) => (
          <GapCard key={gap.id} gap={gap} />
        ))}
      </div>

      {/* ── Methodology note ── */}
      <MethodologyNote />

      {/* ── References footer ── */}
      <div className="card" style={{ background: "rgba(30,42,36,0.03)" }}>
        <h4 style={{ margin: "0 0 12px" }}>📚 Key References</h4>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 8 }}>
          {[
            ["Beck et al. (2018)", "Updated Köppen-Geiger global climate classification", "Sci. Reports"],
            ["Scanlon et al. (2012)", "Global water depletion from groundwater", "Nature"],
            ["Rodell et al. (2009)", "GRACE satellite groundwater trends in India", "Nature"],
            ["Lobell et al. (2011)", "Climate trends and crop production", "Science"],
            ["FAO ECOCROP", "Crop water & temperature requirements database", "FAO"],
            ["Steduto et al. (2012)", "AquaCrop — FAO crop-water productivity model", "FAO Irrig. Paper 66"],
            ["Green & Ampt (1911)", "Flow of air and water through soils", "Infiltration theory"],
            ["CGWB (2000–2022)", "Quality-controlled groundwater level observations", "Nature Sci. Data 2025"],
          ].map(([author, title, journal]) => (
            <div key={author} style={{
              padding: "10px 14px",
              background: "rgba(30,42,36,0.04)",
              borderRadius: 8,
              border: "1px solid var(--border)",
              fontSize: "0.78rem",
            }}>
              <div style={{ fontWeight: 700, marginBottom: 2 }}>{author}</div>
              <div style={{ color: "var(--muted)" }}>{title}</div>
              <div style={{ color: "var(--risk-low)", fontStyle: "italic", marginTop: 2 }}>{journal}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default ResearchGaps;
