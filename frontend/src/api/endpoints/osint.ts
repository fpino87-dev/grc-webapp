import { apiClient } from "../client";

export type EntityType = "my_domain" | "supplier" | "asset";
export type ScanFrequency = "weekly" | "monthly";
export type AlertSeverity = "critical" | "warning" | "info";
export type AlertStatus = "new" | "acknowledged" | "resolved" | "pending_escalation";
export type AlertType =
  | "ssl_expiry" | "ssl_expired" | "blacklist_new"
  | "dmarc_missing" | "score_critical" | "score_degraded"
  | "new_subdomain" | "breach_found";
export type SubdomainStatus = "pending" | "included" | "ignored";
export type ScoreClass = "critical" | "warning" | "attention" | "ok";

export interface OsintScanBrief {
  id: string;
  scan_date: string;
  status: string;
  score_ssl: number;
  score_dns: number;
  score_reputation: number;
  score_grc_context: number;
  score_total: number;
}

export interface OsintEntity {
  id: string;
  entity_type: EntityType;
  source_module: string;
  domain: string;
  display_name: string;
  is_nis2_critical: boolean;
  is_active: boolean;
  scan_frequency: ScanFrequency;
  last_scan: OsintScanBrief | null;
  delta: number | null;
  active_alerts_count: number;
  created_at: string;
  updated_at: string;
}

export interface OsintScanDetail extends OsintScanBrief {
  ssl_valid: boolean | null;
  ssl_expiry_date: string | null;
  ssl_days_remaining: number | null;
  ssl_issuer: string;
  ssl_wildcard: boolean;
  spf_present: boolean | null;
  spf_policy: string;
  dmarc_present: boolean | null;
  dmarc_policy: string;
  mx_present: boolean | null;
  dnssec_enabled: boolean | null;
  domain_expiry_date: string | null;
  domain_registrar: string;
  whois_privacy: boolean | null;
  vt_malicious: number | null;
  vt_suspicious: number | null;
  abuseipdb_score: number | null;
  otx_pulses: number | null;
  gsb_status: string;
  in_blacklist: boolean;
  blacklist_sources: string[];
  hibp_breaches: number | null;
  hibp_data_types: string[];
  enricher_errors: Record<string, string>;
}

export interface OsintEntityDetail extends OsintEntity {
  source_id: string;
  last_scan: OsintScanDetail | null;
  active_alerts: OsintAlert[];
  pending_subdomains_count: number;
}

export interface OsintAlert {
  id: string;
  entity: string;
  entity_domain: string;
  entity_display_name: string;
  scan: string | null;
  alert_type: AlertType;
  severity: AlertSeverity;
  description: string;
  status: AlertStatus;
  linked_incident_id: string | null;
  linked_task_id: string | null;
  created_at: string;
  resolved_at: string | null;
}

export interface OsintSubdomain {
  id: string;
  entity: string;
  entity_domain: string;
  subdomain: string;
  status: SubdomainStatus;
  first_seen: string;
  last_seen: string;
}

export interface OsintDashboardSummary {
  total_entities: number;
  critical_count: number;
  warning_count: number;
  last_scan_date: string | null;
  next_scan_date: string | null;
  pending_subdomains: number;
}

export interface OsintSettings {
  id: string;
  score_threshold_critical: number;
  score_threshold_warning: number;
  freq_my_domains: ScanFrequency;
  freq_suppliers_critical: ScanFrequency;
  freq_suppliers_other: ScanFrequency;
  subdomain_auto_include: "yes" | "no" | "ask";
  anonymization_enabled: boolean;
  has_hibp_key: boolean;
  has_virustotal_key: boolean;
  has_abuseipdb_key: boolean;
  has_gsb_key: boolean;
  has_otx_key: boolean;
  updated_at: string;
}

export interface HistoryPoint {
  scan_id: string;
  scan_date: string;
  score_total: number;
  score_ssl: number;
  score_dns: number;
  score_reputation: number;
  score_grc_context: number;
  has_alerts: boolean;
}

export const osintApi = {
  entities: (params?: Record<string, string>) =>
    apiClient.get<OsintEntity[]>("/osint/entities/", { params }).then(r => r.data),
  entity: (id: string) =>
    apiClient.get<OsintEntityDetail>(`/osint/entities/${id}/`).then(r => r.data),
  entityHistory: (id: string) =>
    apiClient.get<HistoryPoint[]>(`/osint/entities/${id}/history/`).then(r => r.data),
  forceScan: (id: string) =>
    apiClient.post<{ job_id: string; status: string }>(`/osint/entities/${id}/scan/`).then(r => r.data),

  alerts: (params?: Record<string, string>) =>
    apiClient.get<OsintAlert[]>("/osint/alerts/", { params }).then(r => r.data),
  updateAlert: (id: string, data: { status: AlertStatus }) =>
    apiClient.patch<OsintAlert>(`/osint/alerts/${id}/`, data).then(r => r.data),
  escalateAlert: (id: string, action: "incident" | "task" | "ignore") =>
    apiClient.post<OsintAlert>(`/osint/alerts/${id}/escalate/`, { action }).then(r => r.data),

  pendingSubdomains: () =>
    apiClient.get<OsintSubdomain[]>("/osint/subdomains/pending/").then(r => r.data),
  classifySubdomain: (id: string, status: SubdomainStatus) =>
    apiClient.patch<OsintSubdomain>(`/osint/subdomains/${id}/`, { status }).then(r => r.data),

  dashboardSummary: () =>
    apiClient.get<OsintDashboardSummary>("/osint/dashboard/summary/").then(r => r.data),

  settings: () =>
    apiClient.get<OsintSettings>("/osint/settings/").then(r => r.data),
  updateSettings: (data: Partial<OsintSettings> & Record<string, unknown>) =>
    apiClient.patch<OsintSettings>("/osint/settings/", data).then(r => r.data),

  aiAnalyze: (type: "attack_surface" | "suppliers_nis2" | "board_report") =>
    apiClient.post<{ analysis: string }>("/osint/ai/analyze/", { type }).then(r => r.data),
};

export function classifyScore(score: number): ScoreClass {
  if (score >= 70) return "critical";
  if (score >= 50) return "warning";
  if (score >= 30) return "attention";
  return "ok";
}

export function scoreColor(cls: ScoreClass): string {
  return {
    critical: "text-red-700 bg-red-50",
    warning: "text-orange-700 bg-orange-50",
    attention: "text-yellow-700 bg-yellow-50",
    ok: "text-green-700 bg-green-50",
  }[cls];
}

export function scoreBadgeColor(cls: ScoreClass): string {
  return {
    critical: "bg-red-100 text-red-800",
    warning: "bg-orange-100 text-orange-800",
    attention: "bg-yellow-100 text-yellow-800",
    ok: "bg-green-100 text-green-800",
  }[cls];
}

export function deltaArrow(delta: number | null): string {
  if (delta === null || delta === 0) return "→";
  return delta > 0 ? `▲+${delta}` : `▼${delta}`;
}

export function deltaColor(delta: number | null): string {
  if (delta === null || delta === 0) return "text-gray-500";
  return delta > 0 ? "text-red-600" : "text-green-600";
}
