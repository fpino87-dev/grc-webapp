import { apiClient } from "../client";
import { fetchAllPages } from "../pagination";

export interface RoleAssignment {
  id: string;
  user: number;
  user_email?: string;
  user_name?: string;
  role: string;
  scope_type: "org" | "bu" | "plant";
  scope_id: string | null;
  scope_code?: string | null;
  scope_name?: string | null;
  valid_from: string;
  valid_until: string | null;
  is_active: boolean;
}

/** Organo di governo: CdA (organo di gestione NIS2 art. 20), comitato
 *  sicurezza o direzione. Nessun sito = intera organizzazione. */
export type CommitteeType = "cda" | "comitato" | "direzione";
export type MemberRole = "presidente" | "membro" | "segretario";

export interface CommitteeMember {
  id: string;
  committee: string;
  full_name: string;
  position: string;
  body_role: MemberRole;
  user: number | null;
  user_name: string | null;
  user_is_active: boolean | null;
  valid_from: string;
  valid_until: string | null;
  is_active: boolean;
}

export interface SecurityCommittee {
  id: string;
  name: string;
  committee_type: CommitteeType;
  plants: string[];
  plant_codes: string[];
  description: string;
  is_management_body: boolean;
  members: CommitteeMember[];
}

export interface VacantiResult {
  vacant_roles: string[];
  count: number;
  critical: boolean;
}

export interface ExpiringRole {
  id: string;
  role: string;
  user: string;
  valid_until: string;
  days_left?: number;
}

export interface InScadenzaResult {
  expiring: ExpiringRole[];
  expired: ExpiringRole[];
}

export type CoverageStatus =
  | "covered"
  | "covered_via_org"
  | "expiring"
  | "vacant"
  | "unset"
  | "na";

export interface CoverageHolder {
  id: string;
  user: string | null;
  valid_until: string | null;
  days_left: number | null;
}

export interface OrgRoleCoverage {
  role: string;
  framework_refs: string[];
  status: CoverageStatus;
  holders: CoverageHolder[];
}

export interface CoverageCell {
  status: CoverageStatus;
  holders: CoverageHolder[];
  via_org?: boolean;
}

export interface PlantRoleCoverage {
  role: string;
  required: boolean;
  single_holder: boolean;
  framework_refs: string[];
  applies_to: "all" | "nis2_only";
  org_covers_sites: boolean;
  cells: Record<string, CoverageCell>;
}

export interface CoveragePlant {
  id: string;
  code: string;
  name: string;
  bu_id: string | null;
  bu_code: string | null;
  bu_name: string | null;
  nis2_scope: string;
  is_nis2: boolean;
}

export interface RoleCoverageMatrix {
  org_roles: OrgRoleCoverage[];
  plant_roles: PlantRoleCoverage[];
  plants: CoveragePlant[];
}

export interface RoleRequirement {
  id: string;
  role: string;
  scope_level: "org" | "plant";
  applies_to: "all" | "nis2_only";
  org_covers_sites: boolean;
  mandatory: boolean;
  single_holder: boolean;
  enabled: boolean;
  framework_refs: string[];
  notes: string;
}

export interface DocumentWorkflowPolicy {
  id: string;
  document_type: string;
  scope_type: "org" | "bu" | "plant";
  scope_id: string | null;
  submit_roles: string[];
  review_roles: string[];
  approve_roles: string[];
  // Chi approva davvero, oltre al ruolo: delibera dell'organo di governo
  // (politiche deliberate dal CdA) o titolare del documento (contratti, NDA).
  requires_body_resolution?: boolean;
  approval_body?: string | null;
  owner_can_approve?: boolean;
  /** Chi redige non chiude la revisione (separazione dei compiti). */
  require_distinct_reviewer?: boolean;
}

