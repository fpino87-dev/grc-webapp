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

export interface RequiredDocItem {
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
}

export interface RequiredDocumentsStatus {
  framework: string;
  total: number;
  green: number;
  yellow: number;
  red: number;
  results: RequiredDocItem[];
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

  getRuleTypes: () =>
    apiClient.get("/schedule/rule-types/").then(r => r.data),
};
