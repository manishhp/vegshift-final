import React from "react";
import { useCityContext } from "../state/CityContext";
import { useCityDetail } from "../hooks/useCityDetail";
import { useLanguage } from "../state/LanguageContext";
import { t } from "../i18n";

const EconomicProtection: React.FC = () => {
  const { selectedCity } = useCityContext();
  const { detail, loading, error } = useCityDetail(selectedCity);
  const { lang } = useLanguage();

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <h1>{t(lang, "economic.title")}</h1>
          <p>{t(lang, "economic.desc")}</p>
        </div>
        {selectedCity && <span className="tag">{selectedCity}</span>}
      </div>

      {loading && <p>{t(lang, "economic.loading")}</p>}
      {error && <p className="error">{error}</p>}
      {!selectedCity && (
        <p className="muted">{t(lang, 'select.city.header_hint')}</p>
      )}

      {detail && (
        <>
          {/* Alert banner */}
          {detail.eri.alert && (
            <div className="card" style={{
              background: "rgba(178, 58, 36, 0.07)",
              borderColor: "rgba(178, 58, 36, 0.3)",
              display: "flex", gap: 14, alignItems: "center",
            }}>
              <span style={{ fontSize: "2rem" }}>⚠️</span>
              <div>
                <h4 style={{ margin: "0 0 4px", color: "var(--risk-high)" }}>{t(lang, "dashboard.high_eri")}</h4>
                <p style={{ margin: 0, fontSize: "0.875rem" }}>
                  {t(lang, "economic.alert_desc", { city: selectedCity || "" })}
                </p>
              </div>
            </div>
          )}

          {/* Key numbers */}
          <div className="card-grid">
            <div className="card metric-card">
              <div className="metric-label">{t(lang, "dashboard.eri")}</div>
              <div className={`metric-value ${detail.eri.alert ? "metric-delta negative" : "metric-delta positive"}`}>
                {(detail.eri.eri * 100).toFixed(1)}%
              </div>
              <p style={{ fontSize: "0.8rem", margin: 0 }}>
                {detail.eri.alert ? t(lang, "economic.above") : t(lang, "economic.safe")}
              </p>
            </div>
            <div className="card metric-card">
              <div className="metric-label">{t(lang, "economic.primary_crop")}</div>
              <div className="metric-value" style={{ fontSize: "1.3rem", textTransform: "capitalize" }}>
                {detail.eri.primary_crop ?? "—"}
              </div>
              <p style={{ fontSize: "0.8rem", margin: 0 }}>{t(lang, "economic.primary_desc")}</p>
            </div>
            <div className="card metric-card">
              <div className="metric-label">{t(lang, "economic.msp_per")}</div>
              <div className="metric-value" style={{ fontSize: "1.4rem" }}>
                {detail.eri.msp_inr_per_quintal ? `₹${detail.eri.msp_inr_per_quintal}` : t(lang, "not_available")}
              </div>
              <p style={{ fontSize: "0.8rem", margin: 0 }}>{t(lang, "economic.msp_desc")}</p>
            </div>
            <div className="card metric-card">
              <div className="metric-label">{t(lang, "dashboard.distress_floor")}</div>
              <div className="metric-value metric-delta negative" style={{ fontSize: "1.4rem" }}>
                {detail.eri.distress_price_threshold ? `₹${detail.eri.distress_price_threshold}` : t(lang, "not_available")}
              </div>
              <p style={{ fontSize: "0.8rem", margin: 0 }}>{t(lang, "economic.floor_desc")}</p>
            </div>
          </div>

          {/* Schemes + crops */}
          <div className="card-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))" }}>
            <div className="card">
              <h3>{t(lang, "economic.schemes")}</h3>
              <div style={{ display: "grid", gap: 12 }}>
                {detail.eri.procurement_center && (
                  <div style={{ padding: "12px 16px", background: "rgba(30,42,36,0.05)", borderRadius: 12, border: "1px solid var(--border)" }}>
                    <div style={{ fontSize: "0.75rem", color: "var(--muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 4 }}>
                      {t(lang, "economic.procurement")}
                    </div>
                    <div style={{ fontWeight: 600 }}>{detail.eri.procurement_center}</div>
                  </div>
                )}
                {detail.eri.crop_insurance_scheme && (
                  <div style={{ padding: "12px 16px", background: "rgba(30,42,36,0.05)", borderRadius: 12, border: "1px solid var(--border)" }}>
                    <div style={{ fontSize: "0.75rem", color: "var(--muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 4 }}>
                      {t(lang, "economic.insurance")}
                    </div>
                    <div style={{ fontWeight: 600 }}>{detail.eri.crop_insurance_scheme}</div>
                  </div>
                )}
              </div>
            </div>

            {detail.eri.alternative_crops?.length > 0 && (
              <div className="card">
                <h3>{t(lang, "economic.alternatives")}</h3>
                <p style={{ fontSize: "0.83rem", marginBottom: 14 }}>
                  {t(lang, "economic.alt_desc")}
                </p>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                  {detail.eri.alternative_crops.map((crop: string) => (
                    <span key={crop} className="tag risk-low" style={{ fontSize: "0.83rem" }}>
                      ✓ {crop}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Info card */}
          <div className="card" style={{ background: "rgba(245, 158, 11, 0.06)", borderColor: "rgba(245, 158, 11, 0.2)" }}>
            <div style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
              <span style={{ fontSize: "2rem" }}>📜</span>
              <div>
                <h4 style={{ margin: "0 0 6px" }}>{t(lang, "economic.about_title")}</h4>
                <p style={{ margin: 0, fontSize: "0.875rem" }}>
                  {t(lang, "economic.about_desc")}
                </p>
              </div>
            </div>
          </div>
        </>
      )}
    </section>
  );
};

export default EconomicProtection;
