import React, { useState } from "react";
import { useLanguage } from "../state/LanguageContext";
import { t } from "../i18n";
import Explainability from "./Explainability";
import ModelComparison from "./ModelComparison";
import TechStack from "./TechStack";

type InsightSection = "explain" | "compare" | "tech";

const SECTION_META: Record<InsightSection, { title: string; description: string }> = {
  explain: {
    title: "Explainability",
    description: "Understand why the model makes the predictions it does for each city.",
  },
  compare: {
    title: "Model Comparison",
    description: "Compare the performance of alternative models and see why TFT is chosen.",
  },
  tech: {
    title: "Tech Stack",
    description: "Review the software and infrastructure used to build VegShift.",
  },
};

const Insights: React.FC = () => {
  const [selected, setSelected] = useState<InsightSection | null>(null);
  const { lang } = useLanguage();

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <h1>{t(lang, "nav.insights")}</h1>
          <p>
            Select one of the insight views below to explore explainability, model
            comparison, or the platform technology stack.
          </p>
        </div>
      </div>

      {!selected ? (
        <div className="card" style={{ display: "grid", gap: "16px" }}>
          <h2>Choose an insight</h2>
          <div style={{ display: "grid", gap: "12px" }}>
            {Object.entries(SECTION_META).map(([key, meta]) => (
              <button
                key={key}
                type="button"
                className="button"
                style={{ textAlign: "left" }}
                onClick={() => setSelected(key as InsightSection)}
              >
                <div style={{ fontWeight: 700, marginBottom: 6 }}>{meta.title}</div>
                <div style={{ color: "var(--muted)", fontSize: "0.92rem" }}>{meta.description}</div>
              </button>
            ))}
          </div>
        </div>
      ) : (
        <>
          <div style={{ marginBottom: 18 }}>
            <button type="button" className="ghost" onClick={() => setSelected(null)}>
              ← Back to insights
            </button>
          </div>
          {selected === "explain" && <Explainability />}
          {selected === "compare" && <ModelComparison />}
          {selected === "tech" && <TechStack />}
        </>
      )}
    </section>
  );
};

export default Insights;
