import { apiClient } from "../client";

export interface AuditLogEntry {
  id: string;
  timestamp_utc: string;
  user_email_at_time: string;
  user_role_at_time: string;
  action_code: string;
  level: string;
  entity_type: string;
  entity_id: string;
  payload: Record<string, unknown>;
}

export const auditTrailApi = {
  // Paginato lato server e anche nella pagina (l'audit trail può contenere
  // migliaia di eventi): qui si legge UNA pagina, con count/next/previous.
  list: (params?: Record<string, string>) =>
    apiClient
      .get<{ results: AuditLogEntry[]; count: number; next: string | null; previous: string | null }>(
        "/audit-trail/audit-logs/", { params: { page_size: "50", ...params } },
      )
      .then((r) => r.data),
};
