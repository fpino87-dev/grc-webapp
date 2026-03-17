import { apiClient } from "../client";

export interface DocumentVersionSummary {
  id: string;
  version_number: number;
  file_name: string;
  storage_path: string;
  file_url?: string | null;
}

export interface Document {
  id: string;
  title: string;
  category: string;
  document_type: string;
  status: string;
  plant: string | null;
  owner: string | null;
  review_due_date: string | null;
  expiry_date: string | null;
  is_mandatory: boolean;
  approved_at: string | null;
  latest_version?: DocumentVersionSummary | null;
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
  file_url?: string | null;
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
  update: (id: string, data: Partial<Document>) =>
    apiClient.patch<Document>(`/documents/documents/${id}/`, data).then(r => r.data),
  uploadVersion: (id: string, file: File, changeSummary?: string) => {
    const form = new FormData();
    form.append("file", file);
    if (changeSummary) form.append("change_summary", changeSummary);
    return apiClient.post(`/documents/documents/${id}/upload/`, form, {
      headers: { "Content-Type": "multipart/form-data" },
    }).then(r => r.data as DocumentVersionSummary);
  },
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
  createEvidence: (data: Partial<Evidence> & { file?: File }) => {
    const form = new FormData();
    if (data.file) form.append("file", data.file);
    if (data.title) form.append("title", data.title);
    if (data.evidence_type) form.append("evidence_type", data.evidence_type);
    if (data.valid_until) form.append("valid_until", data.valid_until);
    if (data.description) form.append("description", data.description);
    if (data.plant) form.append("plant", data.plant as string);
    return apiClient.post<Evidence>("/documents/evidences/", form, {
      headers: { "Content-Type": "multipart/form-data" },
    }).then(r => r.data);
  },
  searchEvidences: (search: string) =>
    apiClient.get<{results: Evidence[]}>("/documents/evidences/", {params: {search}}).then(r => r.data),
  linkControls: (docId: string, controlInstanceIds: string[]) =>
    apiClient.post(`/documents/documents/${docId}/link-controls/`, { control_instance_ids: controlInstanceIds }).then(r => r.data),
  searchDocuments: (search: string, plant?: string) =>
    apiClient.get<{results: Document[]}>("/documents/documents/", {params: {search, ...(plant ? {plant} : {})}}).then(r => r.data),
};
