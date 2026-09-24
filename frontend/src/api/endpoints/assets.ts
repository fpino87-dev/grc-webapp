import { apiClient } from "../client";
import { fetchAllPages } from "../pagination";

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

export interface AssetIT extends AssetChangeFields, Partial<MaintenanceFields> {
  id: string;
  plant: string;
  name: string;
  asset_type: "IT";
  criticality: number;
  fqdn: string;
  ip_address: string | null;
  os: string;
  eol_date: string | null;
  internet_exposed: boolean;
  cve_score_max: number | null;
  owner: string | null;
  maintainer_supplier: string | null;
  notes: string;
  processes: string[];
  deployment_type: "on_prem" | "iaas" | "paas" | "saas";
  provider: string | null;
  service_name: string | null;
  data_classification: string | null;
}

/** Manutenzione periodica: campi comuni a ogni tipo di asset.
 *  La cadenza è configurazione e si scrive; data ed esito dell'ultima
 *  manutenzione li governa l'azione record-maintenance. */
export interface MaintenanceFields {
  maintenance_frequency_months: number | null;
  last_maintenance_date: string | null;
  next_maintenance_date: string | null;
  last_maintenance_result: "superata" | "con_riserve" | "fallita" | "";
  maintenance_notes: string;
  maintenance_is_overdue: boolean;
}

export type FacilityCategory =
  | "ups"
  | "gruppo_elettrogeno"
  | "antincendio"
  | "climatizzazione"
  | "controllo_accessi"
  | "videosorveglianza"
  | "altro";

export const FACILITY_CATEGORIES: FacilityCategory[] = [
  "ups",
  "gruppo_elettrogeno",
  "antincendio",
  "climatizzazione",
  "controllo_accessi",
  "videosorveglianza",
  "altro",
];

/** Impianti di supporto: continuità elettrica, antincendio, climatizzazione,
 *  sicurezza fisica. Le misure (autonomia rilevata, temperature) non stanno
 *  qui: sono rilevazioni e vivono nelle checklist. */
export interface AssetFacility extends MaintenanceFields {
  id: string;
  plant: string;
  plant_name?: string;
  name: string;
  asset_type: "FAC";
  category: FacilityCategory;
  category_display?: string;
  criticality: number;
  owner: string | null;
  owner_username?: string | null;
  maintainer_supplier: string | null;
  maintainer_supplier_name?: string | null;
  location: string;
  vendor: string;
  model: string;
  serial_number: string;
  installation_date: string | null;
  rated_autonomy_minutes: number | null;
  serves_assets: string[];
  notes: string;
  created_at?: string;
  updated_at?: string;
}

export interface AssetOT extends AssetChangeFields, Partial<MaintenanceFields> {
  id: string;
  plant: string;
  name: string;
  asset_type: "OT";
  criticality: number;
  purdue_level: number;
  category: "PLC" | "SCADA" | "HMI" | "RTU" | "sensore" | "altro";
  patchable: boolean;
  vendor: string;
  fqdn: string;
  ip_address: string | null;
  internet_exposed: boolean;
  owner: string | null;
  maintainer_supplier: string | null;
  notes: string;
  processes: string[];
}

export interface AssetSW extends Partial<MaintenanceFields> {
  id: string;
  plant: string;
  plant_name: string;
  name: string;
  asset_type: "SW";
  criticality: number;
  vendor: string;
  version: string;
  approval_status: "approvato" | "in_valutazione" | "deprecato" | "vietato";
  license_type: "commerciale" | "open_source" | "saas" | "freeware" | "";
  end_of_support: string | null;
  external_ref: string;
  is_eos: boolean;
  days_to_eos: number | null;
  owner: string | null;
  owner_username: string | null;
  notes: string;
  processes: string[];
  created_at: string;
  updated_at: string;
}

export interface RegisterChangeResult {
  ok: boolean; asset: string; ref: string;
  affected: { controls: number; risks: number; processes: number };
}

export const assetsApi = {
  listIT: (params?: Record<string,string>) =>
    fetchAllPages<AssetIT>("/assets/it/", params).then((results) => ({ results, count: results.length })),
  listOT: (params?: Record<string,string>) =>
    fetchAllPages<AssetOT>("/assets/ot/", params).then((results) => ({ results, count: results.length })),
  createIT: (data: Partial<AssetIT>) =>
    apiClient.post<AssetIT>("/assets/it/", data).then(r => r.data),
  createOT: (data: Partial<AssetOT>) =>
    apiClient.post<AssetOT>("/assets/ot/", data).then(r => r.data),
  updateIT: (id: string, data: Partial<AssetIT>) =>
    apiClient.patch<AssetIT>(`/assets/it/${id}/`, data).then(r => r.data),
  updateOT: (id: string, data: Partial<AssetOT>) =>
    apiClient.patch<AssetOT>(`/assets/ot/${id}/`, data).then(r => r.data),
  registerChange: (id: string, type: "IT" | "OT", data: { change_ref: string; change_desc?: string; portal_url?: string }) =>
    apiClient.post<RegisterChangeResult>(`/assets/${type === "IT" ? "it" : "ot"}/${id}/register-change/`, data).then(r => r.data),
  clearRevaluation: (id: string, type: "IT" | "OT", notes?: string) =>
    apiClient.post<{ ok: boolean }>(`/assets/${type === "IT" ? "it" : "ot"}/${id}/clear-revaluation/`, { notes: notes ?? "" }).then(r => r.data),
  needsRevaluationIT: (plant?: string) =>
    apiClient.get<AssetIT[]>("/assets/it/needs-revaluation/", { params: plant ? { plant } : {} }).then(r => r.data),
  listFacility: (params?: Record<string, string>) =>
    fetchAllPages<AssetFacility>("/assets/facility/", params).then((results) => ({ results, count: results.length })),
  createFacility: (data: Partial<AssetFacility>) =>
    apiClient.post<AssetFacility>("/assets/facility/", data).then(r => r.data),
  updateFacility: (id: string, data: Partial<AssetFacility>) =>
    apiClient.patch<AssetFacility>(`/assets/facility/${id}/`, data).then(r => r.data),
  deleteFacility: (id: string) =>
    apiClient.delete(`/assets/facility/${id}/`).then(r => r.data),
  /** Registra l'esecuzione di una manutenzione: sposta avanti la scadenza
   *  successiva e scrive l'audit trail. `type` è il segmento di rotta. */
  recordMaintenance: (
    type: "it" | "ot" | "sw" | "facility",
    id: string,
    data: { date?: string; result?: string; notes?: string },
  ) =>
    apiClient.post(`/assets/${type}/${id}/record-maintenance/`, data).then(r => r.data),
  listSW: (params?: Record<string, string>) =>
    fetchAllPages<AssetSW>("/assets/sw/", params).then((results) => ({ results, count: results.length })),
  createSW: (data: Partial<AssetSW>) =>
    apiClient.post<AssetSW>("/assets/sw/", data).then(r => r.data),
  updateSW: (id: string, data: Partial<AssetSW>) =>
    apiClient.patch<AssetSW>(`/assets/sw/${id}/`, data).then(r => r.data),
  deleteIT: (id: string) => apiClient.delete(`/assets/it/${id}/`),
  deleteOT: (id: string) => apiClient.delete(`/assets/ot/${id}/`),
  deleteSW: (id: string) => apiClient.delete(`/assets/sw/${id}/`),
};
