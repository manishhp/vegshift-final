import React from "react";
import { useLanguage } from "../state/LanguageContext";
import { t } from "../i18n";

interface TrendStripProps {
  slope: number;
  trend: string;
}

const CONFIG = (lang: string) => ({
  deteriorating: { icon: "↘", label: t(lang as any, 'trend.deteriorating.label'), desc: t(lang as any, 'trend.deteriorating.desc') },
  improving:     { icon: "↗", label: t(lang as any, 'trend.improving.label'),     desc: t(lang as any, 'trend.improving.desc') },
  stable:        { icon: "→", label: t(lang as any, 'trend.stable.label'),        desc: t(lang as any, 'trend.stable.desc') },
} as const);

const TrendStrip: React.FC<TrendStripProps> = ({ slope, trend }) => {
  const { lang } = useLanguage();
  const cfgs = CONFIG(lang);
  const cfg = (cfgs as any)[trend] ?? cfgs.stable;

  return (
    <div className={`trend-strip ${trend}`}>
      <span style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <span style={{ fontSize: "1.35rem", lineHeight: 1 }}>{cfg.icon}</span>
        <span>
          <strong>{cfg.label}</strong>
          <span style={{ fontWeight: 400, opacity: 0.75, marginLeft: 6, fontSize: "0.82rem" }}>
            — {cfg.desc}
          </span>
        </span>
      </span>
      <span style={{ fontVariantNumeric: "tabular-nums", fontSize: "0.875rem", fontWeight: 700 }}>
        {slope >= 0 ? "+" : ""}{slope.toFixed(4)}<span style={{ fontWeight: 400, opacity: 0.7, fontSize: "0.78rem", marginLeft: 3 }}>/yr</span>
      </span>
    </div>
  );
};

export default TrendStrip;
