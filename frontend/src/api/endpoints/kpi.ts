import { apiClient } from "../client";

export type KpiSource = "checklist" | "api" | "manual";
export type KpiAggregation =
  | "success_rate"
  | "avg_value"
  | "last_value"
  | "count_ok"
  | "count_fail";
export type KpiDirection = "above" | "below";
export type KpiStatus = "ok" | "warning" | "critical" | "no_data";

export interface KpiDefinition {
  id: string;
  kpi_code: string;
  name: string;
  description: string;
  unit: string;
  source: KpiSource;
  checklist_template: string | null;
  checklist_template_name?: string | null;
  checklist_item_filter: string;
  aggregation: KpiAggregation;
  plant: string | null;
  plant_name?: string | null;
  threshold_warning: number | null;
  threshold_critical: number | null;
  threshold_direction: KpiDirection;
  is_active: boolean;
  notify_on_warning: boolean;
  notify_on_critical: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface KpiDefinitionListItem {
  id: string;
  kpi_code: string;
  name: string;
  unit: string;
  threshold_warning: number | null;
  threshold_critical: number | null;
  threshold_direction: KpiDirection;
  source: KpiSource;
  is_active: boolean;
  plant: string | null;
  last_status: KpiStatus;
  last_value: number | null;
}

export interface KpiSnapshot {
  id: string;
  kpi_definition: string;
  kpi_code: string;
  kpi_name: string;
  unit: string;
  plant: string | null;
  plant_name?: string;
  week_start: string;
  value: number | null;
  status: KpiStatus;
  source: KpiSource;
  measured_at: string | null;
  run_count: number;
  note: string;
  created_at: string;
}

export interface KpiTrend {
  kpi_code: string;
  name: string;
  unit: string;
  threshold_warning: number | null;
  threshold_critical: number | null;
  threshold_direction: KpiDirection;
  results: KpiSnapshot[];
}

export interface KpiSuggestion {
  kpi_code: string;
  name: string;
  description: string;
  unit: string;
  aggregation: KpiAggregation;
  threshold_direction: KpiDirection;
  threshold_warning: number | null;
  threshold_critical: number | null;
  notify_on_warning: boolean;
  notify_on_critical: boolean;
  source: KpiSource;
  category: string;
  frameworks: string[];
  rationale: string;
  checklist_hint: string;
  already_configured: boolean;
  suggested_checklist_template: { id: string; name: string } | null;
}

export interface KpiSuggestResponse {
  plant_frameworks: string[];
  suggestions: KpiSuggestion[];
}

export interface KpiImportOverride {
  threshold_warning?: number | null;
  threshold_critical?: number | null;
  checklist_template?: string | null;
}

export interface KpiImportResult {
  created: string[];
  skipped: string[];
  errors: { kpi_code: string; error: string }[];
}

const DEF = "/tasks/kpi-definitions/";
const SNAP = "/tasks/kpi-snapshots/";

export const kpiApi = {
  // Definizioni
  getKpiDefinitions: (params?: Record<string, string>) =>
    apiClient
      .get<{ results: KpiDefinitionListItem[]; count: number }>(DEF, { params })
      .then((r) => r.data),
  getKpiDefinition: (id: string) =>
    apiClient.get<KpiDefinition>(`${DEF}${id}/`).then((r) => r.data),
  createKpiDefinition: (data: Partial<KpiDefinition>) =>
    apiClient.post<KpiDefinition>(DEF, data).then((r) => r.data),
  updateKpiDefinition: (id: string, data: Partial<KpiDefinition>) =>
    apiClient.patch<KpiDefinition>(`${DEF}${id}/`, data).then((r) => r.data),
  deleteKpiDefinition: (id: string) =>
    apiClient.delete(`${DEF}${id}/`).then((r) => r.data),

  // Snapshot / trend
  getKpiSnapshots: (params?: Record<string, string>) =>
    apiClient
      .get<{ results: KpiSnapshot[]; count: number }>(SNAP, { params })
      .then((r) => r.data),
  getKpiTrend: (kpiCode: string, plantId?: string, weeks = 8) => {
    const params: Record<string, string> = { kpi_code: kpiCode, weeks: String(weeks) };
    if (plantId) params.plant = plantId;
    return apiClient.get<KpiTrend>(`${SNAP}trend/`, { params }).then((r) => r.data);
  },

  // Ingest manuale (anche per test dalla UI) + ricalcolo
  ingestKpi: (data: {
    kpi_code: string;
    plant: string;
    value: number;
    source: string;
    measured_at?: string;
    note?: string;
  }) => apiClient.post("/kpi-ingest/", data).then((r) => r.data),
  computeNow: () =>
    apiClient.post<{ detail: string }>("/kpi-compute/", {}).then((r) => r.data),

  // Consiglia KPI (catalogo standard → import)
  getKpiSuggestions: (plantId?: string, lang?: string) => {
    const params: Record<string, string> = {};
    if (plantId) params.plant = plantId;
    if (lang) params.lang = lang;
    return apiClient.get<KpiSuggestResponse>("/kpi-suggest/", { params }).then((r) => r.data);
  },
  importKpiSuggestions: (
    plantId: string | null,
    kpiCodes: string[],
    overrides: Record<string, KpiImportOverride>
  ) =>
    apiClient
      .post<KpiImportResult>("/kpi-suggest/import/", {
        plant: plantId,
        kpi_codes: kpiCodes,
        overrides,
      })
      .then((r) => r.data),
};
