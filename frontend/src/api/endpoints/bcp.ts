import { apiClient } from "../client";
import { fetchAllPages } from "../pagination";

export type BcpTestState = "ok" | "overdue" | "never";
export type BcpCoverage = "covered" | "test_expired" | "missing";
export type BcpTestResult = "superato" | "parziale" | "fallito";
export type BcpTestType = "tabletop" | "drill" | "full_interruption" | "parallel";

export interface BcpPlan {
  id: string; plant: string; title: string; version: string;
  status: "bozza"|"approvato"|"archiviato";
  rto_hours: number | null; rpo_hours: number | null;
  last_test_date: string | null; next_test_date: string | null;
  owner: string | null;
  /** Storico: il backend lo riversa in `critical_processes`. */
  critical_process?: string | null;
  critical_processes?: string[];
  process_names?: string[];
  document?: string | null;
  document_title?: string | null;
  document_code?: string | null;
  document_status?: string | null;
  test_state?: BcpTestState;
  last_test_result?: BcpTestResult | null;
  can_approve?: boolean;
  test_frequency_value?: number;
  test_frequency_unit?: "days" | "weeks" | "months" | "years";
}

export interface BcpTestObjective {
  text: string;
  met: boolean;
}

export interface BcpTest {
  id: string;
  plan: string;
  plan_title: string;
  plant: string;
  test_date: string;
  result: BcpTestResult;
  test_type: BcpTestType;
  objectives: BcpTestObjective[];
  rto_achieved_hours: number | null;
  rpo_achieved_hours: number | null;
  participants_count: number;
  objectives_met_pct: number | null;
  evidences_count: number;
  evidence_items: BcpTestEvidence[];
  notes: string;
}

export interface BcpTestEvidence {
  id: string;
  title: string;
  evidence_type: string;
  valid_until: string | null;
  file_name: string | null;
}

export interface BcpTestWarning {
  code: "rto_over_mtpd" | "rto_over_target" | "rpo_over_target";
  process: string;
  achieved: number;
  target: number;
}

export interface BcpCoveragePlan {
  id: string;
  title: string;
  status: BcpPlan["status"];
  test_state: BcpTestState;
  last_test_date: string | null;
  next_test_date: string | null;
  last_test_result: BcpTestResult | null;
  rto_declared: number | null;
  rto_demonstrated: number | null;
  rto_measured: boolean;
}

export interface BcpCoverageRow {
  process_id: string;
  process_name: string;
  plant: string | null;
  criticality: number;
  rto_target_hours: number | null;
  rpo_target_hours: number | null;
  mtpd_hours: number | null;
  coverage: BcpCoverage;
  plans: BcpCoveragePlan[];
}

export const bcpApi = {
  list: (params?: Record<string, string>) =>
    fetchAllPages<BcpPlan>("/bcp/plans/", params).then((results) => ({ results, count: results.length })),
  approve: (id: string) =>
    apiClient.post<BcpPlan>(`/bcp/plans/${id}/approve/`).then(r => r.data),
  archive: (id: string) =>
    apiClient.post<BcpPlan>(`/bcp/plans/${id}/archive/`).then(r => r.data),
  coverage: (plantId?: string) =>
    apiClient
      .get<BcpCoverageRow[]>("/bcp/plans/coverage/", { params: plantId ? { plant: plantId } : undefined })
      .then(r => r.data),
  create: (data: Partial<BcpPlan>) =>
    apiClient.post<BcpPlan>("/bcp/plans/", data).then(r => r.data),
  update: (id: string, data: Partial<BcpPlan>) =>
    apiClient.patch<BcpPlan>(`/bcp/plans/${id}/`, data).then(r => r.data),
  tests: (params?: Record<string, string>) =>
    fetchAllPages<BcpTest>("/bcp/tests/", params),
  addTestEvidences: (id: string, data: { evidenceIds?: string[]; file?: File | null }) => {
    const fd = new FormData();
    fd.append("evidence_ids", JSON.stringify(data.evidenceIds ?? []));
    if (data.file) fd.append("evidence_file", data.file);
    return apiClient
      .post<BcpTest>(`/bcp/tests/${id}/evidences/`, fd, {
        headers: { "Content-Type": undefined as unknown as string },
      })
      .then(r => r.data);
  },
  deleteTest: (id: string) =>
    apiClient.delete(`/bcp/tests/${id}/`).then(() => undefined),
  recordTest: (data: Record<string, unknown> | FormData) => {
    const isForm = typeof FormData !== "undefined" && data instanceof FormData;
    return apiClient
      .post<{ test: BcpTest; warnings: BcpTestWarning[] }>(
        "/bcp/tests/",
        data,
        isForm ? { headers: { "Content-Type": undefined as unknown as string } } : undefined
      )
      .then(r => r.data);
  },
  delete: (id: string) =>
    apiClient.delete(`/bcp/plans/${id}/`).then(() => undefined),
};
