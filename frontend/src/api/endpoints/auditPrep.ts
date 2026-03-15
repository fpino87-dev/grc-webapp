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

export interface AuditFinding {
  id: string;
  audit_prep: string;
  finding_type: "major_nc"|"minor_nc"|"observation"|"opportunity";
  title: string;
  description: string;
  auditor_name: string;
  audit_date: string;
  response_deadline: string | null;
  status: "open"|"in_response"|"closed"|"accepted_by_auditor";
  root_cause: string;
  corrective_action: string;
  pdca_cycle: string | null;
  closure_notes: string;
  closed_at: string | null;
  closed_by_name: string | null;
  control_external_id: string | null;
  is_overdue: boolean;
  days_remaining: number | null;
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
  findings: (prepId: string) =>
    apiClient.get<{ results: AuditFinding[] }>("/audit-prep/findings/", { params: { audit_prep: prepId } }).then(r => r.data.results),
  createFinding: (data: Record<string, unknown>) =>
    apiClient.post<AuditFinding>("/audit-prep/findings/", data).then(r => r.data),
  closeFinding: (id: string, data: { closure_notes: string; evidence_id?: string }) =>
    apiClient.post<{ ok: boolean; status: string }>(`/audit-prep/findings/${id}/close/`, data).then(r => r.data),
  programs: (params?: Record<string, string>) =>
    apiClient.get<{ results: AuditProgram[] }>("/audit-prep/programs/", { params }).then(r => r.data),
  createProgram: (data: Partial<AuditProgram>) =>
    apiClient.post<AuditProgram>("/audit-prep/programs/", data).then(r => r.data),
  approveProgram: (id: string) =>
    apiClient.post<{ ok: boolean; status: string }>(`/audit-prep/programs/${id}/approve/`).then(r => r.data),
};

export interface AuditProgram {
  id: string;
  plant: string;
  framework: string;
  year: number;
  title: string;
  status: "bozza"|"approvato"|"in_corso"|"completato";
  objectives: string;
  scope: string;
  planned_audits: PlannedAudit[];
  completion_pct: number;
  next_planned_audit: PlannedAudit | null;
  approved_by_name: string | null;
  approved_at: string | null;
}

export interface PlannedAudit {
  quarter: number;
  scope_domains: string[];
  auditor_type: "interno"|"esterno";
  auditor_name: string;
  planned_date: string;
  actual_date: string | null;
  audit_prep_id: string | null;
  status: "planned"|"completed"|"cancelled";
}
