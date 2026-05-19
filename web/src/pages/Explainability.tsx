import React from "react";
import { useCityContext } from "../state/CityContext";
import { useCityDetail } from "../hooks/useCityDetail";
import { useLanguage } from "../state/LanguageContext";
import { t } from "../i18n";

interface ShapItem { feature: string; score: number; }

const FEATURE_LABELS: Record<string, string> = {
  gdd_annual: "Growing Degree Days",
  monsoon_fraction: "Monsoon Fraction",
  water_deficit: "Water Deficit",
  groundwater_depletion: "GW Depletion Rate",
  recharge_efficiency: "Recharge Efficiency",
  crop_water_deficit: "Crop Water Deficit",
  late_monsoon_fraction: "Late Monsoon",
  koppen_zone: "Köppen Zone",
  cvle_count: "CVLE Count",
  temp_max_annual: "Max Temperature",
  temp_min_annual: "Min Temperature",
  precip_annual: "Annual Precipitation",
};

function prettyFeature(raw: string): string {
  return FEATURE_LABELS[raw] ?? raw.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

const ShapBar: React.FC<{ items: ShapItem[]; delay?: number }> = ({ items, delay = 0 }) => {
  const maxScore = Math.max(...items.map((i) => Math.abs(i.score)));

  return (
    <div className="shap-list">
      {items.map((item, idx) => {
        const pct = maxScore > 0 ? Math.abs(item.score) / maxScore : 0;
        const isPositive = item.score >= 0;
        return (
          <div
            key={item.feature}
            className="shap-row"
            style={{ animationDelay: `${delay + idx * 0.05}s` }}
          >
            <div className="shap-header">
              <span className="shap-feature">{prettyFeature(item.feature)}</span>
              <span className="shap-score">
                {isPositive ? "+" : ""}{item.score.toFixed(4)}
              </span>
            </div>
            <div className="shap-bar-track">
              <div
                className={`shap-bar-fill ${isPositive ? "positive" : "negative"}`}
                style={{
                  "--bar-scale": pct,
                  animationDelay: `${delay + idx * 0.05}s`,
                } as React.CSSProperties}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
};

const Explainability: React.FC = () => {
  const { selectedCity } = useCityContext();
  const { detail, loading, error } = useCityDetail(selectedCity);
  const { lang } = useLanguage();

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <h1>{t(lang, 'nav.explain')}</h1>
          <p>{t(lang, "explain.desc")}</p>
        </div>
        {selectedCity && <span className="tag">{selectedCity}</span>}
      </div>

      {/* Methodology card */}
      <div className="card">
        <div className="card-header">
          <h3>{t(lang, "explain.method")}</h3>
          <span className="tag">SHAP TreeExplainer</span>
        </div>
        <div className="card-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))" }}>
          <div>
            <div style={{ fontSize: "0.78rem", color: "var(--muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 6 }}>{t(lang, "explain.model")}</div>
            <div style={{ fontWeight: 600 }}>Temporal Fusion Transformer</div>
            <div style={{ fontSize: "0.82rem", color: "var(--muted)" }}>5-year encoder · quantile output</div>
          </div>
          <div>
            <div style={{ fontSize: "0.78rem", color: "var(--muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 6 }}>{t(lang, "explain.explainer")}</div>
            <div style={{ fontWeight: 600 }}>SHAP TreeExplainer</div>
            <div style={{ fontSize: "0.82rem", color: "var(--muted)" }}>Random Forest surrogate</div>
          </div>
          <div>
            <div style={{ fontSize: "0.78rem", color: "var(--muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 6 }}>{t(lang, "explain.bar_colour")}</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <div style={{ width: 28, height: 8, borderRadius: 4, background: "#3f7a4a" }} />
                <span style={{ fontSize: "0.82rem" }}>{t(lang, "explain.increases")}</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <div style={{ width: 28, height: 8, borderRadius: 4, background: "#b23a24" }} />
                <span style={{ fontSize: "0.82rem" }}>{t(lang, "explain.decreases")}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {loading && <p>{t(lang, 'loading')}</p>}
      {error && <p className="error">{error}</p>}
      {!selectedCity && <p className="muted">{t(lang, 'select.city.header_hint')}</p>}

      {detail && (
        <>
          <div className="card-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))" }}>
            <div className="card">
              <div className="card-header">
                <h3>{t(lang, "explain.city_drivers")}</h3>
                <span className="tag">{selectedCity}</span>
              </div>
              <p style={{ fontSize: "0.83rem", marginBottom: 16 }}>
                {t(lang, "explain.city_drivers_desc", { city: selectedCity || "" })}
              </p>
              <ShapBar items={detail.shap.city_top} delay={0.1} />
            </div>

            <div className="card">
              <div className="card-header">
                <h3>{t(lang, "explain.global_drivers")}</h3>
                <span className="tag">{t(lang, "explain.all_cities")}</span>
              </div>
              <p style={{ fontSize: "0.83rem", marginBottom: 16 }}>
                {t(lang, "explain.global_desc")}
              </p>
              <ShapBar items={detail.shap.global_top} delay={0.2} />
            </div>
          </div>

          {/* TFT attention weights if available */}
          <div className="card">
            <div className="card-header">
              <h3>{t(lang, "explain.guide")}</h3>
            </div>
            <div className="card-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" }}>
              <div>
                <h4 style={{ fontSize: "0.9rem" }}>{t(lang, "explain.what_shap")}</h4>
                <p style={{ fontSize: "0.83rem" }}>
                  {t(lang, "explain.what_shap_desc")}
                </p>
              </div>
              <div>
                <h4 style={{ fontSize: "0.9rem" }}>{t(lang, "explain.dual")}</h4>
                <p style={{ fontSize: "0.83rem" }}>
                  {t(lang, "explain.dual_desc")}
                </p>
              </div>
              <div>
                <h4 style={{ fontSize: "0.9rem" }}>{t(lang, "explain.city_global")}</h4>
                <p style={{ fontSize: "0.83rem" }}>
                  {t(lang, "explain.city_global_desc")}
                </p>
              </div>
            </div>
          </div>
        </>
      )}
    </section>
  );
};

export default Explainability;
