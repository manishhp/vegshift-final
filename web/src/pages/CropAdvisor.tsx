import React, { useState } from "react";
import { useCityContext } from "../state/CityContext";
import { useCityDetail } from "../hooks/useCityDetail";
import AdvisoryCard from "../components/AdvisoryCard";
import { useLanguage } from "../state/LanguageContext";
import { t } from "../i18n";

const ZONE_LABELS: Record<string, string> = {
  Af: 'Tropical Rainforest (Af)',
  Am: 'Tropical Monsoon (Am)',
  Aw: 'Tropical Savanna (Aw)',
  Csa: 'Hot-Summer Mediterranean (Csa)',
  Csb: 'Warm-Summer Mediterranean (Csb)',
  Cwa: 'Humid Subtropical, Dry Winter (Cwa)',
  Cwb: 'Subtropical Highland, Monsoon (Cwb)',
  Cfa: 'Humid Subtropical (Cfa)',
  Cfb: 'Oceanic (Cfb)',
  BWh: 'Hot Desert (BWh)',
  BWk: 'Cold Desert (BWk)',
  BSh: 'Hot Semi-Arid (BSh)',
  BSk: 'Cold Semi-Arid (BSk)',
};

const getZoneLabel = (zone?: string) => zone ? (ZONE_LABELS[zone] ?? zone) : '';

const CropAdvisor: React.FC = () => {
  const { selectedCity } = useCityContext();
  const { detail, loading, error } = useCityDetail(selectedCity);
  const [filter, setFilter] = useState<"all" | "kharif" | "rabi" | "annual">("all");

  const crops = detail?.advisory.ranked_crops ?? [];
  const filtered = filter === "all" ? crops : crops.filter((c) => c.season === filter);
  const { lang } = useLanguage();

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <h1>{t(lang, 'nav.crops')}</h1>
          <p>{t(lang, "crops.desc")}</p>
        </div>
        {selectedCity && <span className="tag">{selectedCity} · {getZoneLabel(detail?.advisory.current_zone)}</span>}
      </div>

      {/* Scoring methodology */}
      <div className="card">
          <div className="card-header">
          <h3>{t(lang, "crops.method")}</h3>
          <span className="tag">{t(lang, "crops.pipeline_output")}</span>
        </div>
        <div className="card-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))" }}>
          <div>
            <div style={{ fontSize: "0.78rem", color: "var(--muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 6 }}>{t(lang, "crops.gaez")}</div>
            <p style={{ fontSize: "0.83rem", margin: 0 }}>{t(lang, "crops.gaez_desc")}</p>
          </div>
          <div>
            <div style={{ fontSize: "0.78rem", color: "var(--muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 6 }}>{t(lang, "crops.trajectory")}</div>
            <p style={{ fontSize: "0.83rem", margin: 0 }}>{t(lang, "crops.trajectory_desc")}</p>
          </div>
          <div>
            <div style={{ fontSize: "0.78rem", color: "var(--muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 6 }}>{t(lang, "crops.zone_alignment")}</div>
            <p style={{ fontSize: "0.83rem", margin: 0 }}>{t(lang, "crops.zone_alignment_desc")}</p>
          </div>
        </div>
      </div>

      {/* Season filter */}
      {detail && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {(["all", "kharif", "rabi", "annual"] as const).map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setFilter(s)}
              style={{
                background: filter === s ? "var(--accent)" : "rgba(30,42,36,0.07)",
                color: filter === s ? "white" : "var(--muted)",
                border: "1px solid",
                borderColor: filter === s ? "var(--accent)" : "var(--border)",
                borderRadius: 999,
                padding: "6px 16px",
                cursor: "pointer",
                fontWeight: 600,
                fontSize: "0.85rem",
                textTransform: "capitalize",
              }}
            >
              {s === "all"
                ? `${t(lang, "season.all")} (${crops.length})`
                : `${t(lang, `season.${s}`)} (${crops.filter(c => c.season === s).length})`}
            </button>
          ))}
        </div>
      )}

      {loading && <p>{t(lang, 'loading')}</p>}
      {error && <p className="error">{error}</p>}
      {!selectedCity && <p className="muted">{t(lang, 'select.city.header_hint')}</p>}

      {detail && (
        <div className="card-grid">
          {filtered.map((crop, idx) => (
            <AdvisoryCard
              key={`${crop.crop}-${idx}`}
              crop={crop}
              rank={idx + 1}
              climateContext={detail.advisory.climate_context}
              currentZone={detail.advisory.current_zone}
            />
          ))}
        </div>
      )}

      {detail && filtered.length === 0 && (
        <div className="card muted">{t(lang, "crops.empty", { season: t(lang, `season.${filter}`) })}</div>
      )}
    </section>
  );
};

export default CropAdvisor;
