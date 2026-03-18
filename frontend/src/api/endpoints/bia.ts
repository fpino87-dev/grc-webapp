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

export const biaApi = {
  list: (params?: Record<string, string>) =>
    apiClient.get<{ results: CriticalProcess[] }>("/bia/processes/", { params }).then(r => r.data),
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
    apiClient.delete(`/bia/processes/${id}/`).then(r => r.data),
};
