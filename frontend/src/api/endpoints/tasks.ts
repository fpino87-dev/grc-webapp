import { apiClient } from "../client";

export type TaskRecurrence =
  | "none"
  | "daily"
  | "weekly"
  | "monthly"
  | "quarterly"
  | "semiannual"
  | "yearly";

export const TASK_RECURRENCES: TaskRecurrence[] = [
  "none",
  "daily",
  "weekly",
  "monthly",
  "quarterly",
  "semiannual",
  "yearly",
];

export interface Task {
  id: string; title: string; description: string;
  plant: string | null; priority: "bassa"|"media"|"alta"|"critica";
  status: "aperto"|"in_corso"|"completato"|"annullato"|"scaduto";
  source: string; due_date: string | null;
  assigned_to: string | null; recurrence: TaskRecurrence; escalation_level: number;
  source_module: string; source_id: string | null;
  control_instance: string | null;
}

export const tasksApi = {
  list: (params?: Record<string,string>) =>
    apiClient.get<{results: Task[]; count: number}>("/tasks/tasks/", {params}).then(r => r.data),
  complete: (id: string, notes?: string) =>
    apiClient.post(`/tasks/tasks/${id}/complete/`, {notes}).then(r => r.data),
  create: (data: Partial<Task>) =>
    apiClient.post<Task>("/tasks/tasks/", data).then(r => r.data),
  delete: (id: string) =>
    apiClient.delete(`/tasks/tasks/${id}/`).then(r => r.data),
};
