import { apiClient } from "../client";

// ── Compliance (tab Reporting) ────────────────────────────────────────────────
// Conteggi con la regola unica di conformità: N/A fuori dal denominatore,
// controlli base sostituiti da un extender attivo (TISAX L2 → VH L3) contati a parte.
export interface ComplianceCounts {
  total: number;
  compliant: number;
  parziale: number;
  gap: number;
  non_valutato: number;
  na_excluded: number;
  superseded_by_extender: number;
  pct_compliant: number;
}

export interface ComplianceTrendPoint {
  date: string;
  pct_compliant: number;
  legacy: boolean; // calcolato con la regola precedente
  live: boolean;   // valore di oggi, non una fotografia settimanale
}

export interface ComplianceFramework extends ComplianceCounts {
  code: string;
  name: string;
  trend: ComplianceTrendPoint[];
  delta: number | null;
}

export interface CompliancePlantCell {
  pct_compliant: number;
  total: number;
  gap: number;
  parziale: number;
  non_valutato: number;
}

export interface ComplianceOverview {
  frameworks: ComplianceFramework[];
  plants: { id: string; code: string; name: string; cells: Record<string, CompliancePlantCell> }[] | null;
}

export interface ComplianceDomain extends ComplianceCounts {
  code: string;
  name: string;
  order: number;
}

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
  ale: number;
  ale_inherent: number;
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

export interface TreatmentRosi {
  id: string;
  title: string;
  process_id: string;
  process_name: string;
  ale_reduction_pct: number;
  process_ale: number;
  ale_avoided: number;
  cost_implementation: number;
  cost_annual: number;
  annual_cost: number;
  net_annual: number;
  rosi_pct: number | null;
  payback_months: number | null;
  worth_it: boolean;
}

export interface TreatmentRosiTotals {
  count: number;
  ale_avoided: number;
  annual_cost: number;
  net_annual: number;
  rosi_pct: number | null;
  amort_years: number;
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
    ale_total: number;
    ale_total_inherent: number;
    ale_saved: number;
    ale_saved_pct: number;
    ale_valued_count: number;
    ale_coverage_pct: number;
  };
  heatmap: HeatmapCell[];
  top_risks: TopRisk[];
  by_threat: ThreatBreakdown[];
  nis2_breakdown: Nis2CategoryBreakdown[];
  bia_bcp_table: BiaBcpRow[];
  treatments: TreatmentRosi[];
  treatments_totals: TreatmentRosiTotals;
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
  no_required_docs: boolean;
}

export interface MttrEntry {
  count: number;
  avg_days: number | null;
}

export interface SupplierNdaEntry {
  id: string;
  name: string;
  risk_level: string;
  nda_status: "ok" | "expiring" | "expired" | "draft" | "missing";
  expiry_date: string | null;
  days_to_expiry: number | null;
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
  training: TrainingKpi;
  supplier_nda: {
    covered: number;
    expiring_soon: number;
    expired: number;
    without_nda: number;
    suppliers: SupplierNdaEntry[];
  };
}

export interface TrainingKpi {
  coverage: {
    year: number;
    target: number;
    covered: number;
    pct: number | null;
    rows: {
      course_id: string;
      course_title: string;
      plant_id: string;
      plant_code: string;
      target: number;
      trained: number;
      pct: number | null;
    }[];
  };
  plan: {
    year: number;
    items: number;
    due: number;
    done: number;
    pct: number | null;
    overdue: number;
    due_soon: number;
  };
  phishing: {
    sent: number;
    clicked: number;
    reported: number;
    click_pct: number | null;
    report_pct: number | null;
    campaigns: {
      session_id: string;
      course_title: string;
      plant_code: string | null;
      held_on: string;
      sent: number;
      clicked: number;
      reported: number;
      legacy: boolean;
    }[];
  };
  expiring_evidence: {
    session_id: string;
    course_title: string;
    plant_code: string | null;
    held_on: string;
    valid_until: string;
    expired: boolean;
  }[];
  stale_audiences: number;
  // Organo di gestione (NIS2 art. 20): solo conteggi.
  board: { total: number; trained: number; pct: number | null };
}

export interface AccessMatrixRow {
  user_id: string;
  user_name: string;
  user_email: string;
  is_active: boolean;
  kind: "access" | "responsibility";
  role: string;
  role_label: string;
  scope_type: string;
  scope_label: string;
  plant_codes: string[];
  covers_all: boolean;
  valid_until: string | null;
  flags: string[];
}

