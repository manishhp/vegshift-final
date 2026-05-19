import React from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Landing from "./pages/Landing";
import Dashboard from "./pages/Dashboard";
import TechStack from "./pages/TechStack";

import CropAdvisor from "./pages/CropAdvisor";
import WaterIrrigation from "./pages/WaterIrrigation";
import EconomicProtection from "./pages/EconomicProtection";
import Explainability from "./pages/Explainability";
import ModelComparison from "./pages/ModelComparison";
import Reports from "./pages/Reports";

const App: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Landing />} />
        <Route path="dashboard" element={<Dashboard />} />

        <Route path="crops" element={<CropAdvisor />} />
        <Route path="water" element={<WaterIrrigation />} />
        <Route path="economic" element={<EconomicProtection />} />
        <Route path="explain" element={<Explainability />} />
        <Route path="compare" element={<ModelComparison />} />
        <Route path="techstack" element={<TechStack />} />
        <Route path="reports" element={<Reports />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
};

export default App;
