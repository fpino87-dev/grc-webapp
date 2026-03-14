import { apiClient } from "../client";

export interface MappedControl {
  external_id: string;
  framework_code: string;
  relationship: string;
}

export interface ControlInstance {
  id: string;
  plant: string;
  control: string;
  control_external_id: string;
  control_title: string;
  framework_code: string;
  status: "compliant" | "parziale" | "gap" | "na" | "non_valutato";
  owner: string | null;
  notes: string;
  last_evaluated_at: string | null;
  mapped_controls: MappedControl[];
}

export interface Framework {
  id: string;
  code: string;
  name: string;
  version: string;
}

export const controlsApi = {
  instances: (params?: Record<string, string>) =>
    apiClient.get<{ results: ControlInstance[]; count: number }>("/controls/instances/", { params: { page_size: "500", ...params } }).then((r) => r.data),
  frameworks: () =>
    apiClient.get<{ results: Framework[] }>("/controls/frameworks/").then((r) => r.data.results),
  updateInstance: (id: string, data: Partial<ControlInstance>) =>
    apiClient.patch<ControlInstance>(`/controls/instances/${id}/`, data).then((r) => r.data),
  propagate: (id: string) =>
    apiClient.post<{ propagated_to: number }>(`/controls/instances/${id}/propagate/`).then((r) => r.data),
};
