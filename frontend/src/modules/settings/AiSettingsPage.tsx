import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { aiApi, type AiProviderConfig } from "../../api/endpoints/ai";
import { useAuthStore } from "../../store/auth";

const TASKS = [
  ["incident_classify", "Classificazione incidente"],
  ["gap_actions", "Azioni correttive gap"],
  ["rca_draft", "Bozza RCA"],
  ["review_summary", "Sintesi Management Review"],
  ["chatbot", "Chatbot"],
] as const;

export function AiSettingsPage() {
  const role = useAuthStore((s) => s.user?.role);
  const qc = useQueryClient();
  const [form, setForm] = useState<AiProviderConfig>({
    cloud_provider: "anthropic",
    cloud_model: "claude-haiku-4-5-20251001",
    api_key: "",
    local_endpoint: "http://host.docker.internal:11434",
    local_model: "llama3.2:3b",
    monthly_token_budget: 100000,
    budget_reset_day: 1,
    fallback_mode: "auto",
    task_routing: {},
  });
  // "********" = key già salvata, non modificata dall'utente
  const [apiKeyMasked, setApiKeyMasked] = useState(false);
  const [testResult, setTestResult] = useState<Record<string, { ok: boolean; response?: string; error?: string; tokens?: number }> | null>(null);

  const { data: catalog } = useQuery({
    queryKey: ["ai-models-catalog"],
    queryFn: aiApi.modelsCatalog,
  });
  const { data: configs } = useQuery({
    queryKey: ["ai-configs"],
    queryFn: aiApi.listConfig,
  });
  const activeConfig = useMemo(() => configs?.find((c) => c.active) ?? configs?.[0], [configs]);

  useEffect(() => {
    if (activeConfig) {
      setForm({ ...activeConfig, api_key: "" });
      // Se il backend torna "********" significa che la key è salvata
      setApiKeyMasked(activeConfig.api_key === "********");
    }
  }, [activeConfig]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (activeConfig?.id) return aiApi.updateConfig(activeConfig.id, form);
      return aiApi.createConfig(form);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ai-configs"] }),
  });

  const testMutation = useMutation({
    mutationFn: async () => {
      if (!activeConfig?.id) return null;
      return aiApi.testConnection(activeConfig.id);
    },
    onSuccess: (data) => setTestResult(data),
  });

  const resetMutation = useMutation({
    mutationFn: async () => {
      if (!activeConfig?.id) return null;
      return aiApi.resetBudget(activeConfig.id);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ai-configs"] }),
  });

  if (role !== "super_admin" && role !== "compliance_officer") {
    return <div className="p-6 text-sm text-gray-600">Permessi insufficienti.</div>;
  }

  const cloudModels = catalog?.[form.cloud_provider] ?? [];
  const used = activeConfig?.tokens_used_month ?? 0;
  const budget = activeConfig?.monthly_token_budget ?? form.monthly_token_budget;
  const pct = budget > 0 ? Math.min(100, Math.round((used / budget) * 100)) : 100;

  return (
    <div className="p-6 max-w-4xl space-y-4">
      <h2 className="text-xl font-semibold">AI Engine</h2>

      {/* Provider Cloud */}
      <div className="bg-white border rounded p-4 space-y-3">
        <h3 className="font-medium">Provider Cloud</h3>
        <div className="grid grid-cols-2 gap-3">
          <select
            className="border rounded px-2 py-2 text-sm"
            value={form.cloud_provider}
            onChange={(e) => setForm((f) => ({ ...f, cloud_provider: e.target.value }))}
          >
            {Object.keys(catalog ?? {}).filter((k) => k !== "ollama").map((provider) => (
              <option key={provider} value={provider}>{provider}</option>
            ))}
          </select>
          <select
            className="border rounded px-2 py-2 text-sm"
            value={form.cloud_model}
            onChange={(e) => setForm((f) => ({ ...f, cloud_model: e.target.value }))}
          >
            {cloudModels.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </div>

        {/* API Key con indicatore stato */}
        <div className="space-y-1">
          <div className="relative">
            <input
              type="password"
              className="w-full border rounded px-2 py-2 text-sm pr-24"
              placeholder={apiKeyMasked ? "••••••••  (key salvata — digita per modificare)" : "Inserisci API key"}
              value={form.api_key ?? ""}
              onChange={(e) => {
                setApiKeyMasked(false);
                setForm((f) => ({ ...f, api_key: e.target.value }));
              }}
            />
            {apiKeyMasked && (
              <span className="absolute right-2 top-1/2 -translate-y-1/2 text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">
                ✓ salvata
              </span>
            )}
          </div>
          {apiKeyMasked && (
            <p className="text-xs text-gray-400">La key è cifrata nel DB. Lascia vuoto per non modificarla.</p>
          )}
        </div>

        {/* Tasto test cloud */}
        <button
          onClick={() => { setTestResult(null); testMutation.mutate(); }}
          disabled={testMutation.isPending || !activeConfig?.id}
          className="px-3 py-1.5 border border-indigo-300 text-indigo-700 rounded text-sm hover:bg-indigo-50 disabled:opacity-40"
        >
          {testMutation.isPending ? "Test in corso..." : "🔌 Testa API Cloud & Ollama"}
        </button>

        {/* Risultati test */}
        {testResult && (
          <div className="mt-2 space-y-1 text-xs border rounded p-3 bg-gray-50">
            {Object.entries(testResult).map(([target, res]) => (
              <div key={target} className="flex items-start gap-2">
                <span className={res.ok ? "text-green-600 font-bold" : "text-red-500 font-bold"}>
                  {res.ok ? "✓" : "✗"}
                </span>
                <span className="font-medium w-12">{target}</span>
                {res.ok
                  ? <span className="text-gray-600">{res.response}{res.tokens ? ` — ${res.tokens} token` : ""}</span>
                  : <span className="text-red-500">{res.error}</span>
                }
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Provider Locale */}
      <div className="bg-white border rounded p-4 space-y-3">
        <h3 className="font-medium">Provider Locale (Ollama)</h3>
        <input
          className="w-full border rounded px-2 py-2 text-sm"
          value={form.local_endpoint}
          onChange={(e) => setForm((f) => ({ ...f, local_endpoint: e.target.value }))}
        />
        <select
          className="border rounded px-2 py-2 text-sm"
          value={form.local_model}
          onChange={(e) => setForm((f) => ({ ...f, local_model: e.target.value }))}
        >
          {(catalog?.ollama ?? []).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      </div>

      {/* Budget Token */}
      <div className="bg-white border rounded p-4 space-y-3">
        <h3 className="font-medium">Budget Token</h3>
        <input
          type="number"
          className="border rounded px-2 py-2 text-sm"
          value={form.monthly_token_budget}
          onChange={(e) => setForm((f) => ({ ...f, monthly_token_budget: Number(e.target.value) }))}
        />
        <div className="w-full bg-gray-100 h-2 rounded">
          <div className="bg-indigo-600 h-2 rounded" style={{ width: `${pct}%` }} />
        </div>
        <p className="text-xs text-gray-600">{used} / {budget} ({pct}%)</p>
        <button
          onClick={() => resetMutation.mutate()}
          className="px-3 py-1.5 border rounded text-sm"
        >
          Reset manuale budget
        </button>
      </div>

      {/* Routing per Task */}
      <div className="bg-white border rounded p-4 space-y-3">
        <h3 className="font-medium">Routing per Task</h3>
        <div className="space-y-2">
          {TASKS.map(([task, label]) => (
            <div key={task} className="grid grid-cols-3 gap-2 items-center text-sm">
              <div>{label}</div>
              <select
                className="border rounded px-2 py-1.5"
                value={form.task_routing?.[task] ?? (task === "incident_classify" ? "ollama" : "cloud")}
                onChange={(e) => setForm((f) => ({ ...f, task_routing: { ...(f.task_routing ?? {}), [task]: e.target.value as "cloud" | "ollama" } }))}
              >
                <option value="ollama">Locale</option>
                <option value="cloud">Cloud</option>
              </select>
              <div className="text-xs text-gray-500">Fallback: Ollama</div>
            </div>
          ))}
        </div>
      </div>

      {/* Fallback */}
      <div className="bg-white border rounded p-4 space-y-3">
        <h3 className="font-medium">Fallback</h3>
        <select
          className="border rounded px-2 py-2 text-sm"
          value={form.fallback_mode}
          onChange={(e) => setForm((f) => ({ ...f, fallback_mode: e.target.value as AiProviderConfig["fallback_mode"] }))}
        >
          <option value="auto">Automatico</option>
          <option value="notify">Notifica</option>
          <option value="disabled">Disabilitato</option>
        </select>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={() => saveMutation.mutate()}
          disabled={saveMutation.isPending}
          className="px-4 py-2 bg-indigo-600 text-white rounded text-sm disabled:opacity-50"
        >
          {saveMutation.isPending ? "Salvataggio..." : "Salva configurazione"}
        </button>
        {saveMutation.isSuccess && (
          <span className="text-sm text-green-600">✓ Salvato</span>
        )}
        {saveMutation.isError && (
          <span className="text-sm text-red-500">Errore nel salvataggio</span>
        )}
      </div>
    </div>
  );
}
