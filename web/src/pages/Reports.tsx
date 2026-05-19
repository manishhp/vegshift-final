import React, { useState } from "react";
import { jsPDF } from "jspdf";
import { useCityContext } from "../state/CityContext";
import { useCityDetail } from "../hooks/useCityDetail";
import { useLanguage } from "../state/LanguageContext";
import { t } from "../i18n";
import { capitalizeWords } from "../utils/text";

const ZONE_LABELS: Record<string, string> = {
  Af: "Tropical Rainforest (Af)", Am: "Tropical Monsoon (Am)", Aw: "Tropical Savanna (Aw)",
  Csa: "Hot-Summer Mediterranean (Csa)", Csb: "Warm-Summer Mediterranean (Csb)",
  Cwa: "Humid Subtropical, Dry Winter (Cwa)", Cwb: "Subtropical Highland, Monsoon (Cwb)",
  Cfa: "Humid Subtropical (Cfa)", Cfb: "Oceanic (Cfb)",
  BWh: "Hot Desert (BWh)", BWk: "Cold Desert (BWk)",
  BSh: "Hot Semi-Arid (BSh)", BSk: "Cold Semi-Arid (BSk)",
};

const Reports: React.FC = () => {
  const { selectedCity } = useCityContext();
  const { detail, loading, error } = useCityDetail(selectedCity);
  const [downloaded, setDownloaded] = useState(false);
  const { lang } = useLanguage();

  const handleDownloadPDF = () => {
    if (!detail || !selectedCity) return;

    const doc = new jsPDF({ unit: "mm", format: "a4" });
    const W = 210;
    const margin = 18;
    const contentW = W - margin * 2;
    let y = 0;

    const green = [42, 90, 55] as [number, number, number];
    const darkGreen = [30, 60, 38] as [number, number, number];
    const lightGreen = [235, 245, 238] as [number, number, number];
    const muted = [100, 110, 105] as [number, number, number];
    const black = [20, 20, 20] as [number, number, number];
    const white = [255, 255, 255] as [number, number, number];
    const red = [180, 40, 40] as [number, number, number];
    const amber = [160, 100, 20] as [number, number, number];

    // ── Header band ──
    doc.setFillColor(...darkGreen);
    doc.rect(0, 0, W, 36, "F");
    doc.setTextColor(...white);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(20);
    doc.text("VegShift", margin, 16);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(9);
    doc.text("Climate-adaptive crop advisory · AI-powered agriculture", margin, 23);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(13);
    doc.text(`City Report: ${selectedCity}`, margin, 31);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(8);
    doc.text(`Generated ${new Date().toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" })}`, W - margin, 31, { align: "right" });

    y = 44;

    // ── Helper functions ──
    const sectionHeader = (title: string) => {
      doc.setFillColor(...lightGreen);
      doc.roundedRect(margin, y, contentW, 8, 1.5, 1.5, "F");
      doc.setFont("helvetica", "bold");
      doc.setFontSize(9);
      doc.setTextColor(...darkGreen);
      doc.text(title.toUpperCase(), margin + 4, y + 5.5);
      y += 12;
    };

    const row = (label: string, value: string, valueColor?: [number, number, number]) => {
      doc.setFont("helvetica", "normal");
      doc.setFontSize(8.5);
      doc.setTextColor(...muted);
      doc.text(label, margin, y);
      doc.setFont("helvetica", "bold");
      doc.setTextColor(...(valueColor ?? black));
      doc.text(value, margin + 52, y);
      y += 6;
    };

    const divider = () => {
      doc.setDrawColor(220, 230, 225);
      doc.setLineWidth(0.3);
      doc.line(margin, y, W - margin, y);
      y += 4;
    };

    // ── Section 1: Climate Overview ──
    sectionHeader("Climate Overview");
    const zone = detail.advisory.current_zone;
    row("Köppen Zone", ZONE_LABELS[zone] ?? zone);
    row("Climate Trend", capitalizeWords(detail.trend.trend), detail.trend.trend === "deteriorating" ? red : green);
    row("Trend Slope", `${detail.trend.slope.toFixed(4)} per year`);
    row("R²", detail.trend.r_squared.toFixed(3));
    row("Transitions Detected", `${detail.transitions.length}`);
    y += 2;

    // Climate transitions table
    if (detail.transitions.length > 0) {
      doc.setFont("helvetica", "bold");
      doc.setFontSize(8);
      doc.setTextColor(...muted);
      doc.text("Year", margin, y);
      doc.text("From", margin + 22, y);
      doc.text("To", margin + 42, y);
      doc.text("Confirmed (yrs)", margin + 62, y);
      y += 5;
      divider();
      detail.transitions.slice(0, 5).forEach((tr: any) => {
        doc.setFont("helvetica", "normal");
        doc.setFontSize(8.5);
        doc.setTextColor(...black);
        doc.text(String(tr.transition_year), margin, y);
        doc.text(tr.from_zone, margin + 22, y);
        doc.text(tr.to_zone, margin + 42, y);
        doc.text(String(tr.years_confirmed), margin + 62, y);
        y += 5.5;
      });
    }
    y += 4;

    // ── Section 2: Crop Advisory ──
    sectionHeader("Crop Advisory");
    const crops = detail.advisory.ranked_crops.slice(0, 8);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(8);
    doc.setTextColor(...muted);
    doc.text("Rank", margin, y);
    doc.text("Crop", margin + 16, y);
    doc.text("Score", margin + 68, y);
    doc.text("Season", margin + 90, y);
    doc.text("Viability", margin + 118, y);
    y += 5;
    divider();

    crops.forEach((c: any, i: number) => {
      const viability = c.score >= 70 ? "High" : c.score >= 45 ? "Medium" : "Low";
      const vColor: [number, number, number] = c.score >= 70 ? green : c.score >= 45 ? amber : red;
      doc.setFont("helvetica", "bold");
      doc.setFontSize(8.5);
      doc.setTextColor(...darkGreen);
      doc.text(`#${i + 1}`, margin, y);
      doc.setFont("helvetica", "normal");
      doc.setTextColor(...black);
      doc.text(capitalizeWords(c.crop), margin + 16, y);
      doc.text(String(c.score), margin + 68, y);
      doc.text(capitalizeWords(c.season ?? "—"), margin + 90, y);
      doc.setFont("helvetica", "bold");
      doc.setTextColor(...vColor);
      doc.text(viability, margin + 118, y);
      y += 5.5;
    });
    y += 4;

    // ── Section 3: Water & Irrigation ──
    sectionHeader("Water & Irrigation");
    row("Irrigation Method", capitalizeWords(detail.irrigation.irrigation_method ?? "—"));
    row("Groundwater Depth", `${detail.irrigation.gw_depth_mbgl} mbgl`);
    row("Depletion Rate", `${detail.irrigation.depletion_rate}`);
    row("Recharge Efficiency", `${detail.irrigation.recharge_efficiency}`);
    row("Optimal Sowing Window", detail.irrigation.optimal_sow_window ?? "—");

    if (detail.irrigation.avoid_crops?.length) {
      row("Avoid Crops", detail.irrigation.avoid_crops.map(capitalizeWords).join(", "), red);
    }
    if (detail.irrigation.recommended_crops?.length) {
      row("Recommended Crops", detail.irrigation.recommended_crops.slice(0, 5).map(capitalizeWords).join(", "), green);
    }
    y += 4;

    // ── Section 4: Economic Risk Index ──
    sectionHeader("Economic Risk Index (ERI)");
    const eriPct = (detail.eri.eri * 100).toFixed(1);
    const eriColor: [number, number, number] = detail.eri.alert ? red : green;
    row("ERI Score", `${eriPct}%`, eriColor);
    row("Alert Status", detail.eri.alert ? "⚠ HIGH RISK — get PMFBY insurance" : "✓ Stable — low risk", eriColor);
    if (detail.eri.msp_inr_per_quintal) {
      row("MSP (govt. floor price)", `₹${detail.eri.msp_inr_per_quintal} / quintal`);
    }
    if (detail.eri.distress_price_threshold) {
      row("Distress Threshold", `₹${detail.eri.distress_price_threshold} — don't accept below this`);
    }
    y += 4;

    // ── Section 5: SHAP Drivers ──
    if (detail.shap?.city_top?.length) {
      sectionHeader("Top Climate Drivers (SHAP)");
      doc.setFont("helvetica", "bold");
      doc.setFontSize(8);
      doc.setTextColor(...muted);
      doc.text("Feature", margin, y);
      doc.text("Impact", margin + 90, y);
      y += 5;
      divider();
      detail.shap.city_top.slice(0, 6).forEach((d: any) => {
        const impact = parseFloat(d.mean_shap ?? d.shap ?? 0);
        const impactColor: [number, number, number] = impact > 0 ? green : red;
        doc.setFont("helvetica", "normal");
        doc.setFontSize(8.5);
        doc.setTextColor(...black);
        doc.text(d.feature ?? d.name ?? "—", margin, y);
        doc.setFont("helvetica", "bold");
        doc.setTextColor(...impactColor);
        doc.text(`${impact > 0 ? "+" : ""}${impact.toFixed(3)}`, margin + 90, y);
        y += 5.5;
      });
      y += 4;
    }

    // ── Footer ──
    const pageH = 297;
    doc.setFillColor(...darkGreen);
    doc.rect(0, pageH - 12, W, 12, "F");
    doc.setFont("helvetica", "normal");
    doc.setFontSize(7.5);
    doc.setTextColor(...white);
    doc.text("VegShift · SDG 13 Climate Action · Built for Indian farmers and agricultural advisors", margin, pageH - 4.5);
    doc.text("vegshift.app", W - margin, pageH - 4.5, { align: "right" });

    doc.save(`vegshift-${selectedCity.toLowerCase().replace(/\s+/g, "-")}-report.pdf`);
    setDownloaded(true);
    setTimeout(() => setDownloaded(false), 3000);
  };

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <h1>{t(lang, 'nav.reports')}</h1>
          <p>{t(lang, "reports.desc")}</p>
        </div>
      </div>

      <div className="card-grid">
        {/* PDF Download */}
        <div className="card">
          <div style={{ fontSize: "2.5rem", marginBottom: 12 }}>📄</div>
          <h3>{selectedCity ? `${selectedCity} Full Report` : "City Report"}</h3>
          <p style={{ fontSize: "0.875rem" }}>
            Formatted PDF with climate outlook, crop advisory, irrigation strategy, ERI scores, and SHAP drivers.
          </p>
          {!selectedCity && (
            <p style={{ fontSize: "0.8rem", color: "var(--risk-medium)", marginTop: 8 }}>
              {t(lang, 'select.city.header_hint')}
            </p>
          )}
          {loading && <p style={{ fontSize: "0.875rem" }}>{t(lang, "reports.preparing")}</p>}
          {error && <p className="error">{error}</p>}
          <button
            type="button"
            className="primary"
            onClick={handleDownloadPDF}
            disabled={!detail || loading}
            style={{ marginTop: 12 }}
          >
            {downloaded ? "Downloaded!" : "Download PDF"}
          </button>
        </div>

        {/* Pipeline info */}
        <div className="card">
          <div style={{ fontSize: "2.5rem", marginBottom: 12 }}>🧬</div>
          <h3>{t(lang, "reports.pipeline_docs")}</h3>
          <p style={{ fontSize: "0.875rem" }}>
            {t(lang, "reports.pipeline_desc")}
          </p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 12 }}>
            <span className="tag">17 steps</span>
            <span className="tag">250 rows master dataset</span>
            <span className="tag">3 raw datasets</span>
          </div>
        </div>
      </div>

      {/* Report preview */}
      {detail && selectedCity && (
        <div className="card">
          <div className="card-header">
            <h3>{t(lang, "reports.preview", { city: selectedCity })}</h3>
            <span className="tag">PDF preview</span>
          </div>
          <div style={{
            background: "rgba(30, 42, 36, 0.04)",
            borderRadius: 12,
            padding: "16px 20px",
            fontFamily: "monospace",
            fontSize: "0.8rem",
            color: "var(--muted)",
            lineHeight: 1.6,
            border: "1px solid var(--border)",
          }}>
            <div><span style={{ color: "var(--accent-dark)" }}>city:</span> "{selectedCity}"</div>
            <div><span style={{ color: "var(--accent-dark)" }}>zone:</span> "{detail.advisory.current_zone}"</div>
            <div><span style={{ color: "var(--accent-dark)" }}>trend:</span> "{detail.trend.trend}" (slope: {detail.trend.slope.toFixed(4)})</div>
            <div><span style={{ color: "var(--accent-dark)" }}>eri:</span> {(detail.eri.eri * 100).toFixed(1)}% {detail.eri.alert ? "⚠ ALERT" : "✓"}</div>
            <div><span style={{ color: "var(--accent-dark)" }}>transitions:</span> {detail.transitions.length} detected</div>
            <div><span style={{ color: "var(--accent-dark)" }}>top_crops:</span> [{detail.advisory.ranked_crops.slice(0, 3).map((c: any) => `"${capitalizeWords(c.crop)}"`).join(", ")}]</div>
            <div><span style={{ color: "var(--accent-dark)" }}>shap_drivers:</span> {detail.shap.city_top.length} features ranked</div>
          </div>
        </div>
      )}
    </section>
  );
};

export default Reports;
