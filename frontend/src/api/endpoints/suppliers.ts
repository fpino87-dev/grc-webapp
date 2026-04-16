import { apiClient } from "../client";

export interface CpvCode {
  code: string;
  label: string;
}

export interface Supplier {
  id: string;
  name: string;
  vat_number: string;
  country: string;
  email: string;
  description: string;
  risk_level: "basso" | "medio" | "alto" | "critico";
  status: "attivo" | "sospeso" | "terminato";
  evaluation_date: string | null;
  notes: string;
  latest_questionnaire_status: "inviato" | "risposto" | "scaduto" | null;
  // Campi ACN Delibera 127434
  cpv_codes: CpvCode[];
  nis2_relevant: boolean;
  nis2_relevance_criterion: "ict" | "non_fungibile" | "entrambi" | "";
  supply_concentration_pct: string | null;
  concentration_threshold: "bassa" | "media" | "critica" | "nd";
}

export interface QuestionnaireTemplate {
  id: string;
  name: string;
  subject: string;
  body: string;
  form_url: string;
}

export interface SupplierQuestionnaire {
  id: string;
  supplier: string;
  supplier_name: string;
  template: string | null;
  subject_snapshot: string;
  body_snapshot: string;
  form_url_snapshot: string;
  sent_at: string;
  last_sent_at: string;
  sent_to: string;
  sent_by: string | null;
  sent_by_display: string | null;
  send_count: number;
  evaluation_date: string | null;
  risk_result: "basso" | "medio" | "alto" | "critico" | null;
  status: "inviato" | "risposto" | "scaduto";
  expires_at: string | null;
  notes: string;
}

export interface NdaDocument {
  id: string;
  title: string;
  status: string;
  expiry_date: string | null;
  review_due_date: string | null;
  created_at: string;
  has_file: boolean;
  latest_version: {
    file_name: string;
    file_size: number | null;
    sha256: string;
    version_number: number;
  } | null;
}

export const suppliersApi = {
  list: (params?: Record<string, string>) =>
    apiClient.get<{ results: Supplier[] }>("/suppliers/suppliers/", { params }).then(r => r.data),
  create: (data: Partial<Supplier>) =>
    apiClient.post<Supplier>("/suppliers/suppliers/", data).then(r => r.data),
  update: (id: string, data: Partial<Supplier>) =>
    apiClient.patch<Supplier>(`/suppliers/suppliers/${id}/`, data).then(r => r.data),
  delete: (id: string) =>
    apiClient.delete(`/suppliers/suppliers/${id}/`).then(r => r.data),

  // Questionnaire templates
  listTemplates: () =>
    apiClient.get<{ results: QuestionnaireTemplate[] }>("/suppliers/questionnaire-templates/").then(r => r.data.results ?? r.data),
  createTemplate: (data: Partial<QuestionnaireTemplate>) =>
    apiClient.post<QuestionnaireTemplate>("/suppliers/questionnaire-templates/", data).then(r => r.data),
  updateTemplate: (id: string, data: Partial<QuestionnaireTemplate>) =>
    apiClient.patch<QuestionnaireTemplate>(`/suppliers/questionnaire-templates/${id}/`, data).then(r => r.data),
  deleteTemplate: (id: string) =>
    apiClient.delete(`/suppliers/questionnaire-templates/${id}/`).then(r => r.data),

  // Questionnaires
  listQuestionnaires: (params?: Record<string, string>) =>
    apiClient.get<{ results: SupplierQuestionnaire[] }>("/suppliers/questionnaires/", { params }).then(r => r.data.results ?? r.data),
  sendQuestionnaire: (supplierId: string, templateId: string) =>
    apiClient.post<SupplierQuestionnaire>("/suppliers/questionnaires/send/", {
      supplier_id: supplierId,
      template_id: templateId,
    }).then(r => r.data),
  resendQuestionnaire: (id: string) =>
    apiClient.post<SupplierQuestionnaire>(`/suppliers/questionnaires/${id}/resend/`).then(r => r.data),
  evaluateQuestionnaire: (id: string, evaluation_date: string, risk_result: string, notes?: string) =>
    apiClient.post<SupplierQuestionnaire>(`/suppliers/questionnaires/${id}/evaluate/`, {
      evaluation_date, risk_result, notes: notes ?? "",
    }).then(r => r.data),

  // NDA / Contracts
  ndaList: (supplierId: string) =>
    apiClient.get<{ results: NdaDocument[]; count: number }>(`/suppliers/suppliers/${supplierId}/nda/`).then(r => r.data),
  ndaUpload: (supplierId: string, formData: FormData) =>
    apiClient.post<NdaDocument>(`/suppliers/suppliers/${supplierId}/nda/upload/`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }).then(r => r.data),

  // ACN / NIS2
  suggestCpv: (description: string) =>
    apiClient.post<{ suggestions: CpvCode[]; interaction_id: string; provider: string }>(
      "/suppliers/suppliers/suggest-cpv/",
      { description }
    ).then(r => r.data),

  exportCsv: (nis2Only: boolean) => {
    const url = `/suppliers/suppliers/export-csv/${nis2Only ? "?nis2_only=true" : ""}`;
    return apiClient.get(url, { responseType: "blob" }).then(r => {
      const blob = new Blob([r.data], { type: "text/csv;charset=utf-8;" });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = nis2Only ? "fornitori_nis2.csv" : "fornitori.csv";
      link.click();
      URL.revokeObjectURL(link.href);
    });
  },
};
