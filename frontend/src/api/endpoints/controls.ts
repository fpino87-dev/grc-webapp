import { apiClient } from "../client";

export interface MappedControl {
  external_id: string;
  framework_code: string;
  relationship: string;
}

export interface ControlInstance {
  id: string;
  plant: string;
  control: string;
  control_external_id: string;
  control_title: string;
  framework_code: string;
  status: "compliant" | "parziale" | "gap" | "na" | "non_valutato";
  owner: number | null;
  owner_display: string | null;
  notes: string;
  last_evaluated_at: string | null;
  mapped_controls: MappedControl[];
  suggested_status?: string;
  suggestion_differs?: boolean;
  calc_maturity_level: number;
  assets?: string[];
  approved_in_soa: boolean;
  soa_approved_at: string | null;
  soa_approved_by_name: string | null;
}

export interface AssetRef {
  id: string;
  name: string;
  asset_type?: string;
}

export interface Framework {
  id: string;
  code: string;
  name: string;
  version: string;
}

export interface FrameworkGovernanceMeta {
  id: string;
  code: string;
  name: string;
  version: string;
  published_at: string;
  archived_at: string | null;
  controls_count: number;
  domains_count: number;
  languages: string[];
}

export interface FrameworkImportPreview {
  sha256: string;
  framework: { code: string; name: string; version: string; published_at: string };
  counts: { domains: number; controls: number; mappings: number };
  languages: string[];
}

export interface EvidenceRef {
  id: string;
  title: string;
  valid_until: string | null;
  expired: boolean;
  evidence_type: string;
}

export interface DocRequirement {
  type: string;
  mandatory: boolean;
  description: string;
}
export interface EvRequirement {
  type: string;
  mandatory: boolean;
  max_age_days?: number;
  description: string;
}
export interface EvidenceRequirement {
  documents: DocRequirement[];
  evidences: EvRequirement[];
  min_documents: number;
  min_evidences: number;
  notes?: string;
}
export interface RequirementsCheck {
  satisfied: boolean;
  missing_documents: { type: string; description: string }[];
  missing_evidences: { type: string; description: string }[];
  expired_evidences: { id: string; title: string; expired_on: string }[];
  warnings: string[];
  not_applicable?: boolean;
}
export interface LinkedDocument {
  id: string;
  document_code: string;
  title: string;
  document_type: string;
  status: string;
  review_due_date: string | null;
}

export interface ControlDetailInfo {
  control_id: string;
  control_uuid: string;
  title: string;
  domain: string;
  framework: string;
  level: string;
  control_category: string;
  evidence_requirement: EvidenceRequirement;
  description: string;
  practical_summary: string;
  implementation_guidance: string;
  evidence_examples: string[];
  mappings: { target_control__framework__code: string; target_control__external_id: string; relationship: string }[];
  evaluation_history: { timestamp_utc: string; user_email_at_time: string; payload: Record<string, unknown> }[];
  current_evidences: EvidenceRef[];
  linked_documents: LinkedDocument[];
  requirements: RequirementsCheck;
  normative_requirements: { punto: string; applies_to: string[]; ambito: string; text: string }[];
  current_status: string;
  suggested_status: string;
  suggested_status_reason: string;
  applicability: string;
  exclusion_justification: string;
  na_justification: string;
  maturity_level: number | null;
  maturity_level_override: boolean;
  calc_maturity_level: number;
  approved_in_soa: boolean;
  soa_approved_at: string | null;
  soa_approved_by_name: string | null;
  notes: string;
  needs_revaluation?: boolean;
  needs_revaluation_since?: string | null;
  plant_id?: string;
  linked_assets?: AssetRef[];
  available_assets?: AssetRef[];
}

export type GapState = "coperto" | "coperto_riuso" | "parziale" | "parziale_riuso" | "scoperto" | "escluso";

export interface GapCrossLink {
  framework: string;
  external_id: string;
  title: string;
  relationship: "equivalente" | "parziale" | "correlato";
  status: string | null; // status ufficiale della controparte sul plant (null = nessuna istanza)
  via: string | null;    // ID del controllo ISO hub per i collegamenti transitivi
}

export interface GapItem {
  id: string;
  external_id: string;
  framework: string;
  title: string;
  domain: string;
  domain_name: string;
  direct_status: string | null;
  state: GapState;
  cross: GapCrossLink[];
  weight: number; // per ACN = numero di requirement applicabili (denominatore spec §3.1)
  requirements?: { punto: string; applies_to: string[]; text: string }[];
}

export interface GapCoverage {
  applicable: number;
  direct_pct: number;
  assisted_pct: number;
}

export interface GapAnalysisResult {
  target: string;
  profile: string;
  include_proto: boolean | null;
  frameworks: string[];
  counts: Record<GapState, number>;
  coverage: GapCoverage;
  coverage_by_domain: ({ code: string; name: string } & Record<GapState, number> & GapCoverage)[];
  items: GapItem[];
}

