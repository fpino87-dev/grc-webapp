import { apiClient } from "../client";

export interface ReviewAction {
  id: string;
  review: string;
  description: string;
  owner: number | null;
  owner_name: string | null;
  due_date: string | null;
  status: "aperto" | "chiuso";
  closed_at: string | null;
  created_at: string;
}

export interface ManagementReview {
  id: string;
  plant: string | null;
  plant_name: string | null;
  title: string;
  review_date: string;
  next_review_date: string | null;
  status: "pianificato" | "in_corso" | "completato";
  approval_status: "bozza" | "in_review" | "approvato" | "rifiutato";
  approved_by: string | null;
  approved_at: string | null;
  approval_note: string;
  snapshot_generated_at: string | null;
  snapshot_data: Record<string, unknown>;
  actions: ReviewAction[];
  created_at: string;
}

export const managementReviewApi = {
  list: (params?: Record<string, string>) =>
    apiClient.get<{ results: ManagementReview[] }>("/management-review/reviews/", { params }).then((r) => r.data),

  create: (data: Partial<ManagementReview>) =>
    apiClient.post<ManagementReview>("/management-review/reviews/", data).then((r) => r.data),

  update: (id: string, data: Partial<ManagementReview>) =>
    apiClient.patch<ManagementReview>(`/management-review/reviews/${id}/`, data).then((r) => r.data),

  generateSnapshot: (id: string) =>
    apiClient.post<Record<string, unknown>>(`/management-review/reviews/${id}/generate-snapshot/`).then((r) => r.data),

  approve: (id: string, note: string) =>
    apiClient.post<ManagementReview>(`/management-review/reviews/${id}/approve/`, { note }).then((r) => r.data),

  delete: (id: string) =>
    apiClient.delete(`/management-review/reviews/${id}/`).then((r) => r.data),

  downloadReport: async (id: string, filename: string) => {
    const resp = await apiClient.get(`/management-review/reviews/${id}/report/`, { responseType: "blob" });
    const url = URL.createObjectURL(new Blob([resp.data as BlobPart], { type: "text/html" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  },

  createAction: (data: { review: string; description: string; owner?: number | null; due_date?: string | null }) =>
    apiClient.post<ReviewAction>("/management-review/review-actions/", data).then((r) => r.data),

  updateAction: (id: string, data: Partial<ReviewAction>) =>
    apiClient.patch<ReviewAction>(`/management-review/review-actions/${id}/`, data).then((r) => r.data),

  deleteAction: (id: string) =>
    apiClient.delete(`/management-review/review-actions/${id}/`).then((r) => r.data),
};
