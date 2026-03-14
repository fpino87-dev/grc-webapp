import { apiClient } from "../client";

export interface RiskByOwner {
  owner__id: string | null;
  owner__first_name: string;
  owner__last_name: string;
  owner__email: string;
  owner_name: string;
  owner_email: string;
  totale: number;
  rossi: number;
  gialli: number;
  verdi: number;
  processes: number;
}

export interface TaskByOwner {
  assigned_to__first_name: string;
  assigned_to__last_name: string;
  assigned_to__email: string;
  owner_name: string;
  aperti: number;
  scaduti: number;
  completati_30gg: number;
}

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
  ownerReport: (plant?: string) =>
    apiClient.get<{ risks_by_owner: RiskByOwner[]; tasks_by_owner: TaskByOwner[] }>(
      "/reporting/owner-report/",
      { params: plant ? { plant } : {} }
    ).then(r => r.data),
};
