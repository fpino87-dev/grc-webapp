import { apiClient } from "../client";

export interface Supplier {
  id: string;
  name: string;
  vat_number: string;
  country: string;
  email: string;
  risk_level: "basso" | "medio" | "alto" | "critico";
  status: "attivo" | "sospeso" | "terminato";
  evaluation_date: string | null;
  notes: string;
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
};
