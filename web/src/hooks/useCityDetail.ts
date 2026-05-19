import { useEffect, useMemo, useState } from "react";
import { fetchCityDetail } from "../api/client";
import type { CityDetail } from "../api/types";

const cache = new Map<string, CityDetail>();

export function useCityDetail(city: string) {
  const [detail, setDetail] = useState<CityDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    async function load() {
      if (!city) {
        setLoading(false);
        setDetail(null);
        return;
      }
      setLoading(true);
      setError(null);
      if (cache.has(city)) {
        setDetail(cache.get(city) ?? null);
        setLoading(false);
        return;
      }
      try {
        const data = await fetchCityDetail(city);
        if (!active) return;
        cache.set(city, data);
        setDetail(data);
      } catch (err) {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Failed to load city detail.");
      } finally {
        if (active) setLoading(false);
      }
    }
    load();
    return () => {
      active = false;
    };
  }, [city]);

  return useMemo(() => ({ detail, loading, error }), [detail, loading, error]);
}
