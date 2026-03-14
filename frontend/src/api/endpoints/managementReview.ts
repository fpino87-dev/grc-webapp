import { apiClient } from "../client";

export interface ManagementReview {
  id: string;
  plant: string | null;
  title: string;
  held_at: string | null;
  status: string;
  created_at: string;
}

export const managementReviewApi = {
  list: (params?: Record<string, string>) =>
    apiClient.get<{ results: ManagementReview[] }>("/management-review/reviews/", { params }).then((r) => r.data),
  create: (data: Partial<ManagementReview>) =>
    apiClient.post<ManagementReview>("/management-review/reviews/", data).then((r) => r.data),
};
