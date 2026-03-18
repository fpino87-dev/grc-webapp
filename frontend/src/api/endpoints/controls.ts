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
  owner: string | null;
  notes: string;
  last_evaluated_at: string | null;
  mapped_controls: MappedControl[];
  suggested_status?: string;
  suggestion_differs?: boolean;
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
}
export interface LinkedDocument {
  id: string;
  title: string;
  document_type: string;
  status: string;
  review_due_date: string | null;
}

export interface ControlDetailInfo {
  control_id: string;
  title: string;
  domain: string;
  framework: string;
  level: string;
  control_category: string;
  evidence_requirement: EvidenceRequirement;
  description: string;
  implementation_guidance: string;
  evidence_examples: string[];
  mappings: { target_control__framework__code: string; target_control__external_id: string; relationship: string }[];
  evaluation_history: { timestamp_utc: string; user_email_at_time: string; payload: Record<string, unknown> }[];
  current_evidences: EvidenceRef[];
  linked_documents: LinkedDocument[];
  requirements: RequirementsCheck;
  current_status: string;
  suggested_status: string;
  suggested_status_reason: string;
  applicability: string;
  exclusion_justification: string;
  maturity_level: number | null;
  maturity_level_override: boolean;
  calc_maturity_level: number;
  approved_in_soa: boolean;
  soa_approved_at: string | null;
}

export interface GapEntry {
  id: string;
  external_id: string;
  title: string;
  domain: string;
  source_status?: string;
}

export interface GapAnalysisResult {
  source_framework: string;
  target_framework: string;
  covered: GapEntry[];
  partial: GapEntry[];
  gap: GapEntry[];
  not_mapped: GapEntry[];
  summary: {
    total: number;
    covered: number;
    partial: number;
    gap: number;
    not_mapped: number;
    pct_ready: number;
  };
}

export const controlsApi = {
  instances: (params?: Record<string, string>) =>
    apiClient.get<{ results: ControlInstance[]; count: number }>("/controls/instances/", { params: { page_size: "500", ...params } }).then((r) => r.data),
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
  propagate: (id: string) =>
    apiClient.post<{ propagated_to: number }>(`/controls/instances/${id}/propagate/`).then((r) => r.data),
  evaluate: (id: string, status: string, note: string) =>
    apiClient.post(`/controls/instances/${id}/evaluate/`, { status, note }).then((r) => r.data),
  detailInfo: (id: string, lang = "it") =>
    apiClient.get<ControlDetailInfo>(`/controls/instances/${id}/detail-info/`, { params: { lang } }).then((r) => r.data),
  linkEvidence: (instanceId: string, evidenceId: string) =>
    apiClient.post(`/controls/instances/${instanceId}/link_evidence/`, { evidence_id: evidenceId }).then((r) => r.data),
  unlinkEvidence: (instanceId: string, evidenceId: string) =>
    apiClient.post(`/controls/instances/${instanceId}/unlink_evidence/`, { evidence_id: evidenceId }).then((r) => r.data),
  gapAnalysis: (source: string, target: string, plant?: string) =>
    apiClient.get<GapAnalysisResult>("/controls/gap-analysis/", { params: { source, target, ...(plant ? { plant } : {}) } }).then((r) => r.data),
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
};
