import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { CityProvider } from "./state/CityContext";
import { FarmerProfileProvider } from "./state/FarmerProfileContext";
import { LanguageProvider } from "./state/LanguageContext";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <CityProvider>
        <FarmerProfileProvider>
          <LanguageProvider>
            <App />
          </LanguageProvider>
        </FarmerProfileProvider>
      </CityProvider>
    </BrowserRouter>
  </React.StrictMode>
);