export interface SecurityCommitteeRow {
  id: string;
  name: string;
  committee_type: "cda" | "comitato" | "direzione";
  committee_type_label: string;
  is_management_body: boolean;
  covers_all: boolean;
  plant_codes: string[];
  members: {
    id: string; name: string; position: string; body_role: string; body_role_label: string;
    has_account: boolean; valid_until: string | null; flags: string[];
  }[];
  /** no_members | no_chair */
  flags: string[];
}

export interface AccessMatrixData {
  generated_at: string;
  plant_id: string | null;
  plant_code: string | null;
  rows: AccessMatrixRow[];
  vacant_mandatory_roles: string[];
  committees: SecurityCommitteeRow[];
  summary: { users: number; access: number; responsibilities: number; issues: number; committees: number; committee_issues: number };
}

// ── Obiettivi di sicurezza (§6.2) — vista aggregata di sola lettura ──
export type ReportObjectiveTrack = "in_linea" | "a_rischio" | "mancato" | "senza_misure";

export interface ObjectiveCounts {
  attivi: number;
  in_linea: number;
  a_rischio: number;
  mancato: number;
  senza_misure: number;
  in_preparazione: number;
  raggiunti: number;
  non_raggiunti: number;
}

export interface ObjectivesPlantRow extends ObjectiveCounts {
  plant_id: string | null;
  plant_code: string | null;
  plant_name: string | null;
  bu_code: string | null;
}

export interface ObjectiveReportItem {
  id: string;
  code: string;
  title: string;
  plant_code: string | null;
  owner_role: string;
  baseline_value: number | null;
  target_value: number;
  target_direction: "above" | "below";
  target_date: string;
  current_value: number | null;
  measured_on: string | null;
  unit: string;
  progress_pct: number | null;
  elapsed_pct: number | null;
  days_to_target: number;
  track: ReportObjectiveTrack;
}

export interface ObjectiveKpiItem extends ObjectiveReportItem {
  kpi_code: string;
  kpi_name: string;
  kpi_status: "ok" | "warning" | "critical" | "no_data";
  threshold_warning: number | null;
  threshold_critical: number | null;
  threshold_direction: "above" | "below";
  weak_target: boolean;
}

export interface ObjectivesReportData {
  horizon_days: number;
  closed_window_days: number;
  totals: ObjectiveCounts;
  by_plant: ObjectivesPlantRow[];
  deadlines: ObjectiveReportItem[];
  kpi_linked: ObjectiveKpiItem[];
}

export const reportingApi = {
  accessMatrix: (plant?: string) =>
    apiClient.get<AccessMatrixData>(
      "/reporting/access-matrix/",
      { params: plant ? { plant } : {} }
    ).then(r => r.data),

  exportAccessMatrixCsv: (plant?: string) =>
    apiClient.get("/reporting/access-matrix/", {
      params: { export: "csv", ...(plant ? { plant } : {}) },
      responseType: "blob",
    }).then(r => {
      const blob = new Blob([r.data], { type: "text/csv;charset=utf-8;" });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = "access-matrix.csv";
      link.click();
      URL.revokeObjectURL(link.href);
    }),

  complianceOverview: (plant?: string) =>
    apiClient.get<ComplianceOverview>(
      "/reporting/compliance-overview/",
      { params: plant ? { plant } : {} },
    ).then(r => r.data),

  complianceDomains: (framework: string, plant?: string) =>
    apiClient.get<{ framework: string | null; domains: ComplianceDomain[] }>(
      "/reporting/compliance-domains/",
      { params: { framework, ...(plant ? { plant } : {}) } },
    ).then(r => r.data),

  exportComplianceOpenControlsCsv: (framework: string, plant?: string) =>
    apiClient.get("/reporting/compliance-domains/", {
      params: { export: "csv", framework, ...(plant ? { plant } : {}) },
      responseType: "blob",
    }).then(r => {
      const blob = new Blob([r.data], { type: "text/csv;charset=utf-8;" });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = `compliance-${framework}.csv`;
      link.click();
      URL.revokeObjectURL(link.href);
    }),

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
  objectives: (plant?: string) =>
    apiClient.get<ObjectivesReportData>(
      "/reporting/objectives/",
      { params: plant ? { plant } : {} }
    ).then(r => r.data),
  kpiOverview: (plant?: string) =>
    apiClient.get<KpiOverviewData>(
      "/reporting/kpi-overview/",
      { params: plant ? { plant } : {} }
    ).then(r => r.data),
};
