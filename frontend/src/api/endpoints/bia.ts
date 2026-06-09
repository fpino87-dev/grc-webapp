import { apiClient } from "../client";

export interface CriticalProcess {
  id: string; plant: string; name: string;
  status: "bozza" | "validato" | "approvato";
  criticality: number; owner: string | null;
  downtime_cost_hour: string | null;
  danno_reputazionale: number; danno_normativo: number; danno_operativo: number;
  validated_at: string | null; approved_at: string | null;
  mtpd_hours: number | null;
  mbco_pct: number | null;
  rto_target_hours: number | null;
  rpo_target_hours: number | null;
  bia_targets_complete: boolean;
  rto_bcp_status: "ok" | "warning" | "critical" | "unknown";
}

export interface CriticalProcessSnapshot {
  process_id: string;
  bia: Record<string, unknown>;
  risks: Array<Record<string, unknown>>;
  bcp_plans: Array<Record<string, unknown>>;
  summary: {
    rto_bcp_status: string;
    has_bcp_plan: boolean;
    has_high_risks_without_plan: boolean;
  };
}

export interface ResilienceGapItem {
  process_id: string;
  process_name: string;
  plant: string | null;
  criticality: number | null;
  rto_target_hours: number | null;
  gap: "no_bcp_plan" | "bcp_insufficient" | "bcp_marginal";
  bcp_status: string;
  risk_level: "medio" | "alto" | "critico";
}

export interface ResilienceGapRegister {
  items: ResilienceGapItem[];
  count: number;
  by_level: Record<string, number>;
  attention: number;
}

export interface TreatmentOption {
  id: string;
  process: string;
  process_name: string;
  title: string;
  cost_implementation: string;
  cost_annual: string;
  ale_reduction_pct: number;
  created_at: string;
  updated_at: string;
}

export const treatmentOptionsApi = {
  listByProcess: (processId: string) =>
    apiClient.get<{ results: TreatmentOption[] }>("/bia/treatment-options/", {
      params: { process: processId },
    }).then(r => r.data.results),
  create: (data: Partial<TreatmentOption>) =>
    apiClient.post<TreatmentOption>("/bia/treatment-options/", data).then(r => r.data),
  update: (id: string, data: Partial<TreatmentOption>) =>
    apiClient.patch<TreatmentOption>(`/bia/treatment-options/${id}/`, data).then(r => r.data),
  delete: (id: string) =>
    apiClient.delete(`/bia/treatment-options/${id}/`).then(() => undefined),
};

export const biaApi = {
  list: (params?: Record<string, string>) =>
    apiClient.get<{ results: CriticalProcess[] }>("/bia/processes/", { params }).then(r => r.data),
  resilienceGaps: (plantId?: string) =>
    apiClient.get<ResilienceGapRegister>("/bia/processes/resilience-gaps/", {
      params: plantId ? { plant: plantId } : undefined,
    }).then(r => r.data),
  approve: (id: string) =>
    apiClient.post(`/bia/processes/${id}/approve/`).then(r => r.data),
  validate: (id: string) =>
    apiClient.post(`/bia/processes/${id}/validate/`).then(r => r.data),
  create: (data: Partial<CriticalProcess>) =>
    apiClient.post<CriticalProcess>("/bia/processes/", data).then(r => r.data),
  update: (id: string, data: Partial<CriticalProcess>) =>
    apiClient.patch<CriticalProcess>(`/bia/processes/${id}/`, data).then(r => r.data),
  snapshot: (id: string) =>
    apiClient.get<CriticalProcessSnapshot>(`/bia/processes/${id}/snapshot/`).then(r => r.data),
  delete: (id: string) =>
    apiClient.delete(`/bia/processes/${id}/`).then(() => undefined),
  deleteWithCascade: (id: string) =>
    apiClient.delete(`/bia/processes/${id}/`, { params: { cascade: "true" } }).then(() => undefined),
};
