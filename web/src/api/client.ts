import type {
  AblationResults,
  CityDetail,
  CoachRequest,
  CoachResponse,
  MetaInfo,
  MetricsTable,
  ShapCrossModel,
  StatsTests,
  SummaryResponse,
  UncertaintyMetrics,
  ZoneBreakdown,
} from "./types";

const DEFAULT_BASE = "http://127.0.0.1:8000";
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? DEFAULT_BASE;

async function fetchWithTimeout(url: string, timeoutMs = 5000, init?: RequestInit): Promise<Response> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } finally {
    window.clearTimeout(timer);
  }
}

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetchWithTimeout(`${BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(`API error ${response.status}: ${response.statusText}`);
  }
  return (await response.json()) as T;
}

async function postJson<T>(path: string, body: unknown, timeoutMs = 12000): Promise<T> {
  const response = await fetchWithTimeout(`${BASE_URL}${path}`, timeoutMs, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`API error ${response.status}: ${response.statusText}`);
  }
  return (await response.json()) as T;
}

export async function fetchSummary(): Promise<SummaryResponse> {
  const [summary, meta] = await Promise.all([
    fetchJson<SummaryResponse["summary"]>("/summary"),
    fetchJson<MetaInfo>("/meta"),
  ]);
  return { summary, meta };
}

export async function fetchCityDetail(city: string): Promise<CityDetail> {
  return fetchJson<CityDetail>(`/city/${encodeURIComponent(city)}`);
}

export async function fetchCoachPlan(payload: CoachRequest): Promise<CoachResponse> {
  return postJson<CoachResponse>("/coach", payload, 12000);
}

export async function fetchComparativeMetrics(): Promise<MetricsTable> {
  return fetchJson<MetricsTable>("/comparative/metrics");
}

export async function fetchStatsTests(): Promise<StatsTests> {
  return fetchJson<StatsTests>("/comparative/stats");
}

export async function fetchZoneBreakdown(): Promise<ZoneBreakdown> {
  return fetchJson<ZoneBreakdown>("/comparative/zones");
}

export async function fetchAblation(): Promise<AblationResults> {
  return fetchJson<AblationResults>("/comparative/ablation");
}

export async function fetchUncertainty(): Promise<UncertaintyMetrics> {
  return fetchJson<UncertaintyMetrics>("/comparative/uncertainty");
}

export async function fetchShapCrossModel(): Promise<ShapCrossModel> {
  return fetchJson<ShapCrossModel>("/comparative/shap");
}
