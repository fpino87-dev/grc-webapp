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
  list: (params?: Record<string, string>) =>
    apiClient.get<{ results: AuditLogEntry[] }>("/audit-trail/audit-logs/", { params }).then((r) => r.data),
};
