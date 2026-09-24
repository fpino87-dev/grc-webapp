import { apiClient } from "../client";
import { fetchAllPages } from "../pagination";

export interface DocumentVersionSummary {
  id: string;
  version_number: number;
  /** Revisione come sul frontespizio del documento: "Rev. 03", "2.1", … */
  version_label?: string;
  /** version_label se indicata, altrimenti il contatore interno ("v2"). */
  version_display?: string;
  file_name: string;
  storage_path: string;
  file_url?: string | null;
}

// Approvazione in applicazione oppure delibera dell'organo di governo
// (il verbale firmato della seduta resta l'evidenza).
export interface ApproveDocumentPayload {
  notes?: string;
  mode?: "in_app" | "delibera";
  resolution_ref?: string;
  resolution_date?: string;
  governing_body?: string | null;
  review_id?: string | null;
}

export interface DocumentApprovalInfo {
  mode: "in_app" | "delibera";
  /** Versione del file effettivamente approvata (null sulle approvazioni storiche). */
  version: { id: string; version_number: number; version_label: string; version_display: string } | null;
  resolution_ref: string;
  resolution_date: string | null;
  governing_body: string | null;
  review_id: string | null;
  actor: string | null;
  recorded_at: string;
}

export interface Document {
  id: string;
  document_code: string;
  title: string;
  category: string;
  document_type: string;
  status: string;
  plant: string | null;
  plant_name?: string | null;
  plant_code?: string | null;
  shared_plants?: string[];
  shared_plant_names?: Array<{ id: string; name: string; code: string }>;
  is_shared_with_current?: boolean;
  owner: string | null;
  supplier: string | null;
  supplier_name?: string | null;
  review_due_date: string | null;
  expiry_date: string | null;
  is_mandatory: boolean;
  approved_at: string | null;
  last_approval?: DocumentApprovalInfo | null;
  /** In vigore, ma con una versione caricata dopo quella approvata. */
  has_unapproved_version?: boolean;
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
  linked_controls?: Array<{
    id: string;
    control_external_id: string;
    control_title: string;
    framework_code: string;
  }>;
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
    fetchAllPages<Document>("/documents/documents/", params).then((results) => ({ results, count: results.length })),
  create: (data: Partial<Document>) =>
    apiClient.post<Document>("/documents/documents/", data).then(r => r.data),
  update: (id: string, data: Partial<Document>) =>
    apiClient.patch<Document>(`/documents/documents/${id}/`, data).then(r => r.data),
  uploadVersion: (id: string, file: File, changeSummary?: string, versionLabel?: string) => {
    const form = new FormData();
    form.append("file", file);
    if (changeSummary) form.append("change_summary", changeSummary);
    if (versionLabel) form.append("version_label", versionLabel);
    return apiClient.post(`/documents/documents/${id}/upload/`, form, {
      headers: { "Content-Type": "multipart/form-data" },
    }).then(r => r.data as DocumentVersionSummary);
  },
  submit: (id: string) =>
    apiClient.post(`/documents/documents/${id}/submit/`).then(r => r.data),
  approve: (id: string, data?: ApproveDocumentPayload) =>
    apiClient.post(`/documents/documents/${id}/approve/`, data ?? {}).then(r => r.data),
  reject: (id: string, notes?: string) =>
    apiClient.post(`/documents/documents/${id}/reject/`, {notes}).then(r => r.data),
  expiring: () =>
    apiClient.get<Document[]>("/documents/documents/expiring/").then(r => r.data),

  downloadDocument: (id: string) =>
    apiClient.get<Blob>(`/documents/documents/${id}/download-latest/`, {
      responseType: "blob",
    }).then(r => r.data),

  // Evidences
  evidences: (params?: Record<string,string>) =>
    fetchAllPages<Evidence>("/documents/evidences/", params).then((results) => ({ results, count: results.length })),
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
    fetchAllPages<Evidence>("/documents/evidences/", {search}).then((results) => ({ results, count: results.length })),
  linkControls: (docId: string, controlInstanceIds: string[]) =>
    apiClient.post(`/documents/documents/${docId}/link-controls/`, { control_instance_ids: controlInstanceIds }).then(r => r.data),
  searchDocuments: (search: string, plant?: string) =>
    fetchAllPages<Document>("/documents/documents/", {search, ...(plant ? {plant} : {})}).then((results) => ({ results, count: results.length })),

  downloadEvidence: (id: string) =>
    apiClient.get<Blob>(`/documents/evidences/${id}/download/`, {
      responseType: "blob",
    }).then(r => r.data),

  shareDocument: (id: string, plantIds: string[]) =>
    apiClient.post<{ shared_with: Array<{ id: string; name: string; code: string }> }>(
      `/documents/documents/${id}/share/`, { plant_ids: plantIds }
    ).then(r => r.data),

  remove: (id: string) => apiClient.delete(`/documents/documents/${id}/`),
  removeEvidence: (id: string) => apiClient.delete(`/documents/evidences/${id}/`),
};
