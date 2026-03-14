import { apiClient } from "../client";

export interface LessonLearned {
  id: string; title: string; description: string;
  category: string; status: "bozza"|"validato"|"propagato";
  plant: string; corrective_action: string; created_at: string;
}

export const lessonsApi = {
  list: (params?: Record<string, string>) =>
    apiClient.get<{ results: LessonLearned[] }>("/lessons/lessons/", { params }).then(r => r.data),
  validate: (id: string) =>
    apiClient.post(`/lessons/lessons/${id}/validate/`).then(r => r.data),
  create: (data: Partial<LessonLearned>) =>
    apiClient.post<LessonLearned>("/lessons/lessons/", data).then(r => r.data),
};
