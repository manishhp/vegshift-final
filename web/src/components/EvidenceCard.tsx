import React from "react";
import type { EvidenceItem } from "../api/types";
import { useLanguage } from "../state/LanguageContext";
import { t } from "../i18n";

const EvidenceCard: React.FC<{ item: EvidenceItem }> = ({ item }) => {
  const { lang } = useLanguage();
  return (
    <article className={`card evidence-card ${item.is_placeholder ? "placeholder" : ""}`}>
      <div className="evidence-header">
        <h4>{item.title}</h4>
        <span>{item.source}</span>
      </div>
      <p>{item.summary}</p>
      <div className="evidence-footer">
        <span>{item.date !== "YYYY-MM-DD" ? item.date : ""}</span>
        {item.url ? (
          <a href={item.url} target="_blank" rel="noreferrer">
            {t(lang, 'evidence.view')}
          </a>
        ) : item.is_placeholder ? (
          <span className="muted">{t(lang, 'evidence.pending')}</span>
        ) : null}
      </div>
    </article>
  );
};

export default EvidenceCard;
