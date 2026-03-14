import { apiClient } from "../client";

export interface RoleAssignment {
  id: string;
  user: string;
  user_email?: string;
  role: string;
  scope_type: "org" | "bu" | "plant";
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

export const governanceApi = {
  roleAssignments: () =>
    apiClient.get<{ results: RoleAssignment[] }>("/governance/role-assignments/").then((r) => r.data.results),
  createRoleAssignment: (data: Partial<RoleAssignment>) =>
    apiClient.post<RoleAssignment>("/governance/role-assignments/", data).then((r) => r.data),
  committees: () =>
    apiClient.get<{ results: SecurityCommittee[] }>("/governance/committees/").then((r) => r.data.results),
  createCommittee: (data: Partial<SecurityCommittee>) =>
    apiClient.post<SecurityCommittee>("/governance/committees/", data).then((r) => r.data),
};
