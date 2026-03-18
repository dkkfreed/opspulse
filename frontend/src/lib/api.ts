const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchAPI<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(`${BASE}${path}`);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, v);
    });
  }
  const res = await fetch(url.toString(), { next: { revalidate: 60 } });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `API error ${res.status}`);
  }
  return res.json();
}

// --- Types ---
export interface WorkforceSummary {
  period_start: string; period_end: string;
  total_employees: number;
  total_scheduled_hours: number; total_actual_hours: number;
  avg_utilization_pct: number; total_overtime_hours: number;
  total_absences: number; absence_rate_pct: number;
  avg_demand: number; avg_capacity: number; demand_coverage_pct: number;
}

export interface DepartmentRow {
  department_code: string; department_name: string;
  headcount: number; scheduled_hours: number; actual_hours: number;
  utilization_pct: number; overtime_hours: number; absence_count: number;
  demand_units: number; capacity_units: number; demand_coverage_pct: number;
  staffing_status: string;
}

export interface HeatmapRow {
  date: string; department_code: string; department_name: string;
  utilization_pct: number; headcount: number; absences: number;
}

export interface TicketSummary {
  period_start: string; period_end: string;
  total: number; open: number; in_progress: number; resolved: number; closed: number;
  sla_breach_count: number; sla_breach_rate_pct: number;
  avg_resolution_hours: number; critical_open: number; escalated_count: number;
}

export interface TicketTrend {
  date: string; created_count: number; resolved_count: number;
  net_change: number; cumulative_open: number; avg_sentiment: number | null;
}

export interface SLARow {
  priority: string; sla_target_hours: number; total: number;
  breached: number; breach_rate_pct: number;
  avg_resolution_hours: number; p95_resolution_hours: number;
}

export interface CategoryRow {
  category: string; count: number; pct_of_total: number;
  avg_resolution_hours: number; breach_rate_pct: number;
}

export interface ForecastPoint {
  date: string; predicted: number;
  lower_bound: number; upper_bound: number; is_forecast: boolean;
}

export interface ForecastResult {
  metric: string; department_code: string | null;
  horizon_days: number; model_type: string;
  mae: number | null; rmse: number | null;
  confidence_interval: number;
  points: ForecastPoint[];
}

export interface AnomalyAlert {
  date: string; metric: string; department_code: string | null;
  observed_value: number; expected_value: number; z_score: number;
  severity: string; likely_cause: string | null;
  correlated_fields: Record<string, unknown> | null;
}

export interface NarrativeInsight {
  generated_at: string; period: string; role_level: string;
  headline: string; summary: string;
  key_findings: string[]; alerts: string[]; recommendations: string[];
}

export interface MarketSignal {
  signal_date: string; source: string; category: string;
  subcategory: string | null; region: string | null;
  industry: string | null; value: number; change_pct: number; notes: string | null;
}

export interface StaffingGap {
  date: string; department_code: string; department_name: string;
  demand: number; capacity: number; gap: number; gap_pct: number; severity: string;
}

// --- API calls ---
export const api = {
  workforce: {
    summary: (params?: Record<string,string>) =>
      fetchAPI<WorkforceSummary>("/api/v1/workforce/summary", params),
    byDepartment: (params?: Record<string,string>) =>
      fetchAPI<DepartmentRow[]>("/api/v1/workforce/by-department", params),
    heatmap: (params?: Record<string,string>) =>
      fetchAPI<HeatmapRow[]>("/api/v1/workforce/utilization-heatmap", params),
    gaps: (params?: Record<string,string>) =>
      fetchAPI<StaffingGap[]>("/api/v1/workforce/staffing-gaps", params),
  },
  tickets: {
    summary: (params?: Record<string,string>) =>
      fetchAPI<TicketSummary>("/api/v1/tickets/summary", params),
    trends: (params?: Record<string,string>) =>
      fetchAPI<TicketTrend[]>("/api/v1/tickets/trends", params),
    slaReport: (params?: Record<string,string>) =>
      fetchAPI<SLARow[]>("/api/v1/tickets/sla-report", params),
    byCategory: (params?: Record<string,string>) =>
      fetchAPI<CategoryRow[]>("/api/v1/tickets/by-category", params),
  },
  analytics: {
    forecast: (params?: Record<string,string>) =>
      fetchAPI<ForecastResult>("/api/v1/analytics/forecast", params),
    anomalies: (params?: Record<string,string>) =>
      fetchAPI<AnomalyAlert[]>("/api/v1/analytics/anomalies", params),
    narrative: (params?: Record<string,string>) =>
      fetchAPI<NarrativeInsight>("/api/v1/analytics/narrative", params),
    marketSignals: (params?: Record<string,string>) =>
      fetchAPI<MarketSignal[]>("/api/v1/analytics/market-signals", params),
  },
};
