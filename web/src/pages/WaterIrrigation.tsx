import React from "react";
import { useCityContext } from "../state/CityContext";
import { useCityDetail } from "../hooks/useCityDetail";
import ActionSteps from "../components/ActionSteps";
import { useLanguage } from "../state/LanguageContext";
import { t } from "../i18n";
import type { Lang } from "../i18n";
import { capitalizeWords } from "../utils/text";

const RSI_INFO: Record<string, { color: string; descKey: string }> = {
  low:    { color: "var(--risk-low)",    descKey: "water.rsi.low" },
  medium: { color: "var(--risk-medium)", descKey: "water.rsi.medium" },
  high:   { color: "var(--risk-high)",   descKey: "water.rsi.high" },
};

const RsiGauge: React.FC<{ level: string; lang: Lang }> = ({ level, lang }) => {
  const key = level?.toLowerCase() as keyof typeof RSI_INFO;
  const info = RSI_INFO[key] ?? { color: "var(--muted)", descKey: "" };
  const pct = key === "low" ? 0.25 : key === "medium" ? 0.6 : 0.92;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontWeight: 700, color: info.color, textTransform: "capitalize", fontSize: "1.2rem" }}>
          {t(lang, `risk.${key}`)}
        </span>
        <span className={`tag risk-${key}`}>{t(lang, "water.rsi_level")}</span>
      </div>
      <div style={{ height: 10, borderRadius: 999, background: "rgba(30,42,36,0.08)", overflow: "hidden" }}>
        <div style={{
          width: `${pct * 100}%`,
          height: "100%",
          background: info.color,
          borderRadius: 999,
          transition: "width 0.8s ease",
        }} />
      </div>
      <p style={{ margin: 0, fontSize: "0.83rem" }}>{info.descKey ? t(lang, info.descKey) : level}</p>
    </div>
  );
};

const WaterIrrigation: React.FC = () => {
  const { selectedCity } = useCityContext();
  const { detail, loading, error } = useCityDetail(selectedCity);
  const { lang } = useLanguage();

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <h1>{t(lang, 'nav.water')}</h1>
          <p>{t(lang, "water.desc")}</p>
        </div>
        {selectedCity && <span className="tag">{selectedCity}</span>}
      </div>

      {loading && <p>{t(lang, 'loading')}</p>}
      {error && <p className="error">{error}</p>}
      {!selectedCity && <p className="muted">{t(lang, 'select.city.header_hint')}</p>}

      {detail && (
        <>
          {/* GW metrics */}
          <div className="card-grid">
            <div className="card">
              <div className="card-header">
                <h3>{t(lang, "water.rsi")}</h3>
              </div>
              <RsiGauge level={detail.irrigation.rsi_level} lang={lang} />
            </div>

            <div className="card metric-card">
              <div className="metric-label">{t(lang, "water.gw_depth")}</div>
              <div className="metric-value">
                {detail.irrigation.gw_depth_mbgl}
                <span style={{ fontSize: "0.9rem", fontWeight: 400, color: "var(--muted)", marginLeft: 4 }}>mbgl</span>
              </div>
              <p style={{ margin: 0, fontSize: "0.83rem" }}>{t(lang, "water.mbgl")}</p>
            </div>

            <div className="card metric-card">
              <div className="metric-label">{t(lang, "water.depletion")}</div>
              <div className="metric-value metric-delta negative" style={{ fontSize: "1.4rem" }}>
                {detail.irrigation.depletion_rate}
              </div>
              <p style={{ margin: 0, fontSize: "0.83rem" }}>{t(lang, "water.depletion_desc")}</p>
            </div>

            <div className="card metric-card">
              <div className="metric-label">{t(lang, "water.recharge_eff")}</div>
              <div className="metric-value metric-delta positive" style={{ fontSize: "1.4rem" }}>
                {detail.irrigation.recharge_efficiency}
              </div>
              <p style={{ margin: 0, fontSize: "0.83rem" }}>{t(lang, "water.recharge_desc")}</p>
            </div>
          </div>

          {/* Irrigation guidance */}
          <div className="card-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))" }}>
            <ActionSteps
              irrigationMethod={detail.irrigation.irrigation_method}
              sowingWindow={detail.irrigation.optimal_sow_window}
              avoidCrops={detail.irrigation.avoid_crops}
              recommendedCrops={detail.irrigation.recommended_crops}
            />
            <div className="card">
              <h3>{t(lang, "water.sowing_guidance")}</h3>
              <div style={{ display: "grid", gap: 14 }}>
                <div>
                  <div style={{ fontSize: "0.78rem", color: "var(--muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 6 }}>
                    {t(lang, "water.optimal_window")}
                  </div>
                  <span className="tag" style={{ fontSize: "0.85rem" }}>
                    📅 {detail.irrigation.optimal_sow_window}
                  </span>
                </div>
                {detail.irrigation.recommended_crops?.length > 0 && (
                  <div>
                    <div style={{ fontSize: "0.78rem", color: "var(--muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8 }}>
                      {t(lang, "water.compatible_crops")}
                    </div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                      {detail.irrigation.recommended_crops.map((c: string) => (
                        <span key={c} className="tag risk-low" style={{ fontSize: "0.8rem" }}>✓ {capitalizeWords(c)}</span>
                      ))}
                    </div>
                  </div>
                )}
                {detail.irrigation.avoid_crops?.length > 0 && (
                  <div>
                    <div style={{ fontSize: "0.78rem", color: "var(--muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8 }}>
                      {t(lang, "water.avoid_crops")}
                    </div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                      {detail.irrigation.avoid_crops.map((c: string) => (
                        <span key={c} className="tag risk-high" style={{ fontSize: "0.8rem" }}>✗ {capitalizeWords(c)}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Water conservation note */}
          <div className="card" style={{ background: "rgba(13, 117, 182, 0.06)", borderColor: "rgba(13, 117, 182, 0.2)" }}>
            <div style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
              <span style={{ fontSize: "2rem" }}>💧</span>
              <div>
                <h4 style={{ margin: "0 0 6px" }}>{t(lang, "water.conservation_title")}</h4>
                <p style={{ margin: 0, fontSize: "0.875rem" }}>
                  {t(lang, "water.conservation_desc")}
                </p>
              </div>
            </div>
          </div>
        </>
      )}
    </section>
  );
};

export default WaterIrrigation;
