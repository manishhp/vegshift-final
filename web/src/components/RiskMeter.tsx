import React from "react";
import type { RiskLevel } from "../api/types";
import { useLanguage } from "../state/LanguageContext";
import { t } from "../i18n";

const RiskMeter: React.FC<{ level: RiskLevel; showText?: boolean }> = ({ level, showText = true }) => {
  const { lang } = useLanguage();
  const labels: Record<RiskLevel, string> = {
    low: t(lang, 'risk.low'),
    medium: t(lang, 'risk.medium'),
    high: t(lang, 'risk.high'),
  };

  return (
    <div className={`risk-meter risk-${level}`}>
      <div className="risk-bar" />
      {showText ? (
        <div className="risk-text">
          <span>{t(lang, 'risk.level')}</span>
          <strong>{labels[level]}</strong>
        </div>
      ) : null}
    </div>
  );
};

export default RiskMeter;
