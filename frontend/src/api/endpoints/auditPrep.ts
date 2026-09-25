import { apiClient } from "../client";
import { fetchAllPages } from "../pagination";

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
  // Chi conduce l'audit; per la seconda parte il committente è il cliente.
  audit_type: AuditType;
  // Audit interno affidato a un consulente esterno: gestito come la seconda parte.
  external_consultant: boolean;
  requesting_party: string;
  // Rapporto ufficiale dell'auditor/ente (evidenza), impostato solo via report-file.
  report_evidence: string | null;
  report_evidence_title: string | null;
  report_evidence_filename: string | null;
  // Audit multi-sito: gruppo e siti coinvolti (vuoto per un audit di un solo sito)
  group: string | null;
  group_title: string | null;
  group_scope_id: string | null;
  group_sites: { prep: string; plant: string; plant_code: string }[];
}

export interface AuditGroup {
  id: string;
  title: string;
  framework: string | null;
  audit_type: AuditType;
  external_consultant: boolean;
  requesting_party: string;
  auditor_name: string;
  audit_date: string | null;
  scope_id: string;
  report_evidence: string | null;
  report_evidence_title: string | null;
  preps: { id: string; plant: string; plant_code: string; status: string; readiness_score: number | null }[];
}

export type AuditType = "interno" | "seconda_parte" | "terza_parte";

export interface EvidenceItem {
  id: string;
  audit_prep: string;
  control_instance: string | null;
  description: string;
  /** `na` = controllo non applicabile o escluso dalla SoA: resta in elenco con
   *  la giustificazione, senza rilievi e fuori dal punteggio di prontezza. */
  status: "mancante" | "presente" | "scaduto" | "na";
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
  status: "open" | "in_response" | "closed" | "accepted_by_auditor" | "not_pursued";
  root_cause: string;
  corrective_action: string;
  pdca_cycle: string | null;
  // Rilievo comune ai siti di un audit multi-sito (stesso valore sui finding gemelli)
  common_key: string | null;
  // PDCA collegato (collegamento univoco finding ↔ PDCA)
  pdca_title: string | null;
  pdca_phase: string | null;
  // PDCA di organizzazione: copre il rilievo comune su tutti i siti
  pdca_is_org: boolean;
  closure_notes: string;
  closure_evidence: string | null;
  closed_at: string | null;
  closed_by_name: string | null;
  control_external_id: string | null;
  is_overdue: boolean;
  days_remaining: number | null;
  auto_generated: boolean;
}

export interface AutoValidateWarning {
  code: "missing_extended_controls";
  framework_requested: string;
  frameworks_expanded: string[];
  missing_frameworks: string[];
  hint: string;
}

export interface AutoValidateResult {
  ok: boolean;
  evaluated: number;
  presente: number;
  scaduto: number;
  mancante: number;
  na: number;
  findings_created: number;
  findings_skipped_existing: number;
  /** Rilievi automatici aperti su controlli oggi non applicabili: segnalati,
   *  non chiusi d'ufficio. */
  findings_obsolete: number;
  readiness_score: number;
  warning?: AutoValidateWarning;
}

