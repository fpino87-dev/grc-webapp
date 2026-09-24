import { apiClient } from "../client";
import { fetchAllPages } from "../pagination";

/** Traiettoria: non è lo stato del record, è la lettura dell'andamento
 *  rispetto al target e alla scadenza. Un obiettivo può essere "attivo"
 *  (stato) e "a_rischio" (traiettoria) allo stesso tempo. */
export type ObjectiveTrack =
  | "in_linea"
  | "a_rischio"
  | "mancato"
  | "senza_misure"
  | "non_applicabile";

export type ObjectiveStatus =
  | "bozza"
  | "attivo"
  | "raggiunto"
  | "non_raggiunto"
  | "sospeso"
  | "annullato";

export type ObjectiveOrigin =
  | "politica"
  | "risk_assessment"
  | "audit"
  | "requisito"
  | "incidente"
  | "riesame"
  | "altro";

export type MeasureSource = "kpi" | "manual";

export interface ObjectiveEvaluation {
  current_value: number | null;
  measured_on: string | null;
  unit: string;
  progress_pct: number | null;
  elapsed_pct: number | null;
  reached: boolean;
  track: ObjectiveTrack;
  days_to_target: number;
  /** Target che non supera la soglia di warning del KPI: non aggiunge nulla
   *  a ciò che il KPI già segnala ogni settimana. */
  weak_target: boolean;
}

export interface SecurityObjective {
  id: string;
  plant: string | null;
  plant_code: string | null;
  code: string;
  title: string;
  description: string;
  origin: ObjectiveOrigin;
  source_review_id: string | null;
  measure_source: MeasureSource;
  kpi_definition: string | null;
  kpi_code: string | null;
  unit: string;
  start_date: string;
  baseline_value: number | null;
  target_value: number;
  target_direction: "above" | "below";
  target_date: string;
  owner_role: string;
  resources: string;
  evaluation_method: string;
  status: ObjectiveStatus;
  communicated_at: string | null;
  closed_at: string | null;
  closure_note: string;
  evaluation: ObjectiveEvaluation;
}

export interface ObjectiveSeriesPoint {
  date: string;
  value: number;
}

export interface ObjectivesOverview {
  totale: number;
  per_stato: Record<string, number>;
  per_traiettoria: Record<string, number>;
}

const BASE = "/governance/security-objectives/";

export const securityObjectivesApi = {
  list: (params?: Record<string, string>) =>
    fetchAllPages<SecurityObjective>(BASE, params),
  get: (id: string) => apiClient.get<SecurityObjective>(`${BASE}${id}/`).then((r) => r.data),
  create: (data: Partial<SecurityObjective>) =>
    apiClient.post<SecurityObjective>(BASE, data).then((r) => r.data),
  update: (id: string, data: Partial<SecurityObjective>) =>
    apiClient.patch<SecurityObjective>(`${BASE}${id}/`, data).then((r) => r.data),
  remove: (id: string) => apiClient.delete(`${BASE}${id}/`).then((r) => r.data),

  activate: (id: string) =>
    apiClient.post<SecurityObjective>(`${BASE}${id}/activate/`).then((r) => r.data),
  suspend: (id: string, note?: string) =>
    apiClient.post<SecurityObjective>(`${BASE}${id}/suspend/`, { note }).then((r) => r.data),
  close: (id: string, outcome: "raggiunto" | "non_raggiunto" | "annullato", note?: string) =>
    apiClient.post<SecurityObjective>(`${BASE}${id}/close/`, { outcome, note }).then((r) => r.data),
  /** Solo per gli obiettivi a misura manuale: su quelli agganciati a un KPI
   *  il valore si registra sul KPI, per non avere due verità sullo stesso numero. */
  measure: (id: string, value: number, measured_on?: string, note?: string) =>
    apiClient.post(`${BASE}${id}/measure/`, { value, measured_on, note }).then((r) => r.data),
  series: (id: string) =>
    apiClient.get<{ items: ObjectiveSeriesPoint[] }>(`${BASE}${id}/series/`).then((r) => r.data.items),
  overview: (params?: Record<string, string>) =>
    apiClient.get<ObjectivesOverview>(`${BASE}overview/`, { params }).then((r) => r.data),
};
