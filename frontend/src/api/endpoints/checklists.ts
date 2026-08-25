import { apiClient } from "../client";

export type ChecklistFrequency =
  | "daily"
  | "weekly"
  | "monthly"
  | "quarterly"
  | "semiannual"
  | "annual"
  | "ad_hoc";

/** Tutte le frequenze, nell'ordine in cui vanno mostrate nella UI. */
export const CHECKLIST_FREQUENCIES: ChecklistFrequency[] = [
  "daily",
  "weekly",
  "monthly",
  "quarterly",
  "semiannual",
  "annual",
  "ad_hoc",
];

/** Frequenze il cui periodo si misura in mesi: usano day_of_month (+ start_month
 *  per quelle più lunghe di un mese). */
export const MONTH_BASED_FREQUENCIES: ChecklistFrequency[] = [
  "monthly",
  "quarterly",
  "semiannual",
  "annual",
];
export type ChecklistRunStatus = "pending" | "in_progress" | "completed" | "overdue";

export type ChecklistItemType = "checkbox" | "numeric" | "text";

export interface ChecklistTemplateItem {
  /** Presente sugli item già salvati: il backend lo usa per aggiornarli in
   *  place invece di ricrearli (i run storici vi puntano). */
  id?: string;
  order: number;
  text: string;
  is_mandatory: boolean;
  item_type?: ChecklistItemType;
  unit?: string;
  numeric_min?: string | null;
  numeric_max?: string | null;
}

export interface ChecklistTemplate {
  id: string;
  name: string;
  description: string;
  frequency: ChecklistFrequency;
  /** Giorni 0=lun … 6=dom in cui generare il run.
   *  daily: tutti i giorni indicati (vuoto = tutti e 7).
   *  weekly: il primo giorno indicato (vuoto = lunedì). */
  days_of_week?: number[];
  /** Frequenze a mesi: giorno del mese 1-28, 0 = ultimo giorno del mese. */
  day_of_month?: number;
  /** Trimestrale/semestrale/annuale: mese di partenza del ciclo (1-12). */
  start_month?: number;
  plant: string | null;
  plant_name?: string | null;
  /** Categoria di impianti su cui espandere: genera una checklist per ogni
   *  impianto di quel tipo nel sito (vuoto = una sola per sito). */
  facility_category?: string;
  /** Al completamento aggiorna ultima manutenzione ed esito sull'impianto. */
  records_maintenance?: boolean;
  is_active: boolean;
  items: ChecklistTemplateItem[];
  runs_count?: number;
  created_at?: string;
  updated_at?: string;
}

export interface ChecklistRunItem {
  id: string;
  template_item: string;
  text: string;
  is_mandatory: boolean;
  order: number;
  checked: boolean;
  note: string;
  checked_at: string | null;
  checked_by: string | null;
}

export interface ChecklistRun {
  id: string;
  template: string;
  template_name: string;
  /** Impianto a cui si riferisce, per le checklist espanse per categoria. */
  asset?: string | null;
  asset_name?: string | null;
  plant: string;
  plant_name?: string;
  assigned_to: string | null;
  due_date: string;
  completed_at: string | null;
  completed_by: string | null;
  status: ChecklistRunStatus;
  items: ChecklistRunItem[];
  progress_total: number;
  progress_done: number;
  created_at: string;
}

const TPL = "/tasks/checklist-templates/";
const RUN = "/tasks/checklist-runs/";

export const checklistsApi = {
  // Template
  listTemplates: (params?: Record<string, string>) =>
    apiClient
      .get<{ results: ChecklistTemplate[]; count: number }>(TPL, { params })
      .then((r) => r.data),
  getTemplate: (id: string) =>
    apiClient.get<ChecklistTemplate>(`${TPL}${id}/`).then((r) => r.data),
  createTemplate: (data: Partial<ChecklistTemplate>) =>
    apiClient.post<ChecklistTemplate>(TPL, data).then((r) => r.data),
  updateTemplate: (id: string, data: Partial<ChecklistTemplate>) =>
    apiClient.patch<ChecklistTemplate>(`${TPL}${id}/`, data).then((r) => r.data),
  deleteTemplate: (id: string) =>
    apiClient.delete(`${TPL}${id}/`).then((r) => r.data),
  /** Avvia subito una checklist da un template: unica via per gli "ad hoc",
   *  riesecuzione fuori ciclo per gli altri. `due_date` omessa = fine del
   *  periodo corrente (oggi per gli ad hoc). */
  startRun: (id: string, data?: { plant?: string; due_date?: string }) =>
    apiClient.post<ChecklistRun>(`${TPL}${id}/start-run/`, data ?? {}).then((r) => r.data),

  // Run
  listRuns: (params?: Record<string, string>) =>
    apiClient
      .get<{ results: ChecklistRun[]; count: number }>(RUN, { params })
      .then((r) => r.data),
  getRun: (id: string) =>
    apiClient.get<ChecklistRun>(`${RUN}${id}/`).then((r) => r.data),
  completeItem: (
    runId: string,
    payload: { item_id: string; checked: boolean; note?: string }
  ) =>
    apiClient
      .post<ChecklistRun>(`${RUN}${runId}/complete-item/`, payload)
      .then((r) => r.data),
  completeRun: (runId: string) =>
    apiClient.post<ChecklistRun>(`${RUN}${runId}/complete/`, {}).then((r) => r.data),
};
