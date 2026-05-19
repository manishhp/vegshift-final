import React from "react";
import { useCityContext } from "../state/CityContext";
import { useLanguage } from "../state/LanguageContext";
import { t } from "../i18n";

const CitySelector: React.FC = () => {
  const { cities, selectedCity, setSelectedCity } = useCityContext();
  const { lang } = useLanguage();

  return (
    <label className="city-selector">
      <span>{t(lang, "nav.city")}</span>
      <select
        value={selectedCity}
        onChange={(event) => setSelectedCity(event.target.value)}
      >
        {cities.map((city) => (
          <option key={city.city} value={city.city}>
            {city.city}
          </option>
        ))}
      </select>
    </label>
  );
};

export default CitySelector;
