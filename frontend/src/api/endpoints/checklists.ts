import { apiClient } from "../client";

export type ChecklistFrequency = "daily" | "weekly" | "monthly" | "ad_hoc";
export type ChecklistRunStatus = "pending" | "in_progress" | "completed" | "overdue";

export interface ChecklistTemplateItem {
  id?: string;
  order: number;
  text: string;
  is_mandatory: boolean;
}

export interface ChecklistTemplate {
  id: string;
  name: string;
  description: string;
  frequency: ChecklistFrequency;
  plant: string | null;
  plant_name?: string | null;
  is_active: boolean;
  items: ChecklistTemplateItem[];
  runs_count?: number;
  created_at?: string;
  updated_at?: string;
}

export interface ChecklistRunItem {
  id: string;
  template_item: string;
  text: string;
  is_mandatory: boolean;
  order: number;
  checked: boolean;
  note: string;
  checked_at: string | null;
  checked_by: string | null;
}

export interface ChecklistRun {
  id: string;
  template: string;
  template_name: string;
  plant: string;
  plant_name?: string;
  assigned_to: string | null;
  due_date: string;
  completed_at: string | null;
  completed_by: string | null;
  status: ChecklistRunStatus;
  items: ChecklistRunItem[];
  progress_total: number;
  progress_done: number;
  created_at: string;
}

const TPL = "/tasks/checklist-templates/";
const RUN = "/tasks/checklist-runs/";

export const checklistsApi = {
  // Template
  listTemplates: (params?: Record<string, string>) =>
    apiClient
      .get<{ results: ChecklistTemplate[]; count: number }>(TPL, { params })
      .then((r) => r.data),
  getTemplate: (id: string) =>
    apiClient.get<ChecklistTemplate>(`${TPL}${id}/`).then((r) => r.data),
  createTemplate: (data: Partial<ChecklistTemplate>) =>
    apiClient.post<ChecklistTemplate>(TPL, data).then((r) => r.data),
  updateTemplate: (id: string, data: Partial<ChecklistTemplate>) =>
    apiClient.patch<ChecklistTemplate>(`${TPL}${id}/`, data).then((r) => r.data),
  deleteTemplate: (id: string) =>
    apiClient.delete(`${TPL}${id}/`).then((r) => r.data),

  // Run
  listRuns: (params?: Record<string, string>) =>
    apiClient
      .get<{ results: ChecklistRun[]; count: number }>(RUN, { params })
      .then((r) => r.data),
  getRun: (id: string) =>
    apiClient.get<ChecklistRun>(`${RUN}${id}/`).then((r) => r.data),
  completeItem: (
    runId: string,
    payload: { item_id: string; checked: boolean; note?: string }
  ) =>
    apiClient
      .post<ChecklistRun>(`${RUN}${runId}/complete-item/`, payload)
      .then((r) => r.data),
  completeRun: (runId: string) =>
    apiClient.post<ChecklistRun>(`${RUN}${runId}/complete/`, {}).then((r) => r.data),
};
