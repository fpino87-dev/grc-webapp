import { apiClient } from "../client";

export interface BcpPlan {
  id: string; plant: string; title: string; version: string;
  status: "bozza"|"approvato"|"archiviato";
  rto_hours: number | null; rpo_hours: number | null;
  last_test_date: string | null; next_test_date: string | null;
  owner: string | null;
  critical_process?: string | null;
  critical_processes?: string[];
}

export interface BcpTestObjective {
  text: string;
  met: boolean;
}

export interface BcpTest {
  id: string;
  plan: string;
  test_date: string;
  result: "superato" | "parziale" | "fallito";
  test_type: "tabletop" | "drill" | "full_interruption" | "parallel";
  objectives: BcpTestObjective[];
  rto_achieved_hours: number | null;
  rpo_achieved_hours: number | null;
  participants_count: number;
  objectives_met_pct: number | null;
  notes: string;
}

export const bcpApi = {
  list: (params?: Record<string, string>) =>
    apiClient.get<{ results: BcpPlan[] }>("/bcp/plans/", { params }).then(r => r.data),
  approve: (id: string) =>
    apiClient.post(`/bcp/plans/${id}/approve/`).then(r => r.data),
  create: (data: Partial<BcpPlan>) =>
    apiClient.post<BcpPlan>("/bcp/plans/", data).then(r => r.data),
  update: (id: string, data: Partial<BcpPlan>) =>
    apiClient.patch<BcpPlan>(`/bcp/plans/${id}/`, data).then(r => r.data),
  tests: (planId: string) =>
    apiClient.get<{ results: BcpTest[] }>("/bcp/tests/", { params: { plan: planId } }).then(r => r.data.results),
  recordTest: (data: Record<string, unknown>) =>
    apiClient.post<{ test: BcpTest; warnings: string[] }>("/bcp/tests/", data).then(r => r.data),
  delete: (id: string) =>
    apiClient.delete(`/bcp/plans/${id}/`).then(() => undefined),
};
