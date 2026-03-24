import { apiClient } from "../client";

export interface Plant {
  id: string;
  code: string;
  name: string;
  country: string;
  nis2_scope: "essenziale" | "importante" | "non_soggetto";
  status: "attivo" | "in_dismissione" | "chiuso";
  has_ot: boolean;
  logo_url?: string | null;
  nis2_sector?: string;
  nis2_subsector?: string;
  legal_entity_name?: string;
  legal_entity_vat?: string;
  nis2_activity_description?: string;
}

export interface BusinessUnit {
  id: string;
  code: string;
  name: string;
}

export interface PlantFramework {
  id: string;
  plant: string;
  framework: string;
  framework_code: string;
  framework_name: string;
  level: string;
  active: boolean;
  active_from: string;
}

export const plantsApi = {
  list: () => apiClient.get<{ results: Plant[] }>("/plants/plants/").then((r) => r.data.results),
  get: (id: string) => apiClient.get<Plant>(`/plants/plants/${id}/`).then((r) => r.data),
  create: (data: Partial<Plant>) => apiClient.post<Plant>("/plants/plants/", data).then((r) => r.data),
  update: (id: string, data: Partial<Plant>) => apiClient.patch<Plant>(`/plants/plants/${id}/`, data).then((r) => r.data),
  uploadLogo: (id: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return apiClient.post<Plant>(`/plants/plants/${id}/upload-logo/`, form, {
      headers: { "Content-Type": "multipart/form-data" },
    }).then((r) => r.data);
  },
  businessUnits: () =>
    apiClient.get<{ results: BusinessUnit[] }>("/plants/business-units/").then((r) => r.data.results),
  createBusinessUnit: (data: Partial<BusinessUnit>) =>
    apiClient.post<BusinessUnit>("/plants/business-units/", data).then((r) => r.data),
  plantFrameworks: (plantId: string) =>
    apiClient.get<{ results: PlantFramework[] }>("/plants/plant-frameworks/", { params: { plant: plantId } }).then((r) => r.data.results),
  assignFramework: (data: { plant: string; framework: string; level?: string }) =>
    apiClient.post<PlantFramework>("/plants/plant-frameworks/", data).then((r) => r.data),
  toggleFramework: (id: string) =>
    apiClient.post<PlantFramework>(`/plants/plant-frameworks/${id}/toggle_active/`).then((r) => r.data),
  removeFramework: (id: string) =>
    apiClient.delete(`/plants/plant-frameworks/${id}/`),
};
