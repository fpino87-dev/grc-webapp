import { apiClient } from "../client";

export const reportingApi = {
  dashboard: (plant?: string) =>
    apiClient.get<{
      plants_active: number;
      incidents_open: number;
      controls_total: number;
      controls_compliant: number;
      controls_gap: number;
      pct_compliant: number;
    }>("/reporting/dashboard/", { params: plant ? { plant } : {} }).then(r => r.data),
  compliance: (params?: Record<string, string>) =>
    apiClient.get<{
      total: number;
      by_status: Record<string, number>;
      pct_compliant: number;
    }>("/reporting/compliance/", { params }).then(r => r.data),
};
