import { apiClient } from "../client";

export interface Document {
  id: string; title: string; category: string; status: string;
  plant: string | null; owner: string | null;
  review_due_date: string | null; expiry_date: string | null;
  is_mandatory: boolean; approved_at: string | null;
}

export const documentsApi = {
  list: (params?: Record<string,string>) =>
    apiClient.get<{results: Document[]}>("/documents/documents/", {params}).then(r => r.data),
  create: (data: Partial<Document>) =>
    apiClient.post<Document>("/documents/documents/", data).then(r => r.data),
  submit: (id: string) =>
    apiClient.post(`/documents/documents/${id}/submit/`).then(r => r.data),
  approve: (id: string, notes?: string) =>
    apiClient.post(`/documents/documents/${id}/approve/`, {notes}).then(r => r.data),
  reject: (id: string, notes?: string) =>
    apiClient.post(`/documents/documents/${id}/reject/`, {notes}).then(r => r.data),
  expiring: () =>
    apiClient.get<Document[]>("/documents/documents/expiring/").then(r => r.data),
};
