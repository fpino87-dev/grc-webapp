import { apiClient } from "../client";

export type DecisionType = "miglioramento" | "modifica_sgsi" | "risorse" | "obiettivo" | "altro";

/** Obiettivo di sicurezza (§6.2) deliberato dal riesame. Nasce in bozza:
 *  il riesame decide *che* ci sarà un obiettivo, il piano richiesto dalla
 *  norma si completa dopo la riunione. */
export interface DecisionObjective {
  code: string;
  title?: string;
  measure_source: "kpi" | "manual";
  kpi_definition?: string | null;
  unit?: string;
  baseline_value?: number | null;
  target_value: number;
  target_direction?: "above" | "below";
  target_date?: string | null;
  owner_role?: string;
}

export interface ReviewAction {
  id: string;
  review: string;
  agenda_item: string | null;
  decision_type: DecisionType;
  description: string;
  owner: number | null;
  owner_name: string | null;
  due_date: string | null;
  status: "aperto" | "chiuso";
  closed_at: string | null;
  task: string | null;
  task_status: string | null;
  task_title: string | null;
  pdca_cycle: string | null;
  pdca_phase: string | null;
  pdca_title: string | null;
  security_objective: string | null;
  objective_code: string | null;
  objective_status: string | null;
  created_at: string;
}

export interface ReviewAgendaItem {
  id: string;
  review: string;
  code: string;
  title: string;
  order: number;
  mandatory: boolean;
  discussion: string;
  updated_at: string;
}

export interface ExecutiveSummaryMeta {
  ai_assisted?: boolean;
  provider?: string;
  model?: string;
  edited?: boolean;
  accepted_by_name?: string;
  accepted_at?: string;
  generated_at?: string;
  snapshot_generated_at?: string;
  used_fallback?: boolean;
}

export type ParticipantRole = "presidente" | "membro" | "segretario" | "ospite";
export type Attendance = "presente" | "assente" | "delegato";

export interface ReviewParticipant {
  id?: string;
  member: string | null;
  user: number | null;
  full_name: string;
  position: string;
  body_role: ParticipantRole;
  is_chair: boolean;
  attendance: Attendance;
  delegate_name: string;
  has_account?: boolean;
}

export interface ManagementReview {
  id: string;
  plant: string | null;
  plant_name: string | null;
  title: string;
  review_date: string;
  next_review_date: string | null;
  governing_body: string | null;
  governing_body_name: string | null;
  /** Sito il cui logo compare in testa al verbale PDF/HTML. */
  report_logo_plant: string | null;
  report_logo_plant_code: string | null;
  chair_name: string | null;
  participants: ReviewParticipant[];
  status: "pianificato" | "in_corso" | "completato";
  approval_status: "bozza" | "in_review" | "approvato" | "rifiutato";
  approved_by: number | null;
  approved_by_name: string | null;
  approved_at: string | null;
  approval_note: string;
  approval_mode: "" | "in_app" | "delibera";
  approved_member: string | null;
  approved_member_name: string | null;
  approval_resolution_ref: string;
  approval_resolution_date: string | null;
  approval_document_id: string | null;
  /** L'utente corrente può approvare: governance o componente in carica dell'organo. */
  viewer_can_approve: boolean;
  snapshot_generated_at: string | null;
  snapshot_data: Record<string, unknown>;
  executive_summary: string;
  executive_summary_meta: ExecutiveSummaryMeta;
  executive_summary_draft: string;
  executive_summary_draft_meta: ExecutiveSummaryMeta;
  actions: ReviewAction[];
  agenda_items: ReviewAgendaItem[];
  created_at: string;
}

export interface CreateActionPayload {
  review: string;
  agenda_item?: string | null;
  decision_type: DecisionType;
  description: string;
  owner?: number | null;
  due_date?: string | null;
  create_task?: boolean;
  task_role?: string;
  create_pdca?: boolean;
  pdca_plant?: string | null;
  objective?: DecisionObjective | null;
}

const base = "/management-review/reviews";

