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
  incident_category?: string;
  incident_subcategory?: string;
  affected_users_count?: number | null;
  financial_impact_eur?: string | null;
  service_disruption_hours?: string | null;
  personal_data_involved?: boolean;
  cross_border_impact?: boolean;
  critical_infrastructure_impact?: boolean;
  is_significant?: boolean | null;
  is_recurrent?: boolean;
  significance_override?: boolean | null;
  significance_override_reason?: string;
  axis_operational?: number | null;
  axis_economic?: number | null;
  axis_people?: number | null;
  axis_confidentiality?: number | null;
  axis_reputational?: number | null;
  axis_recurrence?: number | null;
  acn_is_category?: string;
  pta_nis2?: number | null;
  ptnr_nis2?: number | null;
  pt_gdpr?: number | null;
  requires_csirt_notification?: boolean | null;
  requires_gdpr_notification?: boolean | null;
}

export interface NIS2TimelineStep {
  step: string;
  label: string;
  deadline: string | null;
  status: "pending" | "due_soon" | "overdue" | "completed" | "not_applicable";
  completed: boolean;
}

export interface NIS2Timeline {
  entity_type: string;
  steps: NIS2TimelineStep[];
  all_done: boolean;
}

export interface NIS2Notification {
  id: string;
  notification_type: string;
  csirt_name: string;
  sent_at: string | null;
  protocol_ref: string;
  sent_by: string | null;
}

export interface NIS2Configuration {
  id?: string;
  plant: string;
  threshold_users: number;
  threshold_hours: number;
  threshold_financial: number;
  multiplier_medium?: number;
  multiplier_high?: number;
  recurrence_window_days?: number;
  recurrence_score_bonus?: number;
  ptnr_threshold?: number;
  created_at?: string;
  updated_at?: string;
}

export interface ClassificationAxisBreakdown {
  score: number;
  value: number | null;
  threshold: number | null;
  note: string;
}

export interface ClassificationBreakdown {
  scores: Record<string, ClassificationAxisBreakdown>;
  pta_ptnr: {
    PTA: number;
    PTNR: number;
    ricorrenza_bonus: number;
    is_recurrent: boolean;
    asse_dominante: string;
  };
  fattispecie: Record<
    string,
    { active: boolean; applicable: boolean; label: string; description: string }
  >;
  decision: {
    is_significant: boolean;
    requires_csirt_notification?: boolean;
    nis2_notifiable: string;
    rationale: string;
    active_fattispecie: string[];
    by_ptnr?: boolean;
    by_fattispecie?: boolean;
  };
  config_used?: Record<string, unknown>;
  recurrence?: {
    auto_detected: boolean;
    manual_toggle: boolean;
    bonus_applied: number;
    last_similar_closed_at: string | null;
  };
  nis2_scope?: string;
  message?: string;
}

export interface ClassificationMethod {
  taxonomy: {
    categories: Array<{ code: string; label: string; description: string }>;
    subcategories: Record<string, Array<{ code: string; label: string }>>;
  };
  nis2_method: {
    decision_model?: "ptnr_or_fattispecie";
    /** @deprecated API legacy; use decision_model */
    logic?: "OR";
    rule: string;
    criteria_disclaimer?: string;
    thresholds: {
      affected_users_count: number;
      service_disruption_hours: number;
      financial_impact_eur: number;
      multiplier_medium?: number;
      multiplier_high?: number;
      ptnr_trigger_csirt?: number;
      pt_gdpr_trigger?: number;
      recurrence_window_days?: number;
      recurrence_score_bonus?: number;
    };
    criteria: Array<{
      key: string;
      label: string;
      type: "boolean" | "threshold";
      operator?: string;
      threshold?: number;
    }>;
  };
  scores?: {
    axis_operational?: number | null;
    axis_economic?: number | null;
    axis_people?: number | null;
    axis_confidentiality?: number | null;
    axis_reputational?: number | null;
    axis_recurrence?: number | null;
    pta_nis2?: number | null;
    ptnr_nis2?: number | null;
    pt_gdpr?: number | null;
    acn_is_category?: string;
    requires_csirt_notification?: boolean | null;
    requires_gdpr_notification?: boolean | null;
  };
}

export const incidentsApi = {
  list: (params?: Record<string, string>) =>
    apiClient.get<{ results: Incident[]; count: number }>("/incidents/incidents/", { params }).then((r) => r.data),
  get: (id: string) => apiClient.get<Incident>(`/incidents/incidents/${id}/`).then((r) => r.data),
  create: (data: Partial<Incident>) =>
    apiClient.post<Incident>("/incidents/incidents/", data).then((r) => r.data),
  update: (id: string, data: Partial<Incident>) =>
    apiClient.patch<Incident>(`/incidents/incidents/${id}/`, data).then((r) => r.data),
  delete: (id: string) =>
    apiClient.delete(`/incidents/incidents/${id}/`).then((r) => r.data),
  close: (id: string) =>
    apiClient.post(`/incidents/incidents/${id}/close/`).then((r) => r.data),
  classifySignificance: (id: string, data?: { override?: boolean; reason?: string }) =>
    apiClient.post(`/incidents/incidents/${id}/classify-significance/`, data ?? {}).then((r) => r.data),
  classificationBreakdown: (id: string) =>
    apiClient
      .get<ClassificationBreakdown>(`/incidents/incidents/${id}/classification-breakdown/`)
      .then((r) => r.data),
  classificationPreview: (payload: Record<string, unknown>) =>
    apiClient
      .post<ClassificationBreakdown>(`/incidents/incidents/classification-preview/`, payload)
      .then((r) => r.data),
  timeline: (id: string) =>
    apiClient.get<NIS2Timeline>(`/incidents/incidents/${id}/nis2-timeline/`).then((r) => r.data),
  classificationMethod: (id: string) =>
    apiClient.get<ClassificationMethod>(`/incidents/incidents/${id}/classification-method/`).then((r) => r.data),
  notifications: (id: string) =>
    apiClient.get<NIS2Notification[]>(`/incidents/incidents/${id}/nis2-notifications/`).then((r) => r.data),
  markSent: (
    id: string,
    payload: { notification_type: string; protocol_ref?: string; authority_response?: string }
  ) => apiClient.post(`/incidents/incidents/${id}/mark-sent/`, payload).then((r) => r.data),
  generateDocument: async (id: string, type: string) => {
    const res = await apiClient.get(`/incidents/incidents/${id}/generate-document/`, {
      params: { type },
      responseType: "text",
    });
    return { ok: true, text: res.data as string };
  },
  listConfig: (plant: string) =>
    apiClient
      .get<{ results: NIS2Configuration[] }>("/incidents/nis2-configurations/", { params: { plant } })
      .then((r) => r.data.results),
  createConfig: (data: NIS2Configuration) =>
    apiClient.post<NIS2Configuration>("/incidents/nis2-configurations/", data).then((r) => r.data),
  updateConfig: (id: string, data: Partial<NIS2Configuration>) =>
    apiClient.patch<NIS2Configuration>(`/incidents/nis2-configurations/${id}/`, data).then((r) => r.data),
};
