import { apiClient } from "../client";
import { fetchAllPages } from "../pagination";

// Formazione a evidenze: la piattaforma non eroga la formazione, la governa.
// Piano → erogazioni con file di prova → evidenze sui controlli → KPI.
// Personale: solo conteggi per gruppo, nessun dato personale dei dipendenti.
// Ruoli critici e organo di gestione: partecipanti per nome, scelti fra i
// titolari di nomine e i componenti degli organi di governo.


export type CourseKind = "corso" | "awareness" | "phishing";
export type AudienceKind = "generale" | "ruoli_critici" | "organo_gestione";
export type ItemState = "fatto" | "in_ritardo" | "in_scadenza" | "pianificato";

export interface ControlOption {
  id: string;
  external_id: string;
  framework_code: string;
  title: string;
}

export interface TrainingCourse {
  id: string;
  title: string;
  description: string;
  source: "interno" | "kb4" | "esterno";
  status: "attivo" | "archiviato";
  kind: CourseKind;
  audience_kind: AudienceKind;
  mandatory: boolean;
  duration_minutes: number | null;
  validity_months: number | null;
  // Ambito: nessun sito = corso di organizzazione, valido per tutti i siti.
  plants: string[];
  plant_codes: string[];
  competency: string;
  competency_level: 1 | 2 | 3;
}

export const courseAppliesTo = (c: Pick<TrainingCourse, "plants">, plantId: string | null) =>
  c.plants.length === 0 || (plantId !== null && c.plants.includes(plantId));

// Impostazione unica del modulo: quali controlli prova un'erogazione, in base
// ai destinatari del corso. La prova va solo sui framework applicati al sito.
export interface EvidenceControl {
  id: string;
  audience_kind: AudienceKind;
  control: string;
  control_detail: ControlOption;
}

export const isNamedCourse = (c: Pick<TrainingCourse, "kind" | "audience_kind">) =>
  c.audience_kind !== "generale" && c.kind !== "phishing";

export interface TrainingCapabilities {
  can_read_records: boolean;
  can_manage_courses: boolean;
  can_manage_org: boolean;
  manage_plant_ids: string[];
}

export interface TrainingAudience {
  id: string;
  plant: string;
  plant_code: string;
  name: string;
  headcount: number;
  headcount_updated_at: string;
  notes: string;
}

export interface TrainingPlan {
  id: string;
  plant: string | null;
  plant_code: string | null;
  year: number;
  document: string | null;
  document_title: string | null;
  document_status: string | null;
  notes: string;
}

export interface TrainingPlanItem {
  id: string;
  plan: string;
  course: string;
  course_title: string;
  audiences: string[];
  due_date: string;
  notes: string;
}

export interface PlanStatus {
  plan_id: string;
  year: number;
  counts: Record<ItemState, number>;
  items: {
    item_id: string;
    course_id: string;
    course_title: string;
    due_date: string;
    state: ItemState;
    sessions: number;
    target_count: number | null;
    trained_count: number;
    coverage_pct: number | null;
  }[];
}

export interface TrainingSession {
  id: string;
  course: string;
  course_title: string;
  course_kind: CourseKind;
  plan_item: string | null;
  plant: string | null;
  plant_code: string | null;
  held_on: string;
  audiences: string[];
  target_count: number | null;
  trained_count: number | null;
  sent_count: number | null;
  clicked_count: number | null;
  reported_count: number | null;
  evidence: string | null;
  evidence_valid_until: string | null;
  evidence_file_path: string | null;
  legacy: boolean;
  notes: string;
  participants_detail: SessionParticipant[];
}

export interface SessionParticipant {
  id: string;
  name: string;
  roles: string[];
  committee: string | null;
  user_id: string | null;
  member_id: string | null;
}

export interface ParticipantOptions {
  role_holders: { user_id: string; name: string; roles: string[] }[];
  members: {
    member_id: string;
    name: string;
    position: string;
    committee: string;
    management_body: boolean;
    user_id: string | null;
  }[];
}

export interface BoardStatus {
  total: number;
  trained: number;
  pct: number | null;
  members: {
    member_id: string;
    full_name: string;
    position: string;
    committee: string;
    trained: boolean;
    valid_until: string | null;
  }[];
}

export interface SessionCreated extends TrainingSession {
  control_links: { linked: number; not_applicable: string[] };
}

const BASE = "/training";
const list = <T,>(url: string, params?: Record<string, string>) => fetchAllPages<T>(url, params);

