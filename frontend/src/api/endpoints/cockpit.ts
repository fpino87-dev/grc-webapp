import { apiClient } from "../client";

export type InsightSeverity = "critical" | "warning" | "info";
export type CockpitArea =
  | "governance" | "controls" | "risk" | "incidents"
  | "supply_chain" | "technical" | "continuity";

export interface CockpitInsight {
  code: string;
  module: string;
  severity: InsightSeverity;
  area: CockpitArea;
  action_type: string;
  plant_id: string | null;
  entity_ref: { type: string; id: string; deep_link: string | null } | null;
  params: Record<string, unknown>;
  compliance_refs: { framework: string; control: string }[];
  effort_h: number | null;
  deadline: string | null;
  owner_role: string;
  fingerprint: string;
  state: { status: string; snoozed_until: string | null; accepted_until: string | null; note: string } | null;
}

export interface PostureArea {
  score: number;
  critical: number;
  warning: number;
  info: number;
}

export interface CockpitResponse {
  insights: CockpitInsight[];
  counts: { critical: number; warning: number; info: number; total: number };
  posture: { total: number; areas: Record<string, PostureArea> };
  suppressed_count: number;
  suppressed?: CockpitInsight[];
}

export interface PosturePoint {
  date: string;
  total: number;
  counts: { critical: number; warning: number; info: number; total: number };
}

export type InsightAction = "snooze" | "accept" | "reopen";

export const cockpitApi = {
  insights: (plant?: string, opts?: { mine?: boolean; includeSuppressed?: boolean }) =>
    apiClient
      .get<CockpitResponse>("/cockpit/insights/", {
        params: {
          ...(plant ? { plant } : {}),
          ...(opts?.mine ? { mine: 1 } : {}),
          ...(opts?.includeSuppressed ? { include_suppressed: 1 } : {}),
        },
      })
      .then(r => r.data),
  action: (fingerprint: string, action: InsightAction, body?: { until?: string; note?: string }) =>
    apiClient.post(`/cockpit/insights/${fingerprint}/${action}/`, body ?? {}).then(r => r.data),
  trend: (plant?: string, days = 90) =>
    apiClient
      .get<{ points: PosturePoint[] }>("/cockpit/posture-trend/", {
        params: { ...(plant ? { plant } : {}), days },
      })
      .then(r => r.data.points),
  explain: (fingerprint: string) =>
    apiClient.post<{ text: string; provider: string; used_fallback: boolean }>(`/cockpit/insights/${fingerprint}/explain/`, {}).then(r => r.data),
  assistant: (question: string, plant?: string) =>
    apiClient.post<{ text: string }>("/cockpit/assistant/", { question, ...(plant ? { plant } : {}) }).then(r => r.data.text),
};
