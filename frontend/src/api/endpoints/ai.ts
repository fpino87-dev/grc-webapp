import { apiClient } from "../client";

export interface AiSuggestResponse {
  task_type: string;
  provider: string;
  model: string;
  used_fallback: boolean;
  interaction_id: string | null;
  result: unknown;
}

export interface AssistantGap {
  kind: string;
  category: "documents" | "controls" | "risk" | "suppliers";
  ref_id: string;
  title: string;
  subtitle: string;
  details: Record<string, unknown>;
  priority_score: number;
  urgency: "red" | "yellow" | "green";
  frontend_url: string;
}

export interface AssistantStartResponse {
  plant: { id: string; code: string; name: string };
  summary: {
    plant_id: string;
    plant_name: string;
    frameworks: Array<{
      code: string;
      name: string;
      total: number;
      compliant: number;
      compliant_direct: number;
      covered_by_extender: number;
      gap: number;
      parziale: number;
      non_valutato: number;
      na_excluded: number;
      pct_compliant: number;
    }>;
  };
  gaps: AssistantGap[];
  gaps_total: number;
  gaps_truncated: boolean;
}

export interface AssistantExplainResponse {
  explanation: string;
  interaction_id: string | null;
  provider: string;
  model: string;
  used_fallback: boolean;
}

export interface AiProviderConfig {
  id?: string;
  name?: string;
  active?: boolean;
  cloud_provider: string;
  cloud_model: string;
  api_key?: string;
  local_endpoint: string;
  local_model: string;
  monthly_token_budget: number;
  tokens_used_month?: number;
  budget_reset_day: number;
  fallback_mode: "auto" | "notify" | "disabled";
  task_routing: Record<string, "cloud" | "ollama">;
}

export const aiApi = {
  suggest: (task_type: string, entity_id: string) =>
    apiClient.post<AiSuggestResponse>("/ai/suggest/", { task_type, entity_id }).then((r) => r.data),
  confirm: (interaction_id: string, final_text: string) =>
    apiClient.post("/ai/confirm/", { interaction_id, action: "confirm", final_text }).then((r) => r.data),
  ignore: (interaction_id: string) =>
    apiClient.post("/ai/confirm/", { interaction_id, action: "ignore" }).then((r) => r.data),
  listConfig: () => apiClient.get<{ results: AiProviderConfig[] }>("/ai/config/").then((r) => r.data.results),
  createConfig: (payload: AiProviderConfig) => apiClient.post<AiProviderConfig>("/ai/config/", payload).then((r) => r.data),
  updateConfig: (id: string, payload: Partial<AiProviderConfig>) =>
    apiClient.patch<AiProviderConfig>(`/ai/config/${id}/`, payload).then((r) => r.data),
  modelsCatalog: () => apiClient.get<Record<string, [string, string][]>>("/ai/config/models-catalog/").then((r) => r.data),
  testConnection: (id: string) => apiClient.post(`/ai/config/${id}/test-connection/`, {}).then((r) => r.data),
  resetBudget: (id: string) => apiClient.post(`/ai/config/${id}/reset-budget/`, {}).then((r) => r.data),
  assistant: {
    start: (plant_id: string) =>
      apiClient
        .post<AssistantStartResponse>("/ai/assistant/start/", { plant_id })
        .then((r) => r.data),
    explain: (plant_id: string, gap: AssistantGap) =>
      apiClient
        .post<AssistantExplainResponse>("/ai/assistant/explain/", { plant_id, gap })
        .then((r) => r.data),
  },
};
