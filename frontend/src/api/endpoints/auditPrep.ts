import { apiClient } from "../client";

export interface AuditPrep {
  id: string;
  plant: string;
  framework: string | null;
  framework_code: string | null;
  title: string;
  audit_date: string | null;
  auditor_name: string;
  status: "in_corso" | "completato" | "archiviato";
  readiness_score: number | null;
  owner: string | null;
  audit_program: string | null;
  audit_entry_id: string;
  coverage_type: "campione" | "esteso" | "full";
}

export interface EvidenceItem {
  id: string;
  audit_prep: string;
  control_instance: string | null;
  description: string;
  status: "mancante" | "presente" | "scaduto";
  notes: string;
  due_date: string | null;
}

export interface AuditFinding {
  id: string;
  audit_prep: string;
  finding_type: "major_nc" | "minor_nc" | "observation" | "opportunity";
  title: string;
  description: string;
  auditor_name: string;
  audit_date: string;
  response_deadline: string | null;
  status: "open" | "in_response" | "closed" | "accepted_by_auditor";
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

export interface PlannedAudit {
  id: string;
  quarter: number;
  title: string;
  framework_codes: string[];
  coverage_type: "campione" | "esteso" | "full";
  scope_domains: string[];
  suggested_domains: string[];
  auditor_type: "interno" | "esterno";
  auditor_name: string;
  planned_date: string;
  actual_date: string | null;
  audit_prep_id: string | null;
  status: "planned" | "in_progress" | "completed" | "cancelled";
  notes: string;
}

export interface AuditProgram {
  id: string;
  plant: string;
  framework: string | null;
  framework_code: string | null;
  frameworks: string[];
  coverage_type: "campione" | "esteso" | "full";
  year: number;
  title: string;
  status: "bozza" | "approvato" | "in_corso" | "completato";
  objectives: string;
  scope: string;
  planned_audits: PlannedAudit[];
  completion_pct: number;
  next_planned_audit: PlannedAudit | null;
  approved_by_name: string | null;
  approved_at: string | null;
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
  complete: (id: string) =>
    apiClient.post<{ ok: boolean; status: string }>(`/audit-prep/audit-preps/${id}/complete/`).then(r => r.data),
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
  createProgram: (data: Record<string, unknown>) =>
    apiClient.post<AuditProgram>("/audit-prep/programs/", data).then(r => r.data),
  approveProgram: (id: string) =>
    apiClient.post<{ ok: boolean; status: string }>(`/audit-prep/programs/${id}/approve/`).then(r => r.data),
  suggestPlan: (data: { plant: string; framework_codes: string[]; year: number; coverage_type: string }) =>
    apiClient.post<{ suggested_plan: PlannedAudit[] }>("/audit-prep/programs/suggest/", data).then(r => r.data),
  launchAudit: (programId: string, auditId: string) =>
    apiClient.post<{ ok: boolean; audit_prep_id: string; controls_count: number }>(
      `/audit-prep/programs/${programId}/launch-audit/`, { audit_id: auditId }
    ).then(r => r.data),
  updateAudit: (programId: string, auditId: string, updates: Record<string, unknown>) =>
    apiClient.post<{ ok: boolean; planned_audits: PlannedAudit[] }>(
      `/audit-prep/programs/${programId}/update-audit/`, { audit_id: auditId, updates }
    ).then(r => r.data),
  syncCompletion: (programId: string) =>
    apiClient.post<{ ok: boolean; completion_pct: number; status: string }>(
      `/audit-prep/programs/${programId}/sync-completion/`
    ).then(r => r.data),
  downloadPrepReport: (id: string) =>
    apiClient.get(`/audit-prep/audit-preps/${id}/report/`, { responseType: "blob" }),
  downloadProgramReport: (id: string) =>
    apiClient.get(`/audit-prep/programs/${id}/report/`, { responseType: "blob" }),
  deletePrep: (id: string) =>
    apiClient.delete(`/audit-prep/audit-preps/${id}/`),
  deleteProgram: (id: string) =>
    apiClient.delete(`/audit-prep/programs/${id}/`),
  annulla: (id: string, reason: string) =>
    apiClient.post(`/audit-prep/audit-preps/${id}/annulla/`, { reason }),
};
