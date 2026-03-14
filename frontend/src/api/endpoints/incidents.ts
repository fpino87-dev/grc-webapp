import { apiClient } from "../client";

export interface Incident {
  id: string;
  plant: string;
  plant_name?: string;
  title: string;
  description: string;
  detected_at: string;
  severity: "bassa" | "media" | "alta" | "critica";
  nis2_notifiable: "si" | "no" | "da_valutare";
  status: "aperto" | "in_analisi" | "chiuso";
  closed_at: string | null;
}

export const incidentsApi = {
  list: (params?: Record<string, string>) =>
    apiClient.get<{ results: Incident[]; count: number }>("/incidents/incidents/", { params }).then((r) => r.data),
  get: (id: string) => apiClient.get<Incident>(`/incidents/incidents/${id}/`).then((r) => r.data),
  create: (data: Partial<Incident>) =>
    apiClient.post<Incident>("/incidents/incidents/", data).then((r) => r.data),
  close: (id: string) =>
    apiClient.post(`/incidents/incidents/${id}/close/`).then((r) => r.data),
};
