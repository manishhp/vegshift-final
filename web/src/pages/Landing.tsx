import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useCityContext } from "../state/CityContext";
import { useFarmerProfile } from "../state/FarmerProfileContext";
import RiskMeter from "../components/RiskMeter";
import { useLanguage } from "../state/LanguageContext";
import { t } from "../i18n";
import { capitalizeWords } from "../utils/text";

const STATS = [
  { number: "10", labelKey: "stats.cities" },
  { number: "25", labelKey: "stats.years" },
  { number: "14", labelKey: "stats.crops" },
];

const ZONE_LABELS: Record<string, string> = {
  Af: 'Tropical rainforest (Af)',
  Am: 'Tropical monsoon (Am)',
  Aw: 'Tropical savanna (Aw)',
  Csa: 'Hot-summer Mediterranean (Csa)',
  Csb: 'Warm-summer Mediterranean (Csb)',
  Cwa: 'Humid subtropical, dry winter (Cwa)',
  Cwb: 'Subtropical highland, monsoon (Cwb)',
  Cfa: 'Humid subtropical (Cfa)',
  Cfb: 'Oceanic (Cfb)',
  BWh: 'Hot desert (BWh)',
  BWk: 'Cold desert (BWk)',
  BSh: 'Hot semi-arid (BSh)',
  BSk: 'Cold semi-arid (BSk)',
};

const getZoneLabel = (zone?: string) => {
  if (!zone) return 'Zone';
  return ZONE_LABELS[zone] || zone;
};

const PIPELINE_STEPS = [
  {
    icon: "🛰️",
    color: "blue",
    stepKey: "pipeline.step1.step",
    titleKey: "pipeline.step1.title",
    descKey: "pipeline.step1.desc",
  },
  {
    icon: "🧠",
    color: "purple",
    stepKey: "pipeline.step2.step",
    titleKey: "pipeline.step2.title",
    descKey: "pipeline.step2.desc",
  },
  {
    icon: "💧",
    color: "amber",
    stepKey: "pipeline.step3.step",
    titleKey: "pipeline.step3.title",
    descKey: "pipeline.step3.desc",
  },
  {
    icon: "🌾",
    color: "green",
    stepKey: "pipeline.step4.step",
    titleKey: "pipeline.step4.title",
    descKey: "pipeline.step4.desc",
  },
  {
    icon: "📊",
    color: "red",
    stepKey: "pipeline.step5.step",
    titleKey: "pipeline.step5.title",
    descKey: "pipeline.step5.desc",
  },
];

const Landing: React.FC = () => {
  const { selectedCity, setSelectedCity, cities, loading, error } = useCityContext();
  const { profile, setProfile, markSubmitted } = useFarmerProfile();
  const { lang } = useLanguage();
  const navigate = useNavigate();
  const [localCrop, setLocalCrop] = useState(profile.desiredCrop || "");

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!localCrop || !selectedCity) return;
    setProfile({ desiredCrop: capitalizeWords(localCrop) });
    markSubmitted();
    navigate("/dashboard");
  };

  return (
    <section className="page">
      {/* ── Hero ── */}
      <div className="hero">
        <div className="hero-eyebrow">{t(lang, "landing.eyebrow")}</div>
        <h1>{t(lang, 'landing.title')}</h1>
        <p>{t(lang, 'landing.desc')}</p>
        <form className="hero-form" onSubmit={handleSubmit}>
          <div className="hero-form-row">
            <label htmlFor="crop-input">What crop are you growing currently?</label>
            <input
              id="crop-input"
              type="text"
              placeholder="e.g. Wheat, Rice, Cotton"
              value={localCrop}
              onChange={(e) => setLocalCrop(e.target.value)}
            />
          </div>
          <div className="hero-form-row">
            <label htmlFor="city-select">Where is your farm located?</label>
            <select
              id="city-select"
              value={selectedCity}
              onChange={(e) => setSelectedCity(e.target.value)}
              disabled={loading || cities.length === 0}
            >
              <option value="">Select your city...</option>
              {cities.map((city) => (
                <option key={city.city} value={city.city}>
                  {city.city}
                </option>
              ))}
            </select>
          </div>
          <button type="submit" className="primary" disabled={!localCrop || !selectedCity || loading}>
            Go to decision dashboard
          </button>
          {error && <p className="error" style={{ marginTop: 8 }}>{error}</p>}
        </form>
      </div>

      {/* ── City grid ── */}
      <div className="section">
        <div className="section-head">
          <h2>{t(lang, "landing.cities_covered")}</h2>
          <span className="tag">2000 – 2024</span>
        </div>
        <div className="city-grid">
          {cities.map((city, i) => (
            <div
              key={city.city}
              className="card city-preview"
              style={{ "--delay": `${i * 0.04}s` } as React.CSSProperties}
              onClick={() => navigate("/city")}
              title={t(lang, "landing.view_city", { city: city.city })}
            >
              <div className="card-header">
                <h3 style={{ margin: 0, fontSize: "1rem" }}>{city.city}</h3>
              </div>
              <p style={{ fontSize: "0.78rem", marginTop: 8, marginBottom: 4 }}>
                Current climate is becoming hotter and drier.
              </p>
              <p style={{ fontSize: "0.78rem", margin: "0 0 4px" }}>
                Suitable crops for future:
              </p>
              <ul style={{ fontSize: "0.78rem", margin: "0 0 8px 16px", paddingLeft: 16 }}>
                {city.top_crops.slice(0, 2).map((c) => (
                  <li key={c.crop}>{capitalizeWords(c.crop)}</li>
                ))}
              </ul>
              <p style={{ fontSize: "0.78rem", margin: 0 }}>
                Water stress: Moderate
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Landing;
