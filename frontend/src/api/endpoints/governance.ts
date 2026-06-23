import { apiClient } from "../client";

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

export interface SecurityCommittee {
  id: string;
  plant: string | null;
  name: string;
  committee_type: "centrale" | "bu";
  frequency: "mensile" | "trimestrale" | "semestrale";
  next_meeting_at: string | null;
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
}

export const governanceApi = {
  roleAssignments: (params?: Record<string, string>) =>
    apiClient.get<{ results: RoleAssignment[] }>("/governance/role-assignments/", { params }).then((r) => r.data.results ?? r.data),
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
    apiClient
      .get<{ results?: RoleRequirement[] } | RoleRequirement[]>("/governance/role-requirements/")
      .then((r) => (Array.isArray(r.data) ? r.data : r.data.results ?? [])),
  createRoleRequirement: (data: Partial<RoleRequirement>) =>
    apiClient.post<RoleRequirement>("/governance/role-requirements/", data).then((r) => r.data),
  updateRoleRequirement: (id: string, data: Partial<RoleRequirement>) =>
    apiClient.patch<RoleRequirement>(`/governance/role-requirements/${id}/`, data).then((r) => r.data),
  deleteRoleRequirement: (id: string) =>
    apiClient.delete(`/governance/role-requirements/${id}/`).then((r) => r.data),
  committees: () =>
    apiClient.get<{ results: SecurityCommittee[] }>("/governance/committees/").then((r) => r.data.results ?? r.data),
  createCommittee: (data: Partial<SecurityCommittee>) =>
    apiClient.post<SecurityCommittee>("/governance/committees/", data).then((r) => r.data),

  // Document workflow policies
  listDocumentPolicies: () =>
    apiClient
      .get<{ results?: DocumentWorkflowPolicy[] } | DocumentWorkflowPolicy[]>(
        "/governance/document-workflow-policies/",
      )
      .then((r) => (Array.isArray(r.data) ? r.data : r.data.results ?? [])),
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
