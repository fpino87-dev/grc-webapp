import { apiClient } from "../client";
import { fetchAllPages } from "../pagination";
import type { RiskClass } from "../../modules/risk/riskClasses";

// ── Tipi ──────────────────────────────────────────────────────────────────────

export type AssetType = "IT" | "OT" | "SEDE" | "PERSONALE" | "FORNITORI" | "PROTOTIPI";
export const ASSET_TYPES: AssetType[] = ["IT", "OT", "SEDE", "PERSONALE", "FORNITORI", "PROTOTIPI"];
export type Treatment = "" | "mitigare" | "accettare" | "trasferire" | "evitare";
export type ImpactDimension = "economic" | "legal" | "customer" | "reputational" | "people" | "operational";
export const IMPACT_DIMENSIONS: ImpactDimension[] = [
  "economic", "legal", "customer", "reputational", "people", "operational",
];

export interface TreatmentRule { rule: "mandatory" | "evaluate" | "acceptable"; months: number }

export interface ActiveAcceptance {
  id: string;
  status: "pending" | "active";
  risk_class: RiskClass;
  expires_on: string;
  upper_opinion: string;
}

export interface Risk {
  id: string;
  plant: string | null;
  plant_name: string | null;
  cycle: string | null;
  evaluated_in_cycle: string | null;
  is_legacy: boolean;
  is_inherited: boolean;
  affected_plants: string[];
  name: string;
  /** Nome da mostrare: `name` o il titolo della minaccia nella lingua di chi guarda. */
  display_name: string;
  status: "bozza" | "completato" | "archiviato";
  asset_type: AssetType | "";
  asset: string | null;
  asset_name: string | null;
  asset_group_label: string;
  supplier: string | null;
  supplier_name: string | null;
  threat: string | null;
  threat_code: string | null;
  threat_title: string | null;
  information_classes: string[];
  business_objectives: string[];
  /** Obiettivi di sicurezza §6.2 che trattano il rischio (solo nella scheda). */
  security_objectives_summary: SecurityObjectiveLink[] | null;
  critical_process: string | null;
  critical_process_name: string | null;
  vulnerability: string;
  consequence: string;
  applicable: boolean;
  not_applicable_reason: string;
  probability: number | null;
  probability_method: "" | "frequenza" | "fer";
  probability_rationale: string;
  impact_economic: number | null;
  impact_legal: number | null;
  impact_customer: number | null;
  impact_reputational: number | null;
  impact_people: number | null;
  impact_operational: number | null;
  impact: number | null;
  impact_rationale: string;
  matrix_class: RiskClass | "";
  current_class: RiskClass | "";
  legal_or_contract_violation: boolean;
  treatment: Treatment;
  treatment_rationale: string;
  treatment_rule: TreatmentRule | null;
  expected_probability: number | null;
  expected_impact: number | null;
  expected_class: RiskClass | "";
  can_apply_expected: boolean;
  owner: number | null;
  owner_name: string | null;
  treatment_owner: number | null;
  treatment_owner_external: string;
  treatment_owner_name: string | null;
  plan_due_date: string | null;
  nis2_in_scope: boolean;
  nis2_art21_category: string;
  impacted_systems: string;
  significant_incident_potential: boolean;
  significant_incident_note: string;
  assessed_by: number | null;
  assessed_by_name: string | null;
  assessed_at: string | null;
  mitigation_plans_count: number;
  mitigation_plans_completed: number;
  mitigation_plans_verified: number;
  active_acceptance: ActiveAcceptance | null;
  legacy_snapshot: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

/** Campi scrivibili della valutazione (le regole stanno nel backend). */
export type RiskInput = Partial<Pick<Risk,
  | "name" | "asset_type" | "asset" | "asset_group_label" | "supplier" | "threat" | "information_classes"
  | "business_objectives"
  | "critical_process" | "vulnerability" | "consequence" | "probability" | "probability_method"
  | "probability_rationale" | "impact_economic" | "impact_legal" | "impact_customer" | "impact_reputational"
  | "impact_people" | "impact_operational" | "impact_rationale"
  | "legal_or_contract_violation" | "treatment" | "treatment_rationale" | "expected_probability"
  | "expected_impact" | "owner" | "treatment_owner" | "treatment_owner_external" | "plan_due_date"
  | "nis2_in_scope" | "nis2_art21_category" | "impacted_systems" | "significant_incident_potential"
  | "significant_incident_note" | "affected_plants"
>> & { plant?: string | null };

export interface ExistingMeasure {
  id: string;
  risk: string;
  control_instance: string | null;
  control_title: string | null;
  description: string;
  effectiveness: "alta" | "media" | "bassa";
  created_at: string;
}

export interface MitigationPlan {
  id: string;
  assessment: string;
  action: string;
  owner: number | null;
  owner_external: string;
  owner_name: string | null;
  due_date: string;
  expected_effect: "" | "probabilita" | "impatto" | "entrambi";
  bcp_plan: string | null;
  bcp_plan_title: string | null;
  bcp_plan_status: string | null;
  control_instance: string | null;
  control_title: string | null;
  completed_at: string | null;
  verified_at: string | null;
  verified_by: number | null;
  verified_by_name: string | null;
  verification_note: string;
  escalation_level: number;
  created_at: string;
}

export interface Acceptance {
  id: string;
  risk: string;
  risk_name: string;
  plant: string | null;
  risk_class: RiskClass;
  status: "pending" | "active" | "rejected" | "revoked" | "expired";
  required_roles: string[];
  signatures_display: { role: string; user: string | null; at: string }[];
  requires_body: boolean;
  body: string | null;
  body_name: string | null;
  body_resolution_ref: string;
  rationale: string;
  expires_on: string;
  upper_opinion: "not_required" | "pending" | "favorable" | "unfavorable";
  opinion_by_name: string | null;
  opinion_at: string | null;
  opinion_note: string;
  activated_at: string | null;
  closed_at: string | null;
  close_reason: string;
  can_sign: boolean;
  can_give_opinion: boolean;
  created_at: string;
}

export interface AcceptanceRequirements {
  class: RiskClass;
  roles: string[];
  scope: "plant" | "org";
  requires_body: boolean;
  notify: string[];
  upper_opinion: "none" | "notify" | "binding";
  max_months: number;
  not_acceptable: boolean;
  /** Plant Manager aggiunto perché chi ha valutato e tratta il rischio lo accetterebbe da solo (§10). */
  added_for_self_management: boolean;
}

export interface LocalImpactReport {
  id: string;
  risk: string;
  risk_name: string;
  plant: string;
  plant_name: string;
  local_impact: number;
  note: string;
  status: "aperta" | "recepita";
  acknowledged_at: string | null;
  created_at: string;
}

export interface ThreatEntry {
  id: string;
  code: string;
  title: string;
  asset_types: AssetType[];
  cia: ("C" | "I" | "A")[];
  translations: Record<string, { title?: string; description?: string }>;
  source: "catalog" | "custom";
  catalog_version: string;
  active: boolean;
}

export type ProtectionLevel = "low" | "normal" | "high" | "very_high";

/** Obiettivo aziendale (procedura §2): il punto di partenza della valutazione. */
export interface BusinessObjective {
  id: string;
  plant: string | null;
  plant_name: string | null;
  code: string;
  name: string;
  description: string;
  impact_dimensions: ImpactDimension[];
  order: number;
  active: boolean;
}

export interface SecurityObjectiveLink {
  id: string;
  code: string;
  title: string;
  status: string;
  target_date: string;
  track: string;
}

export interface ObjectiveRow {
  objective: { id: string; code: string; name: string; impact_dimensions: ImpactDimension[] } | null;
  count: number;
  worst_class: RiskClass | "";
  by_class: Record<RiskClass, number>;
  untreated_high: number;
  risk_ids: string[];
  /** Rischi di gruppo ereditati dal sito per questo obiettivo: a parte, non sommati. */
  inherited_count: number;
  inherited_untreated_high: number;
  inherited_risk_ids: string[];
}

export interface InformationCoverageRow {
  id: string;
  name: string;
  confidentiality: ProtectionLevel;
  plant: string | null;
  state: "evaluated" | "draft" | "missing";
  worst_class: RiskClass | "";
  risk_ids: string[];
}

export interface InformationClass {
  id: string;
  plant: string | null;
  plant_name: string | null;
  name: string;
  description: string;
  owner: number | null;
  owner_name: string | null;
  owner_role: string;
  confidentiality: ProtectionLevel;
  integrity: ProtectionLevel;
  availability: ProtectionLevel;
  critical_processes: string[];
}

export interface AcceptanceRule { roles: string[]; scope: "plant" | "org"; requires_body: boolean; notify?: string[] }

export interface ResolvedPolicy {
  preset: "centralizzato" | "federato" | "sito_singolo";
  configured: boolean;
  group_register_enabled: boolean;
  acceptance_matrix: Record<RiskClass, AcceptanceRule>;
  upper_opinion: Record<RiskClass, "none" | "notify" | "binding">;
  acceptance_max_months: Record<RiskClass, number>;
  economic_thresholds: Record<"2" | "3" | "4" | "5", number>;
  overdue_escalation_days: number;
  review_frequency_months: number;
  org_policy_id: string | null;
  plant_policy_id: string | null;
  /** Scadenza delle misure per classe (mesi), fissa nella procedura. */
  treatment_months: Record<RiskClass, number>;
  /** L'utente ha scope di organizzazione (governo del rischio, registro di gruppo). */
  user_org_scope: boolean;
}

// ── Supporto IA (M20): proposte da confermare, mai applicate dal server ──
export interface AiMeta { provider: string; model: string; used_fallback: boolean; interaction_id: string | null }
export type AiDraftProposal = Partial<Pick<Risk,
  | "vulnerability" | "consequence" | "probability" | "probability_method" | "probability_rationale"
  | "impact_economic" | "impact_legal" | "impact_customer" | "impact_reputational" | "impact_people"
  | "impact_operational" | "impact_rationale" | "treatment" | "treatment_rationale"
  | "expected_probability" | "expected_impact" | "business_objectives" | "information_classes" | "critical_process">>;
/** id → nome dei riferimenti che una proposta IA può indicare. */
export interface AiLinkNames {
  processes: Record<string, string>; objectives: Record<string, string>; information: Record<string, string>;
}
export interface AiMeasure {
  action: string; expected_effect: "" | "probabilita" | "impatto" | "entrambi"; due_date: string;
  control_instance: string | null; control_label: string | null; rationale: string;
}
/** Proposta di identificazione per una minaccia scoperta (copertura §6.5). */
export interface AiIdentifyItem {
  threat_id: string; threat_code: string; applicable: boolean; reason: string;
  proposal?: AiDraftProposal; critical_process?: string | null; business_objectives?: string[];
  information_classes?: string[];
}
export interface AiIdentifyResult extends AiMeta {
  items: AiIdentifyItem[]; remaining: number;
  names?: AiLinkNames;
}
export interface ConsistencyFinding {
  code: string; severity: "error" | "warning"; risk_id: string; risk_name: string; params: Record<string, string | number>;
}
export interface AiReviewFinding { risk_id: string; risk_name: string; issue: string; suggestion: string }
export interface RegisterReview { checks: ConsistencyFinding[]; ai: (AiMeta & { findings: AiReviewFinding[] }) | null }

export type AttentionKey = "critical_untreated" | "high_untreated" | "acceptances_expiring" | "overdue_measures";
export const ATTENTION_KEYS: AttentionKey[] = ["critical_untreated", "high_untreated", "acceptances_expiring", "overdue_measures"];
/** Cosa richiede di agire nel registro (backend: risk.services.register_attention). */
export type Attention = Record<AttentionKey, { count: number; risk_ids: string[]; measures?: number }> & {
  /** Rischi di gruppo che riguardano il sito: a parte, non sommati (null per il registro di gruppo). */
  inherited: { count: number; untreated_high: number; risk_ids: string[] } | null;
};

export type CycleKind = "primo" | "periodico" | "straordinario" | "legacy";
export type CycleStatus = "in_corso" | "in_approvazione" | "approvato" | "archiviato";

export interface Cycle {
  id: string;
  plant: string | null;
  plant_name: string | null;
  kind: CycleKind;
  trigger_reason: string;
  status: CycleStatus;
  started_at: string;
  closed_at: string | null;
  approved_by_body: string | null;
  approved_by_body_name: string | null;
  approval_review: string | null;
  approved_at: string | null;
  local_adoption_ref: string;
  risks_count: number;
}

export interface CoveragePair {
  asset_type: AssetType;
  threat_id: string;
  threat_code: string;
  /** `inherited` = coperta da un rischio di gruppo ereditato dal sito. */
  state: "missing" | "draft" | "evaluated" | "not_applicable" | "inherited";
  risk_ids: string[];
  worst_class: RiskClass | "";
}

export interface Coverage {
  asset_types: AssetType[];
  pairs: CoveragePair[];
  total: number;
  closed: number;
  missing: number;
  pct: number;
}

export interface MatrixCell { probability: number; impact: number; count: number; class: RiskClass }

export interface Trigger { kind: string; count: number }

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Parametro registro: id del sito o "null" per il gruppo. */
export const registerParam = (plantId: string | null) => plantId ?? "null";

const data = <T,>(p: Promise<{ data: T }>) => p.then(r => r.data);

// ── API ───────────────────────────────────────────────────────────────────────

export const riskApi = {
  // Registro
  list: (plantId: string | null, params: Record<string, string> = {}) =>
    fetchAllPages<Risk>("/risk/assessments/", { plant: registerParam(plantId), ...params }),
  /** Tutti i rischi del nuovo metodo visibili all'utente (per obiettivi di organizzazione). */
  listAll: () => fetchAllPages<Risk>("/risk/assessments/"),
  legacy: (plantId: string) => fetchAllPages<Risk>("/risk/assessments/", { plant: plantId, legacy: "1" }),
  get: (id: string) => data(apiClient.get<Risk>(`/risk/assessments/${id}/`)),
  create: (payload: RiskInput) => data(apiClient.post<Risk>("/risk/assessments/", payload)),
  update: (id: string, payload: RiskInput) => data(apiClient.patch<Risk>(`/risk/assessments/${id}/`, payload)),
  remove: (id: string) => apiClient.delete(`/risk/assessments/${id}/`),
  complete: (id: string) => data(apiClient.post<Risk>(`/risk/assessments/${id}/complete/`)),
  confirm: (id: string) => data(apiClient.post<Risk>(`/risk/assessments/${id}/confirm/`)),
  reopen: (id: string) => data(apiClient.post<Risk>(`/risk/assessments/${id}/reopen/`)),
  applyExpected: (id: string, note: string) =>
    data(apiClient.post<Risk>(`/risk/assessments/${id}/apply-expected/`, { note })),
  completeness: (id: string) => data(apiClient.get<{ errors: string[] }>(`/risk/assessments/${id}/completeness/`)),
  acceptanceRequirements: (id: string) =>
    data(apiClient.get<AcceptanceRequirements>(`/risk/assessments/${id}/acceptance-requirements/`)),
  notApplicable: (plantId: string | null, assetType: AssetType, threat: string, reason: string) =>
    data(apiClient.post<Risk>("/risk/assessments/not-applicable/", {
      plant: plantId, asset_type: assetType, threat, reason,
    })),
  coverage: (plantId: string | null) =>
    data(apiClient.get<Coverage>("/risk/assessments/coverage/", { params: { plant: registerParam(plantId) } })),
  objectives: (plantId: string | null) =>
    data(apiClient.get<ObjectiveRow[]>("/risk/assessments/objectives/", { params: { plant: registerParam(plantId) } })),
  informationCoverage: (plantId: string | null) =>
    data(apiClient.get<InformationCoverageRow[]>("/risk/assessments/information-coverage/", {
      params: { plant: registerParam(plantId) },
    })),
  businessObjectives: (plantId: string | null) =>
    fetchAllPages<BusinessObjective>("/risk/business-objectives/").then(all =>
      all.filter(o => o.plant === null || o.plant === plantId)),
  createBusinessObjective: (payload: Partial<BusinessObjective>) =>
    data(apiClient.post<BusinessObjective>("/risk/business-objectives/", payload)),
  updateBusinessObjective: (id: string, payload: Partial<BusinessObjective>) =>
    data(apiClient.patch<BusinessObjective>(`/risk/business-objectives/${id}/`, payload)),
  deleteBusinessObjective: (id: string) => apiClient.delete(`/risk/business-objectives/${id}/`),
  aiDraft: (id: string) => data(apiClient.post<AiMeta & { proposal: AiDraftProposal; names?: AiLinkNames }>(
    `/risk/assessments/${id}/ai-draft/`, {}, { timeout: 180000 },
  )),
  aiMeasures: (id: string) => data(apiClient.post<AiMeta & { measures: AiMeasure[] }>(`/risk/assessments/${id}/ai-measures/`)),
  aiIdentify: (plantId: string | null, assetType: AssetType) =>
    data(apiClient.post<AiIdentifyResult>("/risk/assessments/ai-identify/", { asset_type: assetType }, {
      params: { plant: registerParam(plantId) }, timeout: 240000,
    })),
  aiIdentifyApply: (plantId: string | null, assetType: AssetType, items: AiIdentifyItem[]) =>
    data(apiClient.post<{ created: string[]; not_applicable: number; skipped: number }>(
      "/risk/assessments/ai-identify-apply/", { asset_type: assetType, items },
      { params: { plant: registerParam(plantId) } },
    )),
  review: (plantId: string | null, ai: boolean) =>
    data(apiClient.post<RegisterReview>("/risk/assessments/review/", { ai }, { params: { plant: registerParam(plantId) } })),
  aiSummary: (plantId: string | null) =>
    data(apiClient.post<AiMeta & { summary: string }>("/risk/assessments/ai-summary/", {}, {
      params: { plant: registerParam(plantId) }, timeout: 180000,
    })),
  aiFeedback: (interactionId: string, action: "confirm" | "ignore", finalText = "") =>
    data(apiClient.post("/risk/assessments/ai-feedback/", { interaction_id: interactionId, action, final_text: finalText })),
  attention: (plantId: string | null) =>
    data(apiClient.get<Attention>("/risk/assessments/attention/", { params: { plant: registerParam(plantId) } })),
  triggers: (plantId: string | null) =>
    data(apiClient.get<Trigger[]>("/risk/assessments/triggers/", { params: { plant: registerParam(plantId) } })),
  matrix: (plantId: string | null, view: "current" | "expected") =>
    data(apiClient.get<MatrixCell[]>("/risk/assessments/matrix/", {
      params: { plant: registerParam(plantId), view },
    })),
  exportExcel: (plantId: string | null) =>
    apiClient.get("/risk/assessments/export/", { params: { plant: registerParam(plantId) }, responseType: "blob" }),

  // Misure esistenti
  measures: (riskId: string) => fetchAllPages<ExistingMeasure>("/risk/existing-measures/", { risk: riskId }),
  createMeasure: (payload: Partial<ExistingMeasure>) =>
    data(apiClient.post<ExistingMeasure>("/risk/existing-measures/", payload)),
  updateMeasure: (id: string, payload: Partial<ExistingMeasure>) =>
    data(apiClient.patch<ExistingMeasure>(`/risk/existing-measures/${id}/`, payload)),
  deleteMeasure: (id: string) => apiClient.delete(`/risk/existing-measures/${id}/`),

  // Piani di trattamento
  plans: (params: Record<string, string>) => fetchAllPages<MitigationPlan>("/risk/mitigation-plans/", params),
  createPlan: (payload: Partial<MitigationPlan>) =>
    data(apiClient.post<MitigationPlan>("/risk/mitigation-plans/", payload)),
  updatePlan: (id: string, payload: Partial<MitigationPlan>) =>
    data(apiClient.patch<MitigationPlan>(`/risk/mitigation-plans/${id}/`, payload)),
  deletePlan: (id: string) => apiClient.delete(`/risk/mitigation-plans/${id}/`),
  verifyPlan: (id: string, note: string) =>
    data(apiClient.post<MitigationPlan>(`/risk/mitigation-plans/${id}/verify/`, { note })),
  uncompletePlan: (id: string) => data(apiClient.post<MitigationPlan>(`/risk/mitigation-plans/${id}/uncomplete/`)),

  // Accettazioni
  acceptances: (params: Record<string, string>) => fetchAllPages<Acceptance>("/risk/acceptances/", params),
  requestAcceptance: (payload: {
    risk: string; rationale: string; expires_on?: string; body?: string; body_resolution_ref?: string;
  }) => data(apiClient.post<Acceptance>("/risk/acceptances/", payload)),
  signAcceptance: (id: string) => data(apiClient.post<Acceptance>(`/risk/acceptances/${id}/sign/`)),
  giveOpinion: (id: string, favorable: boolean, note: string) =>
    data(apiClient.post<Acceptance>(`/risk/acceptances/${id}/opinion/`, { favorable, note })),
  bodyDecision: (id: string, body: string, resolution_ref: string) =>
    data(apiClient.post<Acceptance>(`/risk/acceptances/${id}/body-decision/`, { body, resolution_ref })),
  revokeAcceptance: (id: string, reason: string) =>
    data(apiClient.post<Acceptance>(`/risk/acceptances/${id}/revoke/`, { reason })),

  // Rischi ereditati
  localImpactReports: (params: Record<string, string>) =>
    fetchAllPages<LocalImpactReport>("/risk/local-impact-reports/", params),
  reportLocalImpact: (payload: { risk: string; plant: string; local_impact: number; note: string }) =>
    data(apiClient.post<LocalImpactReport>("/risk/local-impact-reports/", payload)),
  acknowledgeLocalImpact: (id: string) =>
    data(apiClient.post<LocalImpactReport>(`/risk/local-impact-reports/${id}/acknowledge/`)),

  // Catalogo minacce
  threats: (params: Record<string, string> = {}) => fetchAllPages<ThreatEntry>("/risk/threats/", params),
  createThreat: (payload: Partial<ThreatEntry>) => data(apiClient.post<ThreatEntry>("/risk/threats/", payload)),
  updateThreat: (id: string, payload: Partial<ThreatEntry>) =>
    data(apiClient.patch<ThreatEntry>(`/risk/threats/${id}/`, payload)),
  deactivateThreat: (id: string) => apiClient.delete(`/risk/threats/${id}/`),

  // Classi di informazioni
  /** Classi del sito più quelle di gruppo (per il gruppo: solo quelle di gruppo). */
  informationClasses: (plantId: string | null) =>
    fetchAllPages<InformationClass>("/risk/information-classes/").then(all =>
      all.filter(ic => ic.plant === null || ic.plant === plantId)),
  createInformationClass: (payload: Partial<InformationClass>) =>
    data(apiClient.post<InformationClass>("/risk/information-classes/", payload)),
  updateInformationClass: (id: string, payload: Partial<InformationClass>) =>
    data(apiClient.patch<InformationClass>(`/risk/information-classes/${id}/`, payload)),
  deleteInformationClass: (id: string) => apiClient.delete(`/risk/information-classes/${id}/`),

  // Governo del rischio
  resolvedPolicy: (plantId: string | null) =>
    data(apiClient.get<ResolvedPolicy>("/risk/governance-policies/resolved/", {
      params: plantId ? { plant: plantId } : {},
    })),
  presets: () => data(apiClient.get<Record<string, ResolvedPolicy>>("/risk/governance-policies/presets/")),
  savePolicy: (plantId: string | null, payload: Partial<ResolvedPolicy> & { notes?: string }) =>
    data(apiClient.post("/risk/governance-policies/save/", { plant: plantId, ...payload })),

  // Cicli
  cycles: (plantId: string | null) => fetchAllPages<Cycle>("/risk/cycles/", { plant: registerParam(plantId) }),
  startCycle: (plantId: string | null, kind: CycleKind, trigger_reason = "") =>
    data(apiClient.post<Cycle>("/risk/cycles/start/", { plant: plantId, kind, trigger_reason })),
  submissionCheck: (id: string) => data(apiClient.get<{ errors: string[] }>(`/risk/cycles/${id}/submission-check/`)),
  submitCycle: (id: string) => data(apiClient.post<Cycle>(`/risk/cycles/${id}/submit/`)),
  returnCycle: (id: string, reason: string) => data(apiClient.post<Cycle>(`/risk/cycles/${id}/return/`, { reason })),
  exportCycle: (id: string) => apiClient.get(`/risk/cycles/${id}/export/`, { responseType: "blob" }),
  approveCycle: (id: string, payload: { body: string; review?: string; local_adoption_ref?: string }) =>
    data(apiClient.post<Cycle>(`/risk/cycles/${id}/approve/`, payload)),
};

/** Messaggio d'errore leggibile dalle risposte 400/403 del backend. */
export function apiError(err: unknown, fallback: string): string {
  const resp = (err as { response?: { data?: unknown } })?.response?.data;
  if (resp && typeof resp === "object") {
    const d = resp as Record<string, unknown>;
    if (typeof d.error === "string") return d.error;
    if (typeof d.detail === "string") return d.detail;
    const first = Object.values(d)[0];
    if (Array.isArray(first) && typeof first[0] === "string") return first[0];
    if (typeof first === "string") return first;
  }
  return fallback;
}
