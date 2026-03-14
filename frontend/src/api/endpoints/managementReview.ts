import { apiClient } from "../client";

export interface ManagementReview {
  id: string;
  plant: string | null;
  title: string;
  review_date: string;
  held_at: string | null;
  status: string;
  approval_status: string;
  approved_by: string | null;
  approved_at: string | null;
  approval_note: string;
  snapshot_generated_at: string | null;
  snapshot_data: Record<string, unknown>;
  created_at: string;
}

export const managementReviewApi = {
  list: (params?: Record<string, string>) =>
    apiClient.get<{ results: ManagementReview[] }>("/management-review/reviews/", { params }).then((r) => r.data),
  create: (data: Partial<ManagementReview>) =>
    apiClient.post<ManagementReview>("/management-review/reviews/", data).then((r) => r.data),
  generateSnapshot: (id: string) =>
    apiClient.post<Record<string, unknown>>(`/management-review/reviews/${id}/generate-snapshot/`).then((r) => r.data),
  approve: (id: string, note: string) =>
    apiClient.post<ManagementReview>(`/management-review/reviews/${id}/approve/`, { note }).then((r) => r.data),
};
