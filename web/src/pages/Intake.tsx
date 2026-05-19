import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useCityContext } from "../state/CityContext";
import { useFarmerProfile } from "../state/FarmerProfileContext";
import { useLanguage } from "../state/LanguageContext";
import { t } from "../i18n";

const Intake: React.FC = () => {
  const { selectedCity, setSelectedCity, cities, loading, error } = useCityContext();
  const { profile, setProfile, markSubmitted } = useFarmerProfile();
  const [local, setLocal] = useState(profile);
  const navigate = useNavigate();

  const update = (field: keyof typeof local, value: string) => {
    setLocal({ ...local, [field]: value });
  };

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    setProfile(local);
    markSubmitted();
    navigate("/dashboard");
  };

  const { lang } = useLanguage();

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <h1>Quick Crop Viability Check</h1>
          <p>Tell us your location and current crop. We'll predict if it will remain viable in the next 5 years and suggest alternatives.</p>
        </div>
      </div>

      <form className="card intake-form" onSubmit={handleSubmit}>
        {error && <p className="error">{error}</p>}
        <div className="form-grid" style={{ maxWidth: "500px" }}>
          <label>
            <div style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "8px" }}>📍 Your Location</div>
            <select
              value={selectedCity}
              onChange={(e) => setSelectedCity(e.target.value)}
              disabled={loading || cities.length === 0}
              style={{ fontSize: "1rem", padding: "10px" }}
            >
              <option value="">Select your city...</option>
              {cities.map((city) => (
                <option key={city.city} value={city.city}>
                  {city.city}
                </option>
              ))}
            </select>
          </label>

          <label style={{ marginTop: "24px" }}>
            <div style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "8px" }}>🌾 Crop You're Growing</div>
            <input
              placeholder="e.g., Rice, Wheat, Cotton, Sugarcane..."
              value={local.desiredCrop}
              onChange={(e) => update("desiredCrop", e.target.value)}
              style={{ fontSize: "1rem", padding: "10px" }}
            />
          </label>
        </div>

        <div style={{ marginTop: "32px", padding: "16px", backgroundColor: "#f0f8ff", borderRadius: "8px", color: "#555" }}>
          <p style={{ margin: 0, fontSize: "0.95rem" }}>
            ✓ We'll predict if your crop will remain viable in the next 5 years<br/>
            ✓ Suggest alternative crops better suited for your location<br/>
            ✓ Provide water management strategies
          </p>
        </div>

        <button type="submit" className="primary" disabled={loading || !selectedCity || !local.desiredCrop} style={{ marginTop: "24px", width: "100%", padding: "12px", fontSize: "1rem" }}>
          {loading ? t(lang, 'loading') : "Get My Prediction"}
        </button>
      </form>
    </section>
  );
};

export default Intake;
