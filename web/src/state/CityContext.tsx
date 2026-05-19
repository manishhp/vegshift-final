import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { fetchSummary } from "../api/client";
import type { CitySummary, MetaInfo } from "../api/types";

interface CityState {
  cities: CitySummary[];
  selectedCity: string;
  setSelectedCity: (city: string) => void;
  loading: boolean;
  error: string | null;
  meta: MetaInfo | null;
}

const CityContext = createContext<CityState | undefined>(undefined);

export const CityProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [cities, setCities] = useState<CitySummary[]>([]);
  const [selectedCity, setSelectedCity] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [meta, setMeta] = useState<MetaInfo | null>(null);

  useEffect(() => {
    let active = true;
    async function load() {
      setLoading(true);
      try {
        const response = await fetchSummary();
        if (!active) return;
        setCities(response.summary);
        setMeta(response.meta ?? null);
        if (response.summary.length === 0) {
          setError("No city data returned. Rebuild the frontend payload and restart the API.");
          setSelectedCity("");
        } else {
          setSelectedCity(response.summary[0].city);
        }
      } catch (err) {
        if (!active) return;
        const message = err instanceof Error ? err.message : "Failed to load summary.";
        setError(`${message} Make sure the API is running at http://127.0.0.1:8000.`);
      } finally {
        if (active) setLoading(false);
      }
    }
    load();
    return () => {
      active = false;
    };
  }, []);

  const value = useMemo(
    () => ({
      cities,
      selectedCity,
      setSelectedCity,
      loading,
      error,
      meta,
    }),
    [cities, selectedCity, loading, error, meta]
  );

  return <CityContext.Provider value={value}>{children}</CityContext.Provider>;
};

export function useCityContext() {
  const ctx = useContext(CityContext);
  if (!ctx) {
    throw new Error("useCityContext must be used within CityProvider");
  }
  return ctx;
}
