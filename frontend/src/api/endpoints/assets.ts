import { apiClient } from "../client";

export interface AssetIT {
  id: string; plant: string; name: string; asset_type: "IT";
  criticality: number; fqdn: string; ip_address: string | null;
  os: string; eol_date: string | null; internet_exposed: boolean;
  cve_score_max: number | null; owner: string | null; notes: string;
}
export interface AssetOT {
  id: string; plant: string; name: string; asset_type: "OT";
  criticality: number; purdue_level: number;
  category: "PLC"|"SCADA"|"HMI"|"RTU"|"sensore"|"altro";
  patchable: boolean; vendor: string; owner: string | null;
}

export const assetsApi = {
  listIT: (params?: Record<string,string>) =>
    apiClient.get<{results: AssetIT[]}>("/assets/assets-it/", {params}).then(r => r.data),
  listOT: (params?: Record<string,string>) =>
    apiClient.get<{results: AssetOT[]}>("/assets/assets-ot/", {params}).then(r => r.data),
  createIT: (data: Partial<AssetIT>) =>
    apiClient.post<AssetIT>("/assets/assets-it/", data).then(r => r.data),
  createOT: (data: Partial<AssetOT>) =>
    apiClient.post<AssetOT>("/assets/assets-ot/", data).then(r => r.data),
};
