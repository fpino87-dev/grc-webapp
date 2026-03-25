import { apiClient } from "../client";

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
}

export interface GrcRole {
  value: string;
  label: string;
}

export const usersApi = {
  list: () => apiClient.get<{ results: GrcUser[] }>("/auth/users/").then(r => r.data.results),
  create: (data: { username: string; email: string; first_name?: string; last_name?: string; password: string; grc_role?: string }) =>
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