export const managementReviewApi = {
  list: (params?: Record<string, string>) =>
    apiClient.get<{ results: ManagementReview[] }>(`${base}/`, { params }).then((r) => r.data),

  create: (data: Partial<ManagementReview>) =>
    apiClient.post<ManagementReview>(`${base}/`, data).then((r) => r.data),

  update: (id: string, data: Partial<ManagementReview>) =>
    apiClient.patch<ManagementReview>(`${base}/${id}/`, data).then((r) => r.data),

  suggestedChair: (plant: string | null) =>
    apiClient
      .get<{ id: number | null; name: string | null }>(`${base}/suggested-chair/`, {
        params: plant ? { plant } : {},
      })
      .then((r) => r.data),

  start: (id: string) => apiClient.post<ManagementReview>(`${base}/${id}/start/`).then((r) => r.data),

  complete: (id: string) => apiClient.post<ManagementReview>(`${base}/${id}/complete/`).then((r) => r.data),

  generateSnapshot: (id: string) =>
    apiClient.post<Record<string, unknown>>(`${base}/${id}/generate-snapshot/`).then((r) => r.data),

  approve: (id: string, data: {
    note: string; mode: "in_app" | "delibera";
    resolution_ref?: string; resolution_date?: string; document_id?: string | null;
  }) =>
    apiClient.post<ManagementReview>(`${base}/${id}/approve/`, data).then((r) => r.data),

  // Documenti deliberati nella seduta: ereditano gli estremi della delibera
  // già registrata sull'approvazione del riesame.
  approveDocuments: (id: string, document_ids: string[]) =>
    apiClient
      .post<{
        approved: Array<{ id: string; title: string }>;
        skipped: Array<{ id: string; title?: string; reason: string }>;
      }>(`${base}/${id}/approve-documents/`, { document_ids })
      .then((r) => r.data),

  setParticipants: (id: string, participants: ReviewParticipant[]) =>
    apiClient.put<ManagementReview>(`${base}/${id}/participants/`, { participants }).then((r) => r.data),

  setReportLogo: (id: string, plant: string | null) =>
    apiClient.post<ManagementReview>(`${base}/${id}/report-logo/`, { plant }).then((r) => r.data),

  participantsFromBody: (id: string) =>
    apiClient.post<ManagementReview>(`${base}/${id}/participants-from-body/`).then((r) => r.data),

  delete: (id: string) => apiClient.delete(`${base}/${id}/`).then((r) => r.data),

  draftSummary: (id: string, lang: string) =>
    apiClient.post<ManagementReview>(`${base}/${id}/summary-draft/`, { lang }).then((r) => r.data),

  discardSummaryDraft: (id: string) =>
    apiClient.delete<ManagementReview>(`${base}/${id}/summary-draft/`).then((r) => r.data),

  saveSummary: (id: string, text: string) =>
    apiClient.post<ManagementReview>(`${base}/${id}/summary/`, { text }).then((r) => r.data),

  downloadReport: async (id: string, filename: string, fmt: "html" | "pdf" = "html") => {
    const resp = await apiClient.get(`${base}/${id}/report/`, { params: { fmt }, responseType: "blob" });
    const type = fmt === "pdf" ? "application/pdf" : "text/html";
    const url = URL.createObjectURL(new Blob([resp.data as BlobPart], { type }));
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  },

  addAgendaItem: (review: string, title: string) =>
    apiClient.post<ReviewAgendaItem>("/management-review/agenda-items/", { review, title }).then((r) => r.data),

  updateAgendaItem: (id: string, data: Partial<Pick<ReviewAgendaItem, "discussion" | "title">>) =>
    apiClient.patch<ReviewAgendaItem>(`/management-review/agenda-items/${id}/`, data).then((r) => r.data),

  deleteAgendaItem: (id: string) =>
    apiClient.delete(`/management-review/agenda-items/${id}/`).then((r) => r.data),

  createAction: (data: CreateActionPayload) =>
    apiClient.post<ReviewAction>("/management-review/review-actions/", data).then((r) => r.data),

  updateAction: (id: string, data: Partial<ReviewAction>) =>
    apiClient.patch<ReviewAction>(`/management-review/review-actions/${id}/`, data).then((r) => r.data),

  deleteAction: (id: string) =>
    apiClient.delete(`/management-review/review-actions/${id}/`).then((r) => r.data),
};

/** Messaggio d'errore delle azioni di dominio (`{"error": ...}`) con fallback. */
export function reviewErrorMessage(e: unknown, fallback: string): string {
  const data = (e as { response?: { data?: { error?: string; detail?: string } } })?.response?.data;
  return data?.error || data?.detail || fallback;
}
