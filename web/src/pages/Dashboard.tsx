import React from "react";
import { useCityContext } from "../state/CityContext";
import { useCityDetail } from "../hooks/useCityDetail";
import { useFarmerProfile } from "../state/FarmerProfileContext";
import AdvisoryCard from "../components/AdvisoryCard";
import { capitalizeWords } from "../utils/text";

const EriGauge: React.FC<{ value: number; alert: boolean }> = ({ value, alert }) => {
  const r = 32;
  const circ = 2 * Math.PI * r;
  const offset = circ * (1 - Math.min(1, value));
  const color = alert ? "var(--risk-high)" : value > 0.5 ? "var(--risk-medium)" : "var(--risk-low)";
  return (
    <div className="eri-gauge">
      <svg viewBox="0 0 80 80">
        <circle className="track" cx="40" cy="40" r={r} />
        <circle
          className="fill"
          cx="40"
          cy="40"
          r={r}
          stroke={color}
          strokeDasharray={circ}
          strokeDashoffset={offset}
        />
      </svg>
      <div className="eri-center" style={{ color }}>
        {(value * 100).toFixed(0)}%
      </div>
    </div>
  );
};

// Helper to convert Köppen codes to farmer language
const getZoneExplanation = (zone: string): string => {
  const zoneMap: Record<string, string> = {
    "BSh": "Hot, semi-arid climate (dry but warm)",
    "BSk": "Cold, semi-arid climate (dry and cool)",
    "BWh": "Hot desert climate (very dry)",
    "BWk": "Cold desert climate (very dry and cold)",
    "Aw": "Tropical savanna (hot with distinct wet/dry seasons)",
    "Am": "Tropical monsoon (very wet during monsoon)",
    "Af": "Tropical rainforest (wet year-round)",
    "Cwa": "Humid subtropical (warm, moderate rain)",
    "Csa": "Mediterranean (hot, dry summers)",
    "Cwb": "Oceanic (cool, dry winters)",
    "Cfb": "Oceanic (cool, wet year-round)",
  };
  return zoneMap[zone] || zone;
};

