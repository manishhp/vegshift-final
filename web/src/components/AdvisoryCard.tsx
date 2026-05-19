import React, { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import type { CropScore, ClimateContext } from "../api/types";
import { useLanguage } from "../state/LanguageContext";
import { t } from "../i18n";
import { capitalizeWords } from "../utils/text";

const RANK_CLASSES = ["gold", "silver", "bronze"];

const CROP_ICONS: Record<string, string> = {
  Wheat: "🌾", Rice: "🌾", Maize: "🌽", Corn: "🌽",
  Cotton: "🪴", Sugarcane: "🌿", Soybean: "🫘", Groundnut: "🥜",
  Tomato: "🍅", Onion: "🧅", Potato: "🥔", Sorghum: "🌾",
  Millet: "🌾", Bajra: "🌾", Jowar: "🌾",
};

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function cropIcon(name: string): string {
  const key = name.toLowerCase();
  for (const [k, v] of Object.entries(CROP_ICONS)) {
    if (key.includes(k.toLowerCase())) return v;
  }
  return "🌱";
}

interface BreakdownRowProps {
  label: string;
  deduction: number;
  explanation: string;
}

function BreakdownRow({ label, deduction, explanation }: BreakdownRowProps) {
  const isOk = deduction === 0;
  const color = isOk ? "var(--risk-low)" : deduction > -10 ? "var(--risk-medium)" : "var(--risk-high)";
  return (
    <div style={{ borderBottom: "1px solid var(--border)", paddingBottom: 10, marginBottom: 10 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
        <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.04em" }}>{label}</span>
        <span style={{ fontSize: "0.9rem", fontWeight: 700, color }}>
          {isOk ? "✓ 0" : `${deduction.toFixed(1)}`}
        </span>
      </div>
      <p style={{ fontSize: "0.82rem", margin: 0, color: "var(--ink)", lineHeight: 1.5 }}>{explanation}</p>
    </div>
  );
}

interface ModalProps {
  crop: CropScore;
  climateContext?: ClimateContext;
  currentZone?: string;
  onClose: () => void;
}

function BreakdownModal({ crop, climateContext, currentZone, onClose }: ModalProps) {
  const { lang } = useLanguage();
  const bd = crop.breakdown!;
  const spec = crop.crop_spec;
  const ctx = climateContext;
  const scorePct = Math.min(1, Math.max(0, crop.score / 100));
  const scoreColor = scorePct >= 0.65 ? "var(--risk-low)" : scorePct >= 0.4 ? "var(--risk-medium)" : "var(--risk-high)";

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [onClose]);

  function zoneExplain() {
    const zone = currentZone ?? "?";
    if (bd.zone === 0) return t(lang, "advisory.breakdown.zone_ok", { zone });
    return t(lang, "advisory.breakdown.zone_bad", { zone, zones: spec?.zones.join(", ") ?? "?" });
  }

  function tempExplain() {
    if (!spec || !ctx) return "";
    if (bd.temp === 0) return t(lang, "advisory.breakdown.temp_ok", { tmax: String(ctx.t_max), cropmax: String(spec.max_temp) });
    return t(lang, "advisory.breakdown.temp_bad", { tmax: String(ctx.t_max), cropmax: String(spec.max_temp) });
  }

  function waterExplain() {
    if (!spec || !ctx) return "";
    if (bd.water === 0) return t(lang, "advisory.breakdown.water_ok", { rain: String(ctx.rainfall_mm), req: String(spec.water_req) });
    return t(lang, "advisory.breakdown.water_bad", { rain: String(ctx.rainfall_mm), req: String(spec.water_req) });
  }

  function gwExplain() {
    if (!ctx) return "";
    if (bd.gw === 0) return t(lang, "advisory.breakdown.gw_ok");
    return t(lang, "advisory.breakdown.gw_bad", { depth: String(ctx.gw_depth_mbgl) });
  }

  function trajExplain() {
    if (bd.trajectory === 0) return t(lang, "advisory.breakdown.traj_ok");
    return t(lang, "advisory.breakdown.traj_bad");
  }

  const totalDeduction = bd.zone + bd.temp + bd.water + bd.gw + bd.trajectory;

  return createPortal(
    <div
      style={{
        position: "fixed", inset: 0, zIndex: 1000,
        background: "rgba(0,0,0,0.45)",
        display: "flex", alignItems: "center", justifyContent: "center",
        padding: "16px",
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: "#ffffff",
          borderRadius: 14,
          border: "1px solid var(--border)",
          width: "100%",
          maxWidth: 480,
          maxHeight: "85vh",
          overflowY: "auto",
          boxShadow: "0 20px 60px rgba(0,0,0,0.25)",
          padding: "24px",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: "1.5rem" }}>{cropIcon(crop.crop)}</span>
            <div>
              <h3 style={{ margin: 0, fontSize: "1.1rem", fontWeight: 700 }}>{capitalize(crop.crop)}</h3>
              <div style={{ display: "flex", gap: 6, marginTop: 4 }}>
                <span className="tag" style={{ fontSize: "0.68rem", padding: "2px 7px", textTransform: "capitalize" }}>{crop.season}</span>
                <span className={`tag ${crop.zone_match ? "risk-low" : "risk-high"}`} style={{ fontSize: "0.68rem", padding: "2px 7px" }}>
                  {crop.zone_match ? t(lang, "advisory.zone_match") : t(lang, "advisory.zone_mismatch")}
                </span>
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "none", border: "none", cursor: "pointer",
              fontSize: "1.2rem", color: "var(--muted)", lineHeight: 1,
              padding: "4px 8px", borderRadius: 6,
            }}
          >✕</button>
        </div>

        {/* Score summary */}
        <div style={{
          background: "rgba(30,42,36,0.06)", borderRadius: 10,
          padding: "12px 16px", marginBottom: 16,
          display: "flex", alignItems: "center", justifyContent: "space-between",
        }}>
          <span style={{ fontSize: "0.85rem", color: "var(--muted)", fontWeight: 600 }}>
            {t(lang, "advisory.viability")}
          </span>
          <strong style={{ fontSize: "1.6rem", color: scoreColor, fontWeight: 800 }}>
            {scorePct >= 0.65 ? t(lang, "viability.high") : scorePct >= 0.4 ? t(lang, "viability.medium") : t(lang, "viability.low")}
          </strong>
        </div>

        {/* Climate context strip */}
        {ctx && (
          <div style={{
            display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16,
            padding: "8px 12px", background: "rgba(30,42,36,0.04)",
            borderRadius: 8, fontSize: "0.78rem", color: "var(--muted)",
          }}>
            <span>🌡 {ctx.t_max}°C max temp</span>
            <span>🌧 {ctx.rainfall_mm}mm/yr rainfall</span>
            <span>💧 {ctx.gw_depth_mbgl}m groundwater</span>
          </div>
        )}

        {/* Title */}
        <div style={{ fontSize: "0.78rem", fontWeight: 700, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 12 }}>
          {t(lang, "advisory.breakdown.title")}
        </div>

        {/* Breakdown rows */}
        <BreakdownRow label={t(lang, "advisory.breakdown.zone")} deduction={bd.zone} explanation={zoneExplain()} />
        <BreakdownRow label={t(lang, "advisory.breakdown.temp")} deduction={bd.temp} explanation={tempExplain()} />
        <BreakdownRow label={t(lang, "advisory.breakdown.water")} deduction={bd.water} explanation={waterExplain()} />
        <BreakdownRow label={t(lang, "advisory.breakdown.gw")} deduction={bd.gw} explanation={gwExplain()} />
        <BreakdownRow label={t(lang, "advisory.breakdown.trajectory")} deduction={bd.trajectory} explanation={trajExplain()} />

        {/* Total */}
        <div style={{
          display: "flex", justifyContent: "space-between", alignItems: "center",
          paddingTop: 10, marginTop: 2,
          borderTop: "2px solid var(--border)",
        }}>
          <span style={{ fontSize: "0.82rem", color: "var(--muted)", fontWeight: 600 }}>Total deductions</span>
          <strong style={{ fontSize: "1rem", color: scoreColor }}>
            {totalDeduction.toFixed(1)} pts → score {crop.score.toFixed(0)}
          </strong>
        </div>
      </div>
    </div>,
    document.body
  );
}

