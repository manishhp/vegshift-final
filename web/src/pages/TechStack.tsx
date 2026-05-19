import React from "react";

const TechStack: React.FC = () => {
  return (
    <section className="page">
      <div className="page-header">
        <div>
          <h1>Technology stack</h1>
          <p>
            VegShift is built as a data-driven system with a modern frontend and machine learning backend.
          </p>
        </div>
      </div>

      <div className="card">
        <h2>Technology stack</h2>
        <div style={{ display: "grid", gap: "16px", lineHeight: 1.8 }}>
          <p>
            VegShift is built as a data-driven analysis system with a modern frontend and machine learning backend.
          </p>
          <div>
            <strong>Data and modeling</strong>
            <ul style={{ paddingLeft: "20px" }}>
              <li>pandas / numpy for data preprocessing</li>
              <li>scikit-learn, XGBoost, LightGBM, and PyTorch for modeling</li>
              <li>Temporal Fusion Transformer for time-series risk prediction</li>
              <li>SHAP explainability for feature insights</li>
            </ul>
          </div>
          <div>
            <strong>Infrastructure and frontend</strong>
            <ul style={{ paddingLeft: "20px" }}>
              <li>FastAPI backend for data services</li>
              <li>React + TypeScript + Vite for the user interface</li>
              <li>Plotly / Dash visualization components for interactive dashboards</li>
              <li>GeoTIFF processing with rasterio for crop suitability extraction</li>
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
};

export default TechStack;
