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
    local_endpoint: "http://172.17.0.1:11434",
    local_model: "llama3.2:3b",
    monthly_token_budget: 100000,
    budget_reset_day: 1,
    fallback_mode: "auto",
    task_routing: {},
  });

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
      setForm({
        ...activeConfig,
        api_key: "",
      });
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

      <div className="bg-white border rounded p-4 space-y-3">
        <h3 className="font-medium">Provider Cloud</h3>
        <div className="grid grid-cols-2 gap-3">
          <select className="border rounded px-2 py-2 text-sm" value={form.cloud_provider} onChange={(e) => setForm((f) => ({ ...f, cloud_provider: e.target.value }))}>
            {Object.keys(catalog ?? {}).filter((k) => k !== "ollama").map((provider) => (
              <option key={provider} value={provider}>{provider}</option>
            ))}
          </select>
          <select className="border rounded px-2 py-2 text-sm" value={form.cloud_model} onChange={(e) => setForm((f) => ({ ...f, cloud_model: e.target.value }))}>
            {cloudModels.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </div>
        <input type="password" className="w-full border rounded px-2 py-2 text-sm" placeholder="API key (lascia vuoto per non modificare)" value={form.api_key ?? ""} onChange={(e) => setForm((f) => ({ ...f, api_key: e.target.value }))} />
      </div>

      <div className="bg-white border rounded p-4 space-y-3">
        <h3 className="font-medium">Provider Locale (Ollama)</h3>
        <input className="w-full border rounded px-2 py-2 text-sm" value={form.local_endpoint} onChange={(e) => setForm((f) => ({ ...f, local_endpoint: e.target.value }))} />
        <select className="border rounded px-2 py-2 text-sm" value={form.local_model} onChange={(e) => setForm((f) => ({ ...f, local_model: e.target.value }))}>
          {(catalog?.ollama ?? []).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
        <button onClick={() => testMutation.mutate()} className="px-3 py-1.5 border rounded text-sm">Testa connessione</button>
      </div>

      <div className="bg-white border rounded p-4 space-y-3">
        <h3 className="font-medium">Budget Token</h3>
        <input type="number" className="border rounded px-2 py-2 text-sm" value={form.monthly_token_budget} onChange={(e) => setForm((f) => ({ ...f, monthly_token_budget: Number(e.target.value) }))} />
        <div className="w-full bg-gray-100 h-2 rounded">
          <div className="bg-indigo-600 h-2 rounded" style={{ width: `${pct}%` }} />
        </div>
        <p className="text-xs text-gray-600">{used} / {budget} ({pct}%)</p>
        <button onClick={() => resetMutation.mutate()} className="px-3 py-1.5 border rounded text-sm">Reset manuale budget</button>
      </div>

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

      <div className="bg-white border rounded p-4 space-y-3">
        <h3 className="font-medium">Fallback</h3>
        <select className="border rounded px-2 py-2 text-sm" value={form.fallback_mode} onChange={(e) => setForm((f) => ({ ...f, fallback_mode: e.target.value as AiProviderConfig["fallback_mode"] }))}>
          <option value="auto">Automatico</option>
          <option value="notify">Notifica</option>
          <option value="disabled">Disabilitato</option>
        </select>
      </div>

      <button onClick={() => saveMutation.mutate()} className="px-4 py-2 bg-indigo-600 text-white rounded text-sm">
        Salva configurazione
      </button>
    </div>
  );
}
