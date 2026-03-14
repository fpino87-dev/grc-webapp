import { apiClient } from "../client";

export interface AuditPrep {
  id: string; plant: string; framework: string;
  title: string; audit_date: string | null; auditor_name: string;
  status: "in_corso"|"completato"|"archiviato";
  readiness_score: number | null; owner: string | null;
}

export interface EvidenceItem {
  id: string; audit_prep: string; description: string;
  status: "mancante"|"presente"|"scaduto"; notes: string;
  due_date: string | null;
}

export const auditPrepApi = {
  list: (params?: Record<string, string>) =>
    apiClient.get<{ results: AuditPrep[] }>("/audit-prep/audit-preps/", { params }).then(r => r.data),
  readiness: (id: string) =>
    apiClient.get<{ score: number }>(`/audit-prep/audit-preps/${id}/readiness/`).then(r => r.data),
  evidence: (prepId: string) =>
    apiClient.get<{ results: EvidenceItem[] }>("/audit-prep/evidence-items/", { params: { audit_prep: prepId } }).then(r => r.data.results),
  create: (data: Partial<AuditPrep>) =>
    apiClient.post<AuditPrep>("/audit-prep/audit-preps/", data).then(r => r.data),
  createEvidence: (data: Partial<EvidenceItem>) =>
    apiClient.post<EvidenceItem>("/audit-prep/evidence-items/", data).then(r => r.data),
  updateEvidence: (id: string, data: Partial<EvidenceItem>) =>
    apiClient.patch<EvidenceItem>(`/audit-prep/evidence-items/${id}/`, data).then(r => r.data),
};
