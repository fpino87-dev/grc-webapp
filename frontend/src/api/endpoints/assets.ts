import { apiClient } from "../client";

export interface AssetChangeFields {
  last_change_ref: string;
  last_change_date: string | null;
  last_change_desc: string;
  change_portal_url: string;
  needs_revaluation: boolean;
  needs_revaluation_since: string | null;
  has_recent_change: boolean;
  change_age_days: number | null;
}

export interface AssetIT extends AssetChangeFields {
  id: string; plant: string; name: string; asset_type: "IT";
  criticality: number; fqdn: string; ip_address: string | null;
  os: string; eol_date: string | null; internet_exposed: boolean;
  cve_score_max: number | null; owner: string | null; notes: string;
}
export interface AssetOT extends AssetChangeFields {
  id: string; plant: string; name: string; asset_type: "OT";
  criticality: number; purdue_level: number;
  category: "PLC"|"SCADA"|"HMI"|"RTU"|"sensore"|"altro";
  patchable: boolean; vendor: string; owner: string | null;
}

export interface RegisterChangeResult {
  ok: boolean; asset: string; ref: string;
  affected: { controls: number; risks: number; processes: number };
}

export const assetsApi = {
  listIT: (params?: Record<string,string>) =>
    apiClient.get<{results: AssetIT[]}>("/assets/it/", {params}).then(r => r.data),
  listOT: (params?: Record<string,string>) =>
    apiClient.get<{results: AssetOT[]}>("/assets/ot/", {params}).then(r => r.data),
  createIT: (data: Partial<AssetIT>) =>
    apiClient.post<AssetIT>("/assets/it/", data).then(r => r.data),
  createOT: (data: Partial<AssetOT>) =>
    apiClient.post<AssetOT>("/assets/ot/", data).then(r => r.data),
  registerChange: (id: string, type: "IT" | "OT", data: { change_ref: string; change_desc?: string; portal_url?: string }) =>
    apiClient.post<RegisterChangeResult>(`/assets/${type === "IT" ? "it" : "ot"}/${id}/register-change/`, data).then(r => r.data),
  clearRevaluation: (id: string, type: "IT" | "OT", notes?: string) =>
    apiClient.post<{ ok: boolean }>(`/assets/${type === "IT" ? "it" : "ot"}/${id}/clear-revaluation/`, { notes: notes ?? "" }).then(r => r.data),
  needsRevaluationIT: (plant?: string) =>
    apiClient.get<AssetIT[]>("/assets/it/needs-revaluation/", { params: plant ? { plant } : {} }).then(r => r.data),
};
