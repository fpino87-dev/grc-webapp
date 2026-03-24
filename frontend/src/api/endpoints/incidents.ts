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
  nis2_sector?: string;
  nis2_subsector?: string;
  internal_contact_name?: string;
  internal_contact_email?: string;
  internal_contact_phone?: string;
  legal_entity_name?: string;
  legal_entity_vat?: string;
}

export const incidentsApi = {
  list: (params?: Record<string, string>) =>
    apiClient.get<{ results: Incident[]; count: number }>("/incidents/incidents/", { params }).then((r) => r.data),
  get: (id: string) => apiClient.get<Incident>(`/incidents/incidents/${id}/`).then((r) => r.data),
  create: (data: Partial<Incident>) =>
    apiClient.post<Incident>("/incidents/incidents/", data).then((r) => r.data),
  update: (id: string, data: Partial<Incident>) =>
    apiClient.patch<Incident>(`/incidents/incidents/${id}/`, data).then((r) => r.data),
  close: (id: string) =>
    apiClient.post(`/incidents/incidents/${id}/close/`).then((r) => r.data),
  classifySignificance: (id: string, data?: { override?: boolean; reason?: string }) =>
    apiClient.post(`/incidents/incidents/${id}/classify-significance/`, data ?? {}).then((r) => r.data),
  timeline: (id: string) =>
    apiClient.get<NIS2Timeline>(`/incidents/incidents/${id}/nis2-timeline/`).then((r) => r.data),
  notifications: (id: string) =>
    apiClient.get<NIS2Notification[]>(`/incidents/incidents/${id}/nis2-notifications/`).then((r) => r.data),
  markSent: (
    id: string,
    payload: { notification_type: string; protocol_ref?: string; authority_response?: string }
  ) => apiClient.post(`/incidents/incidents/${id}/mark-sent/`, payload).then((r) => r.data),
  generateDocument: async (id: string, type: string) => {
    const res = await fetch(
      `${(apiClient.defaults.baseURL ?? "").replace(/\/$/, "")}/incidents/incidents/${id}/generate-document/?type=${type}`,
      {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access") ?? ""}`,
        },
      }
    );
    const text = await res.text();
    return { ok: res.ok, text };
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
