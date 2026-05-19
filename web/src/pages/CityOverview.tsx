import React from "react";
import { useCityContext } from "../state/CityContext";
import { useCityDetail } from "../hooks/useCityDetail";
import EvidenceCard from "../components/EvidenceCard";
import RiskMeter from "../components/RiskMeter";
import TrendStrip from "../components/TrendStrip";
import { useLanguage } from "../state/LanguageContext";
import { t } from "../i18n";
import { capitalizeWords } from "../utils/text";

const CityOverview: React.FC = () => {
  const { selectedCity, cities } = useCityContext();
  const summary = cities.find((c) => c.city === selectedCity);
  const { detail, loading, error } = useCityDetail(selectedCity);

  const { lang } = useLanguage();

  if (!selectedCity || !summary) {
    return (
      <section className="page">
        <div className="card" style={{ textAlign: "center", padding: 48 }}>
          <div style={{ fontSize: "3rem", marginBottom: 16 }}>🗺️</div>
          <h3>{t(lang, 'dashboard.no_city')}</h3>
          <p>{t(lang, 'select.city.placeholder')}</p>
        </div>
      </section>
    );
  }

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <h1>{selectedCity}</h1>
          <p>{t(lang, "city.desc")}</p>
        </div>
        <RiskMeter level={summary.risk_level} />
      </div>

      {/* Key metrics */}
      <div className="card-grid">
        <div className="card metric-card">
          <div className="metric-label">{t(lang, "dashboard.current_zone")}</div>
          <div className="metric-value" style={{ fontSize: "1.4rem" }}>
            {detail?.advisory.current_zone ?? summary.current_zone ?? "—"}
          </div>
          <p style={{ fontSize: "0.8rem", margin: 0 }}>{t(lang, "dashboard.koppen")}</p>
        </div>
        <div className="card metric-card">
          <div className="metric-label">{t(lang, "dashboard.cvle_5yr")}</div>
          <div className={`metric-value ${(summary.recent_cvle_count ?? 0) >= 2 ? "metric-delta negative" : "metric-delta positive"}`}>
            {summary.recent_cvle_count}
          </div>
          <p style={{ fontSize: "0.8rem", margin: 0 }}>{t(lang, "dashboard.cvle_desc")}</p>
        </div>
        <div className="card metric-card">
          <div className="metric-label">{t(lang, 'risk.level')}</div>
          <div className={`metric-value metric-delta ${summary.risk_level === "high" ? "negative" : summary.risk_level === "low" ? "positive" : ""}`} style={{ fontSize: "1.3rem", textTransform: "capitalize" }}>
            {t(lang, `risk.${summary.risk_level}`)}
          </div>
          <p style={{ fontSize: "0.8rem", margin: 0 }}>{t(lang, "city.risk_desc")}</p>
        </div>
        {detail && (
          <div className="card metric-card">
            <div className="metric-label">{t(lang, "dashboard.trend_slope")}</div>
            <div className={`metric-value ${detail.trend.trend === "deteriorating" ? "metric-delta negative" : detail.trend.trend === "improving" ? "metric-delta positive" : ""}`}>
              {detail.trend.slope.toFixed(4)}
            </div>
            <p style={{ fontSize: "0.8rem", margin: 0 }}>{t(lang, "dashboard.per_year_r2", { r2: detail.trend.r_squared.toFixed(3) })}</p>
          </div>
        )}
      </div>

      {/* Top crops */}
      {summary.top_crops.length > 0 && (
        <div className="card">
          <div className="card-header">
            <h3>{t(lang, "city.crop_recommendations")}</h3>
            <span className="tag">{t(lang, "city.ranked")}</span>
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            {summary.top_crops.map((c, i) => (
              <div key={c.crop} style={{
                background: i === 0 ? "rgba(63,122,74,0.12)" : "rgba(30,42,36,0.06)",
                border: `1px solid ${i === 0 ? "rgba(63,122,74,0.3)" : "var(--border)"}`,
                borderRadius: 12,
                padding: "8px 16px",
                display: "flex",
                alignItems: "center",
                gap: 8,
              }}>
                <span style={{ fontWeight: 700, color: "var(--accent-dark)" }}>#{i + 1}</span>
                <span style={{ fontWeight: 600 }}>{capitalizeWords(c.crop)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {loading && <p>{t(lang, "loading")}</p>}
      {error && <p className="error">{error}</p>}

      {detail && (
        <>
          {/* Trend */}
          {detail.trend && <TrendStrip slope={detail.trend.slope} trend={detail.trend.trend} />}

          {/* Climate transitions */}
          <div className="section">
            <div className="section-head">
              <h2>{t(lang, "city.transitions_title")}</h2>
              <span className="tag">{t(lang, "city.detected", { count: String(detail.transitions.length) })}</span>
            </div>
            {detail.transitions.length > 0 ? (
              <div className="table">
                {detail.transitions.map((item, idx) => (
                  <div key={`${item.transition_year}-${idx}`} className="table-row">
                    <div className="year-pill">{item.transition_year}</div>
                    <div>
                      <strong>{item.from_zone}</strong>
                      <span style={{ margin: "0 8px", color: "var(--muted)" }}>→</span>
                      <strong>{item.to_zone}</strong>
                    </div>
                    <div style={{ color: "var(--muted)", fontSize: "0.83rem" }}>
                      {t(lang, "city.confirmed", { count: String(item.years_confirmed) })}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="card muted">
                {t(lang, "city.no_koppen", { city: selectedCity })}
                {t(lang, 'koppen.stable_explain')}
              </div>
            )}
          </div>

          {/* Evidence */}
          <div className="section">
            <h2>{t(lang, "city.ground_evidence")}</h2>
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

export default CityOverview;
