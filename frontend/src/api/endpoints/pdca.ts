import { apiClient } from "../client";

export interface PdcaCycle {
  id: string;
  plant: string;
  title: string;
  trigger_type: string;
  scope_type: string;
  fase_corrente: string;
  act_description?: string;
  check_outcome?: string;
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
};
