import { apiClient } from "../client";
import { fetchAllPages } from "../pagination";

export interface PdcaPhaseEvidence {
  id: string;
  title: string;
  evidence_type?: string;
  file_url?: string | null;
}

export interface PdcaPhase {
  id: string;
  phase: "plan" | "do" | "check" | "act";
  notes?: string;
  evidence?: PdcaPhaseEvidence | null;
  outcome?: string;
  outcome_display?: string;
  completed_at?: string | null;
  completed_by_username?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface PdcaCycle {
  id: string;
  // null = ciclo di organizzazione (vale per tutti i siti)
  plant: string | null;
  plant_name?: string | null;
  plant_code?: string | null;
  // false per i cicli di organizzazione visti da chi non ha scope org
  can_manage?: boolean;
  // Finding di audit collegati (collegamento univoco PDCA ↔ finding ↔ audit)
  findings?: PdcaLinkedFinding[];
  title: string;
  descrizione?: string;
  trigger_type: string;
  audit_subtype?: string;
  riferimento_finding?: string;
  // Responsabile dell'azione (testo libero, anche non utente del portale) e data prevista
  action_owner?: string;
  target_date?: string | null;
  is_overdue?: boolean;
  scope_type: string;
  fase_corrente: string;
  act_description?: string;
  check_outcome?: string;
  motivo_archiviazione?: string;
  reopened_as?: string | null;
  closed_at?: string | null;
  phases?: PdcaPhase[];
  created_at: string;
  updated_at?: string;
}

export interface PdcaLinkedFinding {
  id: string;
  title: string;
  finding_type: "major_nc" | "minor_nc" | "observation" | "opportunity";
  status: string;
  audit_prep: string;
  audit_title: string;
  plant_code: string;
  // Rilievo comune di un audit multi-sito (stesso valore sui finding dei siti)
  common_key: string | null;
  group_title: string | null;
  audit_type: "interno" | "seconda_parte" | "terza_parte";
  requesting_party: string;
}

export const pdcaApi = {
  list: (params?: Record<string, string>) =>
    fetchAllPages<PdcaCycle>("/pdca/cycles/", params).then((results) => ({ results, count: results.length })),
  create: (data: Partial<PdcaCycle> & { finding?: string }) =>
    apiClient.post<PdcaCycle>("/pdca/cycles/", data).then((r) => r.data),
  update: (id: string, data: Partial<PdcaCycle>) =>
    apiClient.patch<PdcaCycle>(`/pdca/cycles/${id}/`, data).then((r) => r.data),
  remove: (id: string, reason: string) =>
    apiClient.delete(`/pdca/cycles/${id}/`, { data: { reason } }),
  archivia: (id: string, motivo: string) =>
    apiClient.post(`/pdca/cycles/${id}/archivia/`, { motivo }),
  /** `reason` obbligatorio se il finding ha già un PDCA (viene sostituito). */
  linkFinding: (cycleId: string, findingId: string, reason?: string) =>
    apiClient.post<PdcaCycle>(`/pdca/cycles/${cycleId}/link-finding/`, { finding: findingId, ...(reason ? { reason } : {}) }).then((r) => r.data),
  unlinkFinding: (cycleId: string, findingId: string, reason: string) =>
    apiClient.post<PdcaCycle>(`/pdca/cycles/${cycleId}/unlink-finding/`, { finding: findingId, reason }).then((r) => r.data),
  capabilities: () =>
    apiClient.get<{ can_manage_org: boolean }>("/pdca/cycles/capabilities/").then((r) => r.data),
};
