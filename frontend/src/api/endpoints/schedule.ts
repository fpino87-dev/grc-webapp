import { apiClient } from "../client";

export interface ScheduleRule {
  id: string;
  rule_type: string;
  rule_type_label: string;
  frequency_value: number;
  frequency_unit: "days" | "weeks" | "months" | "years";
  alert_days_before: number;
  enabled: boolean;
}

export interface SchedulePolicy {
  id: string;
  plant: string | null;
  plant_name: string | null;
  name: string;
  is_active: boolean;
  valid_from: string;
  notes: string;
  rules: ScheduleRule[];
}

export interface ActivityItem {
  category: string;
  category_label: string;
  label: string;
  due_date: string;
  days_left: number;
  urgency: "green" | "yellow" | "red";
  status: string;
  ref_id: string;
  url: string;
}

export interface RequiredDocControl {
  instance_id: string;
  external_id: string;
  title: string;
}

export interface RequiredDocFulfillment {
  kind: "document" | "evidence";
  id: string;
  title: string;
  status: string;
  valid_until: string | null;
  linked_by: string | null;
  linked_at: string | null;
}

export interface RequiredDocItem {
  id: string;
  document_type: string;
  description: string;
  iso_clause: string;
  mandatory: boolean;
  notes: string;
  traffic_light: "green" | "yellow" | "red";
  document: {
    id: string;
    title: string;
    status: string;
    review_due_date: string | null;
  } | null;
  control: RequiredDocControl | null;
  control_status: "resolved" | "no_instance" | "system";
  linkable_count: number;
  fulfillment: RequiredDocFulfillment | null;
}

export interface LinkableDocument {
  id: string;
  title: string;
  document_type: string;
  status: string;
}

export interface LinkableEvidence {
  id: string;
  title: string;
  evidence_type: string;
  valid_until: string | null;
  valid: boolean;
}

export interface RequiredDocLinkables {
  control: RequiredDocControl | null;
  documents: LinkableDocument[];
  evidences: LinkableEvidence[];
}

export interface RequiredDocumentsStatus {
  framework: string;
  total: number;
  green: number;
  yellow: number;
  red: number;
  results: RequiredDocItem[];
}

export interface RequiredDocumentCatalog {
  id: string;
  framework: string;
  document_type: string;
  description: string;
  iso_clause: string;
  mandatory: boolean;
  notes: string;
}

export interface FrameworkControl {
  external_id: string;
  title: string;
  level: string;
}

export const scheduleApi = {
  listPolicies: (plant?: string) =>
    apiClient.get<{ results: SchedulePolicy[] }>("/schedule/policies/", {
      params: plant ? { plant } : {},
    }).then(r => r.data),

  getPolicy: (id: string) =>
    apiClient.get<SchedulePolicy>(`/schedule/policies/${id}/`).then(r => r.data),

  createDefaultPolicy: (data: { plant_id?: string; name?: string }) =>
    apiClient.post<SchedulePolicy>("/schedule/policies/create-default/", data).then(r => r.data),

  updateRule: (policyId: string, data: Partial<ScheduleRule> & { rule_type: string }) =>
    apiClient.patch<ScheduleRule>(`/schedule/policies/${policyId}/update-rule/`, data).then(r => r.data),

  getActivitySchedule: (params?: { plant?: string; months?: number }) =>
    apiClient.get<{ results: ActivityItem[]; count: number }>("/schedule/activity/", { params }).then(r => r.data),

  getRequiredDocumentsStatus: (params?: { plant?: string; framework?: string }) =>
    apiClient.get<RequiredDocumentsStatus>("/schedule/required-documents-status/", { params }).then(r => r.data),

  getRequiredDocLinkables: (params: { plant: string; required_document: string }) =>
    apiClient.get<RequiredDocLinkables>("/schedule/required-documents-linkables/", { params }).then(r => r.data),

  linkRequiredDoc: (data: { plant: string; required_document: string; document?: string; evidence?: string }) =>
    apiClient.post("/schedule/required-documents-fulfillment/", data).then(r => r.data),

  unlinkRequiredDoc: (params: { plant: string; required_document: string }) =>
    apiClient.delete("/schedule/required-documents-fulfillment/", { params }),

  getRuleTypes: () =>
    apiClient.get("/schedule/rule-types/").then(r => r.data),

  // ── Catalogo documenti obbligatori (CRUD, solo ruoli abilitati) ──────────
  listRequiredDocuments: (framework: string) =>
    apiClient.get<{ results: RequiredDocumentCatalog[] }>("/schedule/required-documents/", {
      params: { framework, page_size: 1000 },
    }).then(r => r.data.results ?? []),

  createRequiredDocument: (data: Omit<RequiredDocumentCatalog, "id">) =>
    apiClient.post<RequiredDocumentCatalog>("/schedule/required-documents/", data).then(r => r.data),

  updateRequiredDocument: (id: string, data: Partial<Omit<RequiredDocumentCatalog, "id">>) =>
    apiClient.patch<RequiredDocumentCatalog>(`/schedule/required-documents/${id}/`, data).then(r => r.data),

  deleteRequiredDocument: (id: string) =>
    apiClient.delete(`/schedule/required-documents/${id}/`),

  getFrameworkControls: (framework: string) =>
    apiClient.get<{ results: FrameworkControl[] }>("/schedule/framework-controls/", {
      params: { framework },
    }).then(r => r.data.results ?? []),
};