export interface SyncControlsResult {
  ok: boolean;
  added: number;
  frameworks_requested: string[];
  frameworks_expanded: string[];
  note?: string;
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
    fetchAllPages<AuditPrep>("/audit-prep/audit-preps/", params).then((results) => ({ results, count: results.length })),
  readiness: (id: string) =>
    apiClient.get<{ score: number }>(`/audit-prep/audit-preps/${id}/readiness/`).then(r => r.data),
  evidence: (prepId: string) =>
    fetchAllPages<EvidenceItem>("/audit-prep/evidence-items/", { audit_prep: prepId }),
  create: (data: Partial<AuditPrep>) =>
    apiClient.post<AuditPrep>("/audit-prep/audit-preps/", data).then(r => r.data),
  update: (id: string, data: Partial<AuditPrep>) =>
    apiClient.patch<AuditPrep>(`/audit-prep/audit-preps/${id}/`, data).then(r => r.data),
  uploadReportFile: (id: string, file: File, title?: string) => {
    const fd = new FormData();
    fd.append("file", file);
    if (title) fd.append("title", title);
    return apiClient.post<AuditPrep>(`/audit-prep/audit-preps/${id}/report-file/`, fd, {
      headers: { "Content-Type": "multipart/form-data" },
    }).then(r => r.data);
  },
  detachReportFile: (id: string) =>
    apiClient.delete(`/audit-prep/audit-preps/${id}/report-file/`),
  downloadReportFile: (id: string) =>
    apiClient.get<Blob>(`/audit-prep/audit-preps/${id}/report-file/`, { responseType: "blob" }).then(r => r.data),
  createGroup: (data: Partial<AuditGroup> & { plants: string[] }) =>
    apiClient.post<AuditGroup>("/audit-prep/audit-groups/", data).then(r => r.data),
  updateGroup: (id: string, data: Partial<AuditGroup>) =>
    apiClient.patch<AuditGroup>(`/audit-prep/audit-groups/${id}/`, data).then(r => r.data),
  complete: (id: string) =>
    apiClient.post<{ ok: boolean; status: string }>(`/audit-prep/audit-preps/${id}/complete/`).then(r => r.data),
  createEvidence: (data: Partial<EvidenceItem>) =>
    apiClient.post<EvidenceItem>("/audit-prep/evidence-items/", data).then(r => r.data),
  updateEvidence: (id: string, data: Partial<EvidenceItem>) =>
    apiClient.patch<EvidenceItem>(`/audit-prep/evidence-items/${id}/`, data).then(r => r.data),
  findings: (prepId: string, extra?: Record<string, string>) =>
    fetchAllPages<AuditFinding>("/audit-prep/findings/", { audit_prep: prepId, ...extra }),
  openPdca: (findingId: string) =>
    apiClient.post<AuditFinding>(`/audit-prep/findings/${findingId}/open-pdca/`, {}).then(r => r.data),
  openCommonPdca: (findingId: string) =>
    apiClient.post<AuditFinding>(`/audit-prep/findings/${findingId}/open-common-pdca/`, {}).then(r => r.data),
  linkPdca: (findingId: string, cycleId: string) =>
    apiClient.post<AuditFinding>(`/audit-prep/findings/${findingId}/link-pdca/`, { pdca_cycle: cycleId }).then(r => r.data),
  closeWithPdca: (findingId: string) =>
    apiClient.post<AuditFinding>(`/audit-prep/findings/${findingId}/close-with-pdca/`, {}).then(r => r.data),
  replacePdca: (findingId: string, cycleId: string, reason: string) =>
    apiClient.post<AuditFinding>(`/audit-prep/findings/${findingId}/replace-pdca/`, { pdca_cycle: cycleId, reason }).then(r => r.data),
  unlinkPdca: (findingId: string, reason: string) =>
    apiClient.post<AuditFinding>(`/audit-prep/findings/${findingId}/unlink-pdca/`, { reason }).then(r => r.data),
  createFinding: (data: Record<string, unknown>) =>
    apiClient.post<AuditFinding>("/audit-prep/findings/", data).then(r => r.data),
  /** Corregge i testi del finding (nel rilievo comune titolo e descrizione valgono per tutti i siti). */
  updateFinding: (id: string, data: Partial<Pick<AuditFinding, "title" | "description" | "root_cause" | "corrective_action">>) =>
    apiClient.patch<AuditFinding>(`/audit-prep/findings/${id}/`, data).then(r => r.data),
  /** Osservazione/opportunità non perseguita: motivo, prova facoltativa (evidenza esistente o file). */
  notPursueFinding: (id: string, data: { reason: string; evidence_id?: string; file?: File | null; evidence_title?: string }) => {
    if (data.file) {
      const fd = new FormData();
      fd.append("reason", data.reason);
      fd.append("file", data.file);
      if (data.evidence_title) fd.append("evidence_title", data.evidence_title);
      return apiClient.post<AuditFinding>(`/audit-prep/findings/${id}/not-pursue/`, fd, {
        headers: { "Content-Type": "multipart/form-data" },
      }).then(r => r.data);
    }
    return apiClient.post<AuditFinding>(`/audit-prep/findings/${id}/not-pursue/`,
      { reason: data.reason, ...(data.evidence_id ? { evidence_id: data.evidence_id } : {}) }).then(r => r.data);
  },
  reopenFinding: (id: string, reason: string) =>
    apiClient.post<AuditFinding>(`/audit-prep/findings/${id}/reopen/`, { reason }).then(r => r.data),
  closeFinding: (id: string, data: { closure_notes: string; evidence_id?: string }) =>
    apiClient.post<{ ok: boolean; status: string }>(`/audit-prep/findings/${id}/close/`, data).then(r => r.data),
  programs: (params?: Record<string, string>) =>
    fetchAllPages<AuditProgram>("/audit-prep/programs/", params).then((results) => ({ results, count: results.length })),
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
  autoValidate: (id: string) =>
    apiClient.post<AutoValidateResult>(
      `/audit-prep/audit-preps/${id}/auto-validate/`
    ).then(r => r.data),
  syncControls: (id: string) =>
    apiClient.post<SyncControlsResult>(
      `/audit-prep/audit-preps/${id}/sync-controls/`
    ).then(r => r.data),
};
