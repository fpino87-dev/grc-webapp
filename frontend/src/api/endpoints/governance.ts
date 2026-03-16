import { apiClient } from "../client";

export interface RoleAssignment {
  id: string;
  user: number;
  user_email?: string;
  user_name?: string;
  role: string;
  scope_type: "org" | "bu" | "plant";
  scope_id: string | null;
  scope_label?: string;
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

export const governanceApi = {
  roleAssignments: () =>
    apiClient.get<{ results: RoleAssignment[] }>("/governance/role-assignments/").then((r) => r.data.results ?? r.data),
  createRoleAssignment: (data: Partial<RoleAssignment>) =>
    apiClient.post<RoleAssignment>("/governance/role-assignments/", data).then((r) => r.data),
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
  committees: () =>
    apiClient.get<{ results: SecurityCommittee[] }>("/governance/committees/").then((r) => r.data.results ?? r.data),
  createCommittee: (data: Partial<SecurityCommittee>) =>
    apiClient.post<SecurityCommittee>("/governance/committees/", data).then((r) => r.data),
};
