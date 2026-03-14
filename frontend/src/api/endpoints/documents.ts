import { apiClient } from "../client";

export interface Document {
  id: string; title: string; category: string; document_type: string; status: string;
  plant: string | null; owner: string | null;
  review_due_date: string | null; expiry_date: string | null;
  is_mandatory: boolean; approved_at: string | null;
}

export interface Evidence {
  id: string;
  title: string;
  description: string;
  evidence_type: string;
  valid_until: string | null;
  plant: string | null;
  plant_name: string | null;
  file_path: string;
  uploaded_by: string | null;
  uploaded_by_username: string | null;
  control_instances_count: number;
  created_at: string;
}

export const EVIDENCE_TYPE_LABELS: Record<string, string> = {
  screenshot: "Screenshot",
  log: "Log di sistema",
  report: "Report",
  verbale: "Verbale",
  certificato: "Certificato",
  test_result: "Risultato test",
  altro: "Altro",
};

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

  // Evidences
  evidences: (params?: Record<string,string>) =>
    apiClient.get<{results: Evidence[]}>("/documents/evidences/", {params}).then(r => r.data),
  createEvidence: (data: Partial<Evidence>) =>
    apiClient.post<Evidence>("/documents/evidences/", data).then(r => r.data),
  searchEvidences: (search: string) =>
    apiClient.get<{results: Evidence[]}>("/documents/evidences/", {params: {search}}).then(r => r.data),
};
