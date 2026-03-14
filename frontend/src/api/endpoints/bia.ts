import { apiClient } from "../client";

export interface CriticalProcess {
  id: string; plant: string; name: string;
  status: "bozza" | "validato" | "approvato";
  criticality: number; owner: string | null;
  downtime_cost_hour: string | null;
  danno_reputazionale: number; danno_normativo: number; danno_operativo: number;
  validated_at: string | null; approved_at: string | null;
}

export const biaApi = {
  list: (params?: Record<string, string>) =>
    apiClient.get<{ results: CriticalProcess[] }>("/bia/processes/", { params }).then(r => r.data),
  approve: (id: string) =>
    apiClient.post(`/bia/processes/${id}/approve/`).then(r => r.data),
  create: (data: Partial<CriticalProcess>) =>
    apiClient.post<CriticalProcess>("/bia/processes/", data).then(r => r.data),
};