export const governanceApi = {
  roleAssignments: (params?: Record<string, string>) =>
    fetchAllPages<RoleAssignment>("/governance/role-assignments/", params),
  createRoleAssignment: (data: Partial<RoleAssignment>) =>
    apiClient.post<RoleAssignment>("/governance/role-assignments/", data).then((r) => r.data),
  deleteRoleAssignment: (id: string) =>
    apiClient.delete(`/governance/role-assignments/${id}/`).then((r) => r.data),
  terminaRole: (id: string, data: { reason: string; termination_date?: string }) =>
    apiClient.post<{ ok: boolean; valid_until: string; message: string }>(
      `/governance/role-assignments/${id}/termina/`, data
    ).then((r) => r.data),
  sostituisciRole: (id: string, data: { new_user_id: number; reason?: string; handover_date?: string; document_id?: string }) =>
    apiClient.post<{ ok: boolean; message: string; new_user: string; handover_date: string }>(
      `/governance/role-assignments/${id}/sostituisci/`, data
    ).then((r) => r.data),
  vacanti: (plantId?: string) =>
    apiClient.get<VacantiResult>(
      `/governance/role-assignments/vacanti/${plantId ? `?plant=${plantId}` : ""}`
    ).then((r) => r.data),
  inScadenza: (days = 30) =>
    apiClient.get<InScadenzaResult>(
      `/governance/role-assignments/in-scadenza/?days=${days}`
    ).then((r) => r.data),
  coverageMatrix: () =>
    apiClient.get<RoleCoverageMatrix>(
      "/governance/role-assignments/coverage-matrix/"
    ).then((r) => r.data),

  // Role requirements (config matrice copertura)
  listRoleRequirements: () =>
    fetchAllPages<RoleRequirement>("/governance/role-requirements/"),
  createRoleRequirement: (data: Partial<RoleRequirement>) =>
    apiClient.post<RoleRequirement>("/governance/role-requirements/", data).then((r) => r.data),
  updateRoleRequirement: (id: string, data: Partial<RoleRequirement>) =>
    apiClient.patch<RoleRequirement>(`/governance/role-requirements/${id}/`, data).then((r) => r.data),
  deleteRoleRequirement: (id: string) =>
    apiClient.delete(`/governance/role-requirements/${id}/`).then((r) => r.data),
  committees: () =>
    fetchAllPages<SecurityCommittee>("/governance/committees/"),
  createCommittee: (data: Partial<SecurityCommittee>) =>
    apiClient.post<SecurityCommittee>("/governance/committees/", data).then((r) => r.data),
  updateCommittee: (id: string, data: Partial<SecurityCommittee>) =>
    apiClient.patch<SecurityCommittee>(`/governance/committees/${id}/`, data).then((r) => r.data),
  deleteCommittee: (id: string) =>
    apiClient.delete(`/governance/committees/${id}/`).then((r) => r.data),
  createMember: (data: Partial<CommitteeMember>) =>
    apiClient.post<CommitteeMember>("/governance/committee-members/", data).then((r) => r.data),
  updateMember: (id: string, data: Partial<CommitteeMember>) =>
    apiClient.patch<CommitteeMember>(`/governance/committee-members/${id}/`, data).then((r) => r.data),
  deleteMember: (id: string) =>
    apiClient.delete(`/governance/committee-members/${id}/`).then((r) => r.data),

  // Document workflow policies
  listDocumentPolicies: () =>
    fetchAllPages<DocumentWorkflowPolicy>("/governance/document-workflow-policies/"),
  createDocumentPolicy: (data: Partial<DocumentWorkflowPolicy>) =>
    apiClient
      .post<DocumentWorkflowPolicy>("/governance/document-workflow-policies/", data)
      .then((r) => r.data),
  updateDocumentPolicy: (id: string, data: Partial<DocumentWorkflowPolicy>) =>
    apiClient
      .patch<DocumentWorkflowPolicy>(`/governance/document-workflow-policies/${id}/`, data)
      .then((r) => r.data),
  deleteDocumentPolicy: (id: string) =>
    apiClient.delete(`/governance/document-workflow-policies/${id}/`).then((r) => r.data),
};