const Dashboard: React.FC = () => {
  const { selectedCity, cities } = useCityContext();
  const { profile, hasSubmitted } = useFarmerProfile();
  const { detail, loading, error } = useCityDetail(selectedCity);
  const summary = cities.find((c) => c.city === selectedCity);

  if (!hasSubmitted) {
    return (
      <section className="page">
        <div className="card" style={{ textAlign: "center", padding: 48 }}>
          <div style={{ fontSize: "3rem", marginBottom: 16 }}>🌾</div>
          <h3>Provide crop and city on the home page</h3>
          <p>
            The decision dashboard is personalised to your farm profile — city and crop. Enter your current crop and location on the home page to unlock the analysis.
          </p>
          <a className="primary" href="/" style={{ marginTop: 16, display: "inline-block" }}>
            → Go to home
          </a>
        </div>
      </section>
    );
  }

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <h1>Decision Dashboard</h1>
          <p>Personalised guidance based on your farm profile and current climate risk in {selectedCity}.</p>
        </div>
      </div>

      {/* Crop Viability Assessment */}
      {detail && profile.desiredCrop && (
        <div className="card" style={{ borderLeft: "4px solid var(--primary)", paddingLeft: "20px" }}>
          <div className="card-header">
            <h3>Your Crop: {profile.desiredCrop}</h3>
          </div>
          {(() => {
            const cropMatch = detail.advisory.ranked_crops.find(
              (c: any) => c.crop.toLowerCase() === profile.desiredCrop.toLowerCase()
            );
            const rank = cropMatch ? detail.advisory.ranked_crops.indexOf(cropMatch) + 1 : null;
            const isRecommended = cropMatch && rank <= 3;

            return (
              <div style={{ display: "grid", gap: "16px" }}>
                <div>
                  <div style={{ fontSize: "0.9rem", color: "#666", marginBottom: "8px" }}>VIABILITY IN NEXT 5 YEARS</div>
                  <div style={{ fontSize: "1.4rem", fontWeight: 600, color: isRecommended ? "#22c55e" : "#ef4444" }}>
                    {isRecommended ? "✓ VIABLE" : "⚠ AT RISK"}
                  </div>
                </div>

                {isRecommended && (
                  <p style={{ margin: 0, padding: "12px 0", borderTop: "1px solid #eee", color: "#555" }}>
                    Good news! <strong>{capitalizeWords(profile.desiredCrop)}</strong> is ranked <strong>#{rank}</strong> among recommended crops for {selectedCity}.
                    It's well-suited to current climate conditions.
                  </p>
                )}

                {!isRecommended && (
                  <p style={{ margin: 0, padding: "12px 0", borderTop: "1px solid #eee", color: "#d32f2f" }}>
                    <strong>{capitalizeWords(profile.desiredCrop)}</strong> is showing viability challenges in {selectedCity} over the next 5 years.
                    Consider switching to recommended alternatives below.
                  </p>
                )}

                {detail.advisory.ranked_crops.length > 0 && (
                  <div style={{ paddingTop: "12px", borderTop: "1px solid #eee" }}>
                    <div style={{ fontSize: "0.9rem", color: "#666", marginBottom: "8px" }}>SUGGESTED ALTERNATIVES</div>
                    <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                      {detail.advisory.ranked_crops.slice(0, 3).map((crop: any, idx: number) => (
                        <span
                          key={idx}
                          style={{
                            padding: "8px 12px",
                            backgroundColor: "#f0f0f0",
                            borderRadius: "4px",
                            fontSize: "0.9rem",
                            fontWeight: 500,
                          }}
                        >
                          {capitalizeWords(crop.crop)} ({crop.score})
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })()}
        </div>
      )}

      {/* Farm profile summary */}
      <div className="card">
        <div className="card-header">
          <h3>Your Profile</h3>
          <span className="tag">{selectedCity}</span>
        </div>
        <div className="input-summary">
          {[
            { label: "Location", value: selectedCity },
            { label: "Current Crop", value: profile.desiredCrop || "—" },
          ].map((item) => (
            <div key={item.label} className="input-summary-item">
              <div className="label">{item.label}</div>
              <div className="value">{item.value}</div>
            </div>
          ))}
        </div>
      </div>

      {loading && (
        <div className="card" style={{ textAlign: "center", padding: 32 }}>
          <p style={{ marginBottom: 0 }}>Running climate analysis for {selectedCity}…</p>
        </div>
      )}
      {error && <p className="error">{error}</p>}

      {detail && (
        <>
          {/* Climate Outlook - Transitions in plain language */}
          <div className="card" style={{ borderLeft: "4px solid #ff9800", paddingLeft: "20px" }}>
            <h3>🌍 Climate Outlook for {selectedCity}</h3>
            <div style={{ fontSize: "0.95rem", lineHeight: "1.6", color: "#555" }}>
              <p style={{ margin: "0 0 12px 0" }}>
                <strong>Your region's climate type:</strong> {getZoneExplanation(detail.advisory.current_zone)}
              </p>
              <p style={{ margin: 0, padding: "12px", backgroundColor: "#fff3e0", borderRadius: "4px" }}>
                📌 Our analysis shows your region has experienced climate shifts in the past. These changes affect which crops can grow well. 
                Your water patterns and growing season may be changing, which is why some crops that worked before may not work now.
              </p>
            </div>
          </div>

          {/* 5-Year Risk Assessment */}
          <div className="card" style={{ borderLeft: "4px solid #f44336", paddingLeft: "20px" }}>
            <h3>⚠️ 5-Year Crop Viability Risk</h3>
            <div style={{ fontSize: "0.95rem", lineHeight: "1.6", color: "#555" }}>
              {detail.summary?.recent_cvle_count > 0 ? (
                <p style={{ margin: "0 0 12px 0", padding: "12px", backgroundColor: "#ffebee", borderRadius: "4px", borderLeft: "3px solid #f44336" }}>
                  <strong style={{ color: "#d32f2f" }}>Alert:</strong> There have been {detail.summary?.recent_cvle_count} years in the past when this region 
                  experienced severe stress for crops — not enough rain at planting time AND wells running very low. This pattern may repeat.
                </p>
              ) : (
                <p style={{ margin: "0 0 12px 0", padding: "12px", backgroundColor: "#e8f5e9", borderRadius: "4px", borderLeft: "3px solid #4caf50" }}>
                  <strong style={{ color: "#2e7d32" }}>Stable:</strong> Recent years show manageable conditions for most crops. Continue monitoring rainfall and well levels.
                </p>
              )}
              <p style={{ margin: 0 }}>
                ✓ Choose crops ranked in top 3 to reduce risk | 
                ✓ Use drip irrigation to save water | 
                ✓ Track your well depth month-to-month
              </p>
            </div>
          </div>

          {/* Crop recommendations */}
          <div className="section">
            <div className="section-head">
              <h2>Top crop recommendations</h2>
              <span className="tag">{detail.advisory.current_zone}</span>
            </div>
            <div className="card-grid">
              {detail.advisory.ranked_crops.slice(0, 3).map((crop, idx) => (
                <AdvisoryCard key={`${crop.crop}-${idx}`} crop={crop} rank={idx + 1} />
              ))}
            </div>
          </div>

          {/* Irrigation + Economic in 2 cols */}
          <div className="card-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))" }}>
            {/* Action Steps - Simplified */}
            <div className="card">
              <div className="card-header">
                <h3>📋 What To Do Now</h3>
              </div>
              <div style={{ display: "grid", gap: "12px", fontSize: "0.95rem" }}>
                <div style={{ padding: "10px", backgroundColor: "#f5f5f5", borderRadius: "4px" }}>
                  <strong>Water Method:</strong>
                  <p style={{ margin: "6px 0 0 0", fontSize: "0.9rem", color: "#666" }}>
                    {detail.irrigation.irrigation_method === "drip_only" 
                      ? "🚰 Use ONLY drip irrigation (saves 40% water vs flood)" 
                      : detail.irrigation.irrigation_method === "drip_or_sprinkler_with_rwh"
                      ? "💧 Use drip or sprinkler + collect rainwater"
                      : "🌧️ Sprinkler system recommended"}
                  </p>
                </div>

                <div style={{ padding: "10px", backgroundColor: "#f5f5f5", borderRadius: "4px" }}>
                  <strong>Best Planting Time:</strong>
                  <p style={{ margin: "6px 0 0 0", fontSize: "0.9rem", color: "#666" }}>
                    {detail.irrigation.optimal_sow_window}
                  </p>
                </div>

                <div style={{ padding: "10px", backgroundColor: "#f5f5f5", borderRadius: "4px" }}>
                  <strong>Avoid:</strong>
                  <p style={{ margin: "6px 0 0 0", fontSize: "0.9rem", color: "#d32f2f" }}>
                    {detail.irrigation.avoid_crops && detail.irrigation.avoid_crops.length > 0
                      ? detail.irrigation.avoid_crops.map(capitalizeWords).join(", ") + " (too water-thirsty)"
                      : "No restrictions now"}
                  </p>
                </div>

                <div style={{ padding: "10px", backgroundColor: "#e8f5e9", borderRadius: "4px" }}>
                  <strong style={{ color: "#2e7d32" }}>Priority:</strong>
                  <p style={{ margin: "6px 0 0 0", fontSize: "0.9rem", color: "#2e7d32" }}>
                    {detail.irrigation.recommended_crops && detail.irrigation.recommended_crops.length > 0
                      ? detail.irrigation.recommended_crops.slice(0, 3).map(capitalizeWords).join(", ")
                      : "Cotton, Sorghum, Groundnut"}
                  </p>
                </div>
              </div>
            </div>

            {/* Economic protection - Simplified */}
            <div className="card">
              <div className="card-header">
                <h3>💰 Protect Your Income</h3>
              </div>
              <div style={{ display: "grid", gap: "12px", fontSize: "0.95rem" }}>
                <div style={{ padding: "10px", backgroundColor: "#e3f2fd", borderRadius: "4px" }}>
                  <strong>Fair Price (MSP):</strong>
                  <p style={{ margin: "6px 0 0 0", fontSize: "1.1rem", color: "#1976d2", fontWeight: 600 }}>
                    ₹{detail.eri.msp_inr_per_quintal || "N/A"} per quintal
                  </p>
                  <p style={{ margin: "4px 0 0 0", fontSize: "0.85rem", color: "#666" }}>
                    Minimum guaranteed price from government
                  </p>
                </div>

                <div style={{ padding: "10px", backgroundColor: "#fff3e0", borderRadius: "4px" }}>
                  <strong>Danger Zone:</strong>
                  <p style={{ margin: "6px 0 0 0", fontSize: "1rem", color: "#f57c00", fontWeight: 600 }}>
                    Don't accept less than ₹{detail.eri.distress_price_threshold}
                  </p>
                  <p style={{ margin: "4px 0 0 0", fontSize: "0.85rem", color: "#666" }}>
                    Below this, middlemen are taking unfair profit. Report to APMC.
                  </p>
                </div>

                <div style={{ padding: "10px", backgroundColor: "#f3e5f5", borderRadius: "4px" }}>
                  <strong>Risk Level:</strong>
                  <p style={{ margin: "6px 0 0 0", fontSize: "0.9rem" }}>
                    {detail.eri.alert ? "⚠️ ALERT - High risk" : "✓ Stable - Low risk"}
                  </p>
                  <p style={{ margin: "4px 0 0 0", fontSize: "0.85rem", color: "#666" }}>
                    Get crop insurance (PMFBY) before planting
                  </p>
                </div>
              </div>
            </div>
          </div>

        </>
      )}
    </section>
  );
};

export default Dashboard;
