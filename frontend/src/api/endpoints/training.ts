import { apiClient } from "../client";

export interface TrainingCourse {
  id: string; title: string; source: "interno"|"kb4"|"esterno";
  status: "attivo"|"archiviato"; mandatory: boolean;
  duration_minutes: number | null; deadline: string | null;
  description: string;
}

export interface TrainingEnrollment {
  id: string; course: string; user: string;
  status: "assegnato"|"in_corso"|"completato"|"scaduto";
  completed_at: string | null; score: number | null; passed: boolean | null;
}

export const trainingApi = {
  courses: () => apiClient.get<{ results: TrainingCourse[] }>("/training/courses/").then(r => r.data.results),
  enrollments: (params?: Record<string, string>) =>
    apiClient.get<{ results: TrainingEnrollment[] }>("/training/enrollments/", { params }).then(r => r.data.results),
  createCourse: (data: Partial<TrainingCourse>) =>
    apiClient.post<TrainingCourse>("/training/courses/", data).then(r => r.data),
  updateCourse: (id: string, data: Partial<TrainingCourse>) =>
    apiClient.patch<TrainingCourse>(`/training/courses/${id}/`, data).then(r => r.data),
  deleteCourse: (id: string) =>
    apiClient.delete(`/training/courses/${id}/`),
};
