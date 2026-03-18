import { apiClient } from "../client";

export interface RiskMitigationPlan {
  id: string;
  assessment: string;
  action: string;
  owner: string | null;
  due_date: string;
  completed_at: string | null;
}

export interface RiskAssessment {
  id: string;
  plant: string;
  plant_name: string;
  asset: string | null;
  asset_name: string | null;
  name: string;
  threat_category: string;
  assessment_type: "IT" | "OT";
  probability: number | null;
  impact: number | null;
  inherent_probability: number | null;
  inherent_impact: number | null;
  inherent_score: number | null;
  inherent_risk_level: "verde" | "giallo" | "rosso" | null;
  treatment: string;
  status: "bozza" | "completato" | "archiviato";
  score: number | null;
  risk_level: "verde" | "giallo" | "rosso" | null;
  risk_reduction_pct: number | null;
  ale_annuo: string | null;
  ale_calcolato: string | null;
  weighted_score: number | null;
  owner: string | null;
  owner_name: string | null;
  critical_process: string | null;
  critical_process_name: string | null;
  risk_accepted: boolean;
  risk_accepted_formally: boolean;
  risk_accepted_by: string | null;
  accepted_by_name: string | null;
  risk_accepted_at: string | null;
  risk_acceptance_note: string;
  risk_acceptance_expiry: string | null;
  assessed_at: string | null;
  plan_due_date: string | null;
  needs_revaluation: boolean;
  needs_revaluation_since: string | null;
}

export interface SuggestResidualResult {
  suggested: number | null;
  reduction_pct?: number;
  compliant_controls?: number;
  reason: string;
}

export interface RiskContext {
  risk: Record<string, unknown>;
  bia: Record<string, unknown> | null;
  bcp_plans: Array<Record<string, unknown>>;
  bcp_summary: {
    has_bcp_covering_process: boolean;
    best_rto_vs_mtpd_status: string;
  } | null;
}

export const THREAT_CATEGORIES = [
  { value: "accesso_non_autorizzato", label: "Accesso non autorizzato" },
  { value: "malware_ransomware",      label: "Malware / Ransomware" },
  { value: "data_breach",             label: "Data breach / Fuga di dati" },
  { value: "phishing_social",         label: "Phishing / Social engineering" },
  { value: "guasto_hw_sw",            label: "Guasto hardware / software" },
  { value: "disastro_naturale",       label: "Disastro naturale / ambientale" },
  { value: "errore_umano",            label: "Errore umano" },
  { value: "attacco_supply_chain",    label: "Attacco supply chain" },
  { value: "ddos",                    label: "DoS / DDoS" },
  { value: "insider_threat",          label: "Insider threat" },
  { value: "furto_perdita",           label: "Furto / perdita dispositivi" },
  { value: "altro",                   label: "Altro" },
];

export const PROB_LABELS: Record<number, string> = {
  1: "1 – Molto bassa", 2: "2 – Bassa", 3: "3 – Media", 4: "4 – Alta", 5: "5 – Molto alta",
};
export const IMPACT_LABELS: Record<number, string> = {
  1: "1 – Trascurabile", 2: "2 – Minore", 3: "3 – Moderato", 4: "4 – Grave", 5: "5 – Critico",
};

export const riskApi = {
  list: (params?: Record<string, string>) =>
    apiClient.get<{ results: RiskAssessment[] }>("/risk/assessments/", { params }).then(r => r.data),
  create: (data: Partial<RiskAssessment>) =>
    apiClient.post<RiskAssessment>("/risk/assessments/", data).then(r => r.data),
  update: (id: string, data: Partial<RiskAssessment>) =>
    apiClient.patch<RiskAssessment>(`/risk/assessments/${id}/`, data).then(r => r.data),
  complete: (id: string) =>
    apiClient.post(`/risk/assessments/${id}/complete/`).then(r => r.data),
  accept: (id: string) =>
    apiClient.post(`/risk/assessments/${id}/accept/`).then(r => r.data),
  mitigationPlans: (assessmentId: string) =>
    apiClient.get<{ results: RiskMitigationPlan[] }>("/risk/mitigation-plans/", { params: { assessment: assessmentId, page_size: "100" } }).then(r => r.data.results),
  createPlan: (data: Partial<RiskMitigationPlan>) =>
    apiClient.post<RiskMitigationPlan>("/risk/mitigation-plans/", data).then(r => r.data),
  completePlan: (id: string) =>
    apiClient.patch<RiskMitigationPlan>(`/risk/mitigation-plans/${id}/`, { completed_at: new Date().toISOString() }).then(r => r.data),
  suggestResidual: (id: string) =>
    apiClient.get<SuggestResidualResult>(`/risk/assessments/${id}/suggest-residual/`).then(r => r.data),
  acceptRisk: (id: string, note: string, expiryDate?: string) =>
    apiClient.post(`/risk/assessments/${id}/accept-risk/`, { note, expiry_date: expiryDate }).then(r => r.data),
  context: (id: string) =>
    apiClient.get<RiskContext>(`/risk/assessments/${id}/context/`).then(r => r.data),
};
