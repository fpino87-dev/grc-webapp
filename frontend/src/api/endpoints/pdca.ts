import { apiClient } from "../client";

export interface PdcaCycle {
  id: string;
  plant: string;
  title: string;
  descrizione?: string;
  trigger_type: string;
  audit_subtype?: string;
  riferimento_finding?: string;
  scope_type: string;
  fase_corrente: string;
  act_description?: string;
  check_outcome?: string;
  motivo_archiviazione?: string;
  reopened_as?: string | null;
  closed_at?: string | null;
  created_at: string;
  updated_at?: string;
}

export const pdcaApi = {
  list: (params?: Record<string, string>) =>
    apiClient.get<{ results: PdcaCycle[] }>("/pdca/cycles/", { params }).then((r) => r.data),
  create: (data: Partial<PdcaCycle>) =>
    apiClient.post<PdcaCycle>("/pdca/cycles/", data).then((r) => r.data),
  update: (id: string, data: Partial<PdcaCycle>) =>
    apiClient.patch<PdcaCycle>(`/pdca/cycles/${id}/`, data).then((r) => r.data),
  remove: (id: string, reason: string) =>
    apiClient.delete(`/pdca/cycles/${id}/`, { data: { reason } }),
  archivia: (id: string, motivo: string) =>
    apiClient.post(`/pdca/cycles/${id}/archivia/`, { motivo }),
};
