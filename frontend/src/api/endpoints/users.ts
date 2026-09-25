import { apiClient } from "../client";
import { fetchAllPages } from "../pagination";

export interface GrcUser {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  is_staff: boolean;
  is_superuser: boolean;
  date_joined: string;
  grc_role: string | null;
  plant_access: { id: string; role: string; scope_type: string }[];
  // Gestione utenti: accessi descritti, responsabilità attive, avvisi di coerenza
  last_login?: string | null;
  accesses?: UserAccess[];
  responsibilities?: UserResponsibility[];
  warnings?: ResponsibilityGap[];
  mfa_enabled?: boolean;
}

export type AccessScopeType = "org" | "bu" | "plant_list" | "single_plant";

export interface UserAccess {
  id: string;
  role: string;
  role_label: string;
  scope_type: AccessScopeType;
  scope_bu_code: string | null;
  scope_plant_codes: string[];
}

export interface UserResponsibility {
  id: string;
  role: string;
  scope_type: "org" | "bu" | "plant";
  scope_id: string | null;
  scope_code: string | null;
  valid_until: string | null;
}

/** Responsabilità attiva senza accesso al portale sullo stesso perimetro. */
export interface ResponsibilityGap {
  responsibility: string;
  role: string;
  scope_type: "org" | "bu" | "plant";
  scope_id: string | null;
}

/** Cosa può fare ogni ruolo per area: W modifica, R consultazione, - niente. */
export interface RoleMatrix {
  roles: string[];
  areas: { key: string; perms: Record<string, "W" | "R" | "-"> }[];
}

export interface NewAccess {
  role: string;
  scope_type: AccessScopeType;
  scope_plants?: string[];
  scope_bu?: string | null;
}

export interface GrcRole {
  value: string;
  label: string;
}

// Tutti i ruoli di accesso (GrcRole) assegnabili a un perimetro.
export const GRC_ACCESS_ROLES = [
  "super_admin",
  "compliance_officer",
  "risk_manager",
  "plant_manager",
  "control_owner",
  "internal_auditor",
  "external_auditor",
] as const;

export interface PlantAccessGrant {
  id: string;
  user: number;
  role: string;
  role_label: string;
  scope_type: "org" | "bu" | "plant_list" | "single_plant";
  scope_bu: string | null;
  scope_bu_code: string | null;
  scope_plants: string[];
  scope_plant_codes: string[];
}

export const plantAccessApi = {
  listForUser: (userId: number) =>
    fetchAllPages<PlantAccessGrant>("/auth/plant-access/", { user: String(userId) }),
  create: (data: { user: number; role: string; scope_type: string; scope_plants?: string[]; scope_bu?: string | null }) =>
    apiClient.post<PlantAccessGrant>("/auth/plant-access/", data).then(r => r.data),
  remove: (id: string) => apiClient.delete(`/auth/plant-access/${id}/`),
};

export const usersApi = {
  list: () => fetchAllPages<GrcUser>("/auth/users/"),
  /** Gestione utenti: `status` active (default), inactive o all. */
  listForAdmin: (status: "active" | "inactive" | "all" = "active") =>
    fetchAllPages<GrcUser>("/auth/users/", { status }),
  roleMatrix: () => apiClient.get<RoleMatrix>("/auth/users/role-matrix/").then(r => r.data),
  create: (data: { username: string; email: string; first_name?: string; last_name?: string; password: string; grc_role?: string; accesses?: NewAccess[] }) =>
    apiClient.post<GrcUser>("/auth/users/", data).then(r => r.data),
  update: (id: number, data: Partial<GrcUser>) =>
    apiClient.patch<GrcUser>(`/auth/users/${id}/`, data).then(r => r.data),
  setPassword: (id: number, password: string) =>
    apiClient.post(`/auth/users/${id}/set_password/`, { password }).then(r => r.data),
  assignRole: (id: number, role: string, scope_type = "org") =>
    apiClient.post(`/auth/users/${id}/assign_role/`, { role, scope_type }).then(r => r.data),
  toggleActive: (id: number) =>
    apiClient.post(`/auth/users/${id}/toggle_active/`).then(r => r.data),
  listRoles: () => apiClient.get<GrcRole[]>("/auth/users/list_roles/").then(r => r.data),
  me: () => apiClient.get<GrcUser>("/auth/users/me/").then(r => r.data),
  remove: (id: number) => apiClient.delete(`/auth/users/${id}/`),
  resetTestDb: () =>
    apiClient.post<{ status: string; message: string; detail: string }>(
      "/auth/reset-test-db/",
      {},
      { headers: { "X-Confirm-Reset": "RESET-CONFIRMED" } },
    ).then(r => r.data),
};
