import { apiClient } from "../client";

export interface BcpPlan {
  id: string; plant: string; title: string; version: string;
  status: "bozza"|"approvato"|"archiviato";
  rto_hours: number | null; rpo_hours: number | null;
  last_test_date: string | null; next_test_date: string | null;
  owner: string | null;
}

export const bcpApi = {
  list: (params?: Record<string, string>) =>
    apiClient.get<{ results: BcpPlan[] }>("/bcp/plans/", { params }).then(r => r.data),
  approve: (id: string) =>
    apiClient.post(`/bcp/plans/${id}/approve/`).then(r => r.data),
  create: (data: Partial<BcpPlan>) =>
    apiClient.post<BcpPlan>("/bcp/plans/", data).then(r => r.data),
};