export const controlsApi = {
  instances: (params?: Record<string, string>) =>
    apiClient.get<{ results: ControlInstance[]; count: number }>("/controls/instances/", { params: { page_size: "1000", ...params } }).then((r) => r.data),
  frameworks: (plantId?: string) =>
    apiClient.get<{ results: Framework[] }>(
      "/controls/frameworks/",
      { params: plantId ? { plant: plantId } : {} }
    ).then((r) => r.data.results ?? r.data),
  frameworksGovernance: () =>
    apiClient.get<{ results: FrameworkGovernanceMeta[] }>(
      "/controls/frameworks/governance/",
    ).then((r) => r.data.results ?? r.data),
  previewFrameworkImport: (payload: Record<string, unknown>) =>
    apiClient.post<FrameworkImportPreview>("/controls/frameworks/import-preview/", payload).then((r) => r.data),
  importFramework: (payload: Record<string, unknown>) =>
    apiClient.post<{ ok: boolean; framework: { id: string; code: string; name: string; version: string }; message: string }>(
      "/controls/frameworks/import/",
      payload,
    ).then((r) => r.data),
  updateInstance: (id: string, data: Partial<ControlInstance>) =>
    apiClient.patch<ControlInstance>(`/controls/instances/${id}/`, data).then((r) => r.data),
  eligibleOwners: (plantId: string) =>
    apiClient
      .get<{ id: number; name: string; role: string }[]>("/controls/instances/eligible-owners/", {
        params: { plant: plantId },
      })
      .then((r) => r.data),
  propagate: (id: string) =>
    apiClient
      .post<{ propagated_to: number; skipped_no_instance: number; blocked?: string }>(
        `/controls/instances/${id}/propagate/`,
      )
      .then((r) => r.data),
  bulkApproveSoa: (instanceIds: string[], approved = true) =>
    apiClient
      .post<{ ok: boolean; approved_count: number; approved: boolean }>(
        "/controls/instances/bulk-approve-soa/",
        { instance_ids: instanceIds, approved },
      )
      .then((r) => r.data),
  evaluate: (id: string, status: string, note: string) =>
    apiClient.post(`/controls/instances/${id}/evaluate/`, { status, note }).then((r) => r.data),
  detailInfo: (id: string, lang = "it") =>
    apiClient.get<ControlDetailInfo>(`/controls/instances/${id}/detail-info/`, { params: { lang } }).then((r) => r.data),
  linkEvidence: (instanceId: string, evidenceId: string) =>
    apiClient.post(`/controls/instances/${instanceId}/link_evidence/`, { evidence_id: evidenceId }).then((r) => r.data),
  unlinkEvidence: (instanceId: string, evidenceId: string) =>
    apiClient.post(`/controls/instances/${instanceId}/unlink_evidence/`, { evidence_id: evidenceId }).then((r) => r.data),
  gapAnalysis: (target: string, plant: string, opts?: { profile?: string; proto?: boolean; lang?: string }) =>
    apiClient.get<GapAnalysisResult>("/controls/gap-analysis/", {
      params: {
        target, plant,
        ...(opts?.profile ? { profile: opts.profile } : {}),
        ...(opts?.proto ? { proto: "true" } : {}),
        ...(opts?.lang ? { lang: opts.lang } : {}),
      },
    }).then((r) => r.data),
  linkDocument: (instanceId: string, documentId: string) =>
    apiClient.post(`/controls/instances/${instanceId}/link-document/`, { document_id: documentId }).then((r) => r.data),
  unlinkDocument: (instanceId: string, documentId: string) =>
    apiClient.post(`/controls/instances/${instanceId}/unlink-document/`, { document_id: documentId }).then((r) => r.data),
  applySuggestion: (instanceId: string, note: string) =>
    apiClient.post(`/controls/instances/${instanceId}/apply-suggestion/`, { note }).then((r) => r.data),
  setApplicability: (instanceId: string, applicability: string, justification: string) =>
    apiClient.post(`/controls/instances/${instanceId}/set-applicability/`, { applicability, justification }).then((r) => r.data),
  setMaturity: (instanceId: string, maturityLevel: number) =>
    apiClient.post(`/controls/instances/${instanceId}/set-maturity/`, { maturity_level: maturityLevel }).then((r) => r.data),
  deleteInstance: (id: string) => apiClient.delete(`/controls/instances/${id}/`),
  archiveFramework: (id: string) => apiClient.delete(`/controls/frameworks/${id}/`),
  deleteFramework: (id: string) => apiClient.delete(`/controls/frameworks/${id}/delete/`),
  explainControl: (controlId: string, lang = "it") =>
    apiClient.post<{ summary: string; interaction_id: string; provider: string; model: string }>(
      `/controls/controls/${controlId}/explain/`,
      { lang },
    ).then((r) => r.data),
  generateDocument: (controlId: string, lang = "it") =>
    apiClient.post(
      `/controls/controls/${controlId}/generate-document/`,
      { lang },
      { responseType: "blob", timeout: 300_000 },
    ).then((r) => r.data as Blob),
};
