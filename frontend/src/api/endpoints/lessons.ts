import { apiClient } from "../client";
import { fetchAllPages } from "../pagination";

export interface LessonLearned {
  id: string; title: string; description: string;
  category: string; status: "bozza"|"validato"|"propagato";
  plant: string | null; corrective_action: string; created_at: string;
}

export const lessonsApi = {
  list: (params?: Record<string, string>) =>
    fetchAllPages<LessonLearned>("/lessons/lessons/", params).then((results) => ({ results, count: results.length })),
  validate: (id: string) =>
    apiClient.post(`/lessons/lessons/${id}/validate/`).then(r => r.data),
  create: (data: Partial<LessonLearned>) =>
    apiClient.post<LessonLearned>("/lessons/lessons/", data).then(r => r.data),
};
