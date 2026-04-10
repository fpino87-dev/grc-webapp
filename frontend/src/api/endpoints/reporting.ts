import { apiClient } from "../client";

export interface RiskByOwner {
  owner__id: string | null;
  owner__first_name: string;
  owner__last_name: string;
  owner__email: string;
  owner_name: string;
  owner_email: string;
  totale: number;
  rossi: number;
  gialli: number;
  verdi: number;
  processes: number;
}

export interface TaskByOwner {
  assigned_to__first_name: string;
  assigned_to__last_name: string;
  assigned_to__email: string;
  owner_name: string;
  aperti: number;
  scaduti: number;
  completati_30gg: number;
}

export interface KpiSnapshot {
  week_start: string;
  pct_compliant: number;
  overall_maturity: number | null;
  open_risks: number;
  high_risks: number;
  open_incidents: number;
  critical_incidents: number;
  controls_compliant: number;
  controls_total: number;
  controls_gap: number;
}

export interface HeatmapCell {
  prob: number;
  impact: number;
  count: number;
}

export interface TopRisk {
  id: string;
  name: string;
  score: number;
  inherent_score: number | null;
  threat_category: string;
  threat_label: string;
  treatment: string;
  nis2_relevance: string;
  nis2_relevance_label: string;
  nis2_art21_category: string;
  owner_name: string;
  formally_accepted: boolean;
  needs_revaluation: boolean;
}

export interface ThreatBreakdown {
  category: string;
  label: string;
  count: number;
  residual_avg: number;
  inherent_avg: number;
  rossi: number;
  gialli: number;
  verdi: number;
}

export interface Nis2CategoryBreakdown {
  category: string;
  label: string;
  total: number;
  significativo: number;
  potenzialmente_significativo: number;
  non_significativo: number;
}

export interface BiaBcpRow {
  process_id: string;
  process_name: string;
  criticality: number | null;
  bia_status: string;
  rto_target_hours: number | null;
  rpo_target_hours: number | null;
  risks_total: number;
  risks_red: number;
  risks_yellow: number;
  risks_green: number;
  bcp_plans_count: number;
  bcp_status: string | null;
  next_test_date: string | null;
  last_test_date: string | null;
  last_test_result: string | null;
  test_overdue: boolean;
}

export interface RiskBiaBcpData {
  kpis: {
    risks_total: number;
    risks_red: number;
    risks_yellow: number;
    risks_needs_revaluation: number;
    risks_formally_accepted: number;
    bia_critical_no_bcp: number;
    bcp_test_overdue: number;
  };
  heatmap: HeatmapCell[];
  top_risks: TopRisk[];
  by_threat: ThreatBreakdown[];
  nis2_breakdown: Nis2CategoryBreakdown[];
  bia_bcp_table: BiaBcpRow[];
}

// ── KPI Overview ──────────────────────────────────────────────────────────────

export interface RequiredDocsCoverage {
  framework: string;
  total: number;
  green: number;
  yellow: number;
  red: number;
  pct_coverage: number;
  mandatory_total: number;
  mandatory_ok: number;
  pct_mandatory: number;
}

export interface MttrEntry {
  count: number;
  avg_days: number | null;
}

export interface KpiOverviewData {
  required_docs: RequiredDocsCoverage[];
  mttr: {
    findings: {
      all: MttrEntry;
      major: MttrEntry;
      minor: MttrEntry;
      observation: MttrEntry;
    };
    incidents: {
      all: MttrEntry;
      by_severity: Record<string, MttrEntry>;
    };
    tasks: {
      all: MttrEntry;
    };
  };
  training: {
    total_users: number;
    mandatory_courses_count: number;
    users_all_mandatory_completed: number;
    pct_all_mandatory: number;
    courses: {
      id: string;
      title: string;
      source: string;
      deadline: string | null;
      enrolled: number;
      completed: number;
      pct_completed: number;
      not_enrolled: number;
    }[];
  };
}

export const reportingApi = {
  dashboard: (plant?: string) =>
    apiClient.get<{
      plants_active: number;
      incidents_open: number;
      controls_total: number;
      controls_compliant: number;
      controls_gap: number;
      pct_compliant: number;
    }>("/reporting/dashboard/", { params: plant ? { plant } : {} }).then(r => r.data),
  compliance: (params?: Record<string, string>) =>
    apiClient.get<{
      total: number;
      by_status: Record<string, number>;
      pct_compliant: number;
    }>("/reporting/compliance/", { params }).then(r => r.data),
  ownerReport: (plant?: string) =>
    apiClient.get<{ risks_by_owner: RiskByOwner[]; tasks_by_owner: TaskByOwner[] }>(
      "/reporting/owner-report/",
      { params: plant ? { plant } : {} }
    ).then(r => r.data),
  kpiTrend: (params?: { plant?: string; framework?: string; weeks?: number }) =>
    apiClient.get<{ results: KpiSnapshot[]; framework: string }>(
      "/reporting/kpi-trend/",
      { params }
    ).then(r => r.data),
  riskBiaBcp: (plant?: string) =>
    apiClient.get<RiskBiaBcpData>(
      "/reporting/risk-bia-bcp/",
      { params: plant ? { plant } : {} }
    ).then(r => r.data),
  kpiOverview: (plant?: string) =>
    apiClient.get<KpiOverviewData>(
      "/reporting/kpi-overview/",
      { params: plant ? { plant } : {} }
    ).then(r => r.data),
};