interface AdvisoryCardProps {
  crop: CropScore;
  rank: number;
  climateContext?: ClimateContext;
  currentZone?: string;
}

const AdvisoryCard: React.FC<AdvisoryCardProps> = ({ crop, rank, climateContext, currentZone }) => {
  const [modalOpen, setModalOpen] = useState(false);
  const rankClass = rank <= 3 ? RANK_CLASSES[rank - 1] : "";
  const scorePct = Math.min(1, Math.max(0, crop.score / 100));
  const scoreColor = scorePct >= 0.65 ? "var(--risk-low)" : scorePct >= 0.4 ? "var(--risk-medium)" : "var(--risk-high)";
  const { lang } = useLanguage();
  const hasBreakdown = !!crop.breakdown;

  return (
    <>
      <div
        className={`card advisory-card ${crop.zone_match ? "zone-match" : "zone-mismatch"}`}
        style={{ cursor: hasBreakdown ? "pointer" : "default" }}
        onClick={() => hasBreakdown && setModalOpen(true)}
        role={hasBreakdown ? "button" : undefined}
        tabIndex={hasBreakdown ? 0 : undefined}
        onKeyDown={(e) => { if (hasBreakdown && (e.key === "Enter" || e.key === " ")) setModalOpen(true); }}
      >
        <div className="advisory-head">
          <div className={`rank-badge ${rankClass}`}>#{rank}</div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
              <span style={{ fontSize: "1.1rem" }}>{cropIcon(crop.crop)}</span>
              <h4 style={{ margin: 0, fontSize: "0.98rem", fontWeight: 700, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                {capitalize(crop.crop)}
              </h4>
            </div>
            <div style={{ display: "flex", gap: 5, flexWrap: "wrap", marginTop: 4 }}>
              <span className="tag" style={{ fontSize: "0.68rem", padding: "2px 7px", textTransform: "capitalize" }}>{crop.season}</span>
              <span className={`tag ${crop.zone_match ? "risk-low" : "risk-high"}`} style={{ fontSize: "0.68rem", padding: "2px 7px" }}>
                {crop.zone_match ? t(lang, "advisory.zone_match") : t(lang, "advisory.zone_mismatch")}
              </span>
            </div>
          </div>
        </div>

        <div className="score-bar-row">
          <div className="score-bar-label">
            <span>{t(lang, "advisory.viability")}</span>
            <strong style={{ color: scoreColor }}>
              {scorePct >= 0.65 ? t(lang, "viability.high") : scorePct >= 0.4 ? t(lang, "viability.medium") : t(lang, "viability.low")}
            </strong>
          </div>
          <div className="score-bar-track">
            <div
              className="score-bar-fill"
              style={{ "--bar-scale": scorePct, "--delay": `${rank * 0.08}s` } as React.CSSProperties}
            />
          </div>
        </div>

        {hasBreakdown && (
          <div style={{ fontSize: "0.72rem", color: "var(--accent)", marginTop: 6, fontWeight: 500 }}>
            {t(lang, "advisory.why")} →
          </div>
        )}
      </div>

      {modalOpen && crop.breakdown && (
        <BreakdownModal
          crop={crop}
          climateContext={climateContext}
          currentZone={currentZone}
          onClose={() => setModalOpen(false)}
        />
      )}
    </>
  );
};

export default AdvisoryCard;