export const trainingApi = {
  capabilities: () =>
    apiClient.get<TrainingCapabilities>(`${BASE}/courses/capabilities/`).then(r => r.data),

  // Catalogo corsi
  courses: (params?: Record<string, string>) => list<TrainingCourse>(`${BASE}/courses/`, params),
  controlOptions: (search: string) =>
    apiClient.get<ControlOption[]>(`${BASE}/courses/control-options/`, { params: { search } })
      .then(r => r.data),
  competencyOptions: () =>
    apiClient.get<string[]>(`${BASE}/courses/competency-options/`).then(r => r.data),
  evidenceControls: () => list<EvidenceControl>(`${BASE}/evidence-controls/`),
  createEvidenceControl: (audience_kind: AudienceKind, control: string) =>
    apiClient.post<EvidenceControl>(`${BASE}/evidence-controls/`, { audience_kind, control })
      .then(r => r.data),
  deleteEvidenceControl: (id: string) => apiClient.delete(`${BASE}/evidence-controls/${id}/`),
  createCourse: (data: Partial<TrainingCourse>) =>
    apiClient.post<TrainingCourse>(`${BASE}/courses/`, data).then(r => r.data),
  updateCourse: (id: string, data: Partial<TrainingCourse>) =>
    apiClient.patch<TrainingCourse>(`${BASE}/courses/${id}/`, data).then(r => r.data),
  deleteCourse: (id: string) => apiClient.delete(`${BASE}/courses/${id}/`),

  // Gruppi destinatari (per sito, solo numeri)
  audiences: (params?: Record<string, string>) =>
    list<TrainingAudience>(`${BASE}/audiences/`, params),
  createAudience: (data: Partial<TrainingAudience>) =>
    apiClient.post<TrainingAudience>(`${BASE}/audiences/`, data).then(r => r.data),
  updateAudience: (id: string, data: Partial<TrainingAudience>) =>
    apiClient.patch<TrainingAudience>(`${BASE}/audiences/${id}/`, data).then(r => r.data),
  deleteAudience: (id: string) => apiClient.delete(`${BASE}/audiences/${id}/`),

  // Piano formativo
  plans: (params?: Record<string, string>) => list<TrainingPlan>(`${BASE}/plans/`, params),
  planStatus: (id: string) =>
    apiClient.get<PlanStatus>(`${BASE}/plans/${id}/status/`).then(r => r.data),
  createPlan: (data: Partial<TrainingPlan>) =>
    apiClient.post<TrainingPlan>(`${BASE}/plans/`, data).then(r => r.data),
  updatePlan: (id: string, data: Partial<TrainingPlan>) =>
    apiClient.patch<TrainingPlan>(`${BASE}/plans/${id}/`, data).then(r => r.data),
  deletePlan: (id: string) => apiClient.delete(`${BASE}/plans/${id}/`),
  planItems: (params?: Record<string, string>) =>
    list<TrainingPlanItem>(`${BASE}/plan-items/`, params),
  createPlanItem: (data: Partial<TrainingPlanItem>) =>
    apiClient.post<TrainingPlanItem>(`${BASE}/plan-items/`, data).then(r => r.data),
  updatePlanItem: (id: string, data: Partial<TrainingPlanItem>) =>
    apiClient.patch<TrainingPlanItem>(`${BASE}/plan-items/${id}/`, data).then(r => r.data),
  deletePlanItem: (id: string) => apiClient.delete(`${BASE}/plan-items/${id}/`),

  // Erogazioni: il file di prova è obbligatorio e diventa l'evidenza
  sessions: (params?: Record<string, string>) =>
    list<TrainingSession>(`${BASE}/sessions/`, params),
  registerSession: (form: FormData) =>
    apiClient.post<SessionCreated>(`${BASE}/sessions/`, form, {
      headers: { "Content-Type": "multipart/form-data" },
    }).then(r => r.data),
  updateSession: (id: string, data: Partial<TrainingSession>) =>
    apiClient.patch<TrainingSession>(`${BASE}/sessions/${id}/`, data).then(r => r.data),
  deleteSession: (id: string) => apiClient.delete(`${BASE}/sessions/${id}/`),
  participantOptions: (plant: string, heldOn: string) =>
    apiClient.get<ParticipantOptions>(`${BASE}/sessions/participant-options/`, {
      params: { plant, held_on: heldOn },
    }).then(r => r.data),
  boardStatus: (plant: string) =>
    apiClient.get<BoardStatus>(`${BASE}/sessions/board-status/`, { params: { plant } })
      .then(r => r.data),
};
