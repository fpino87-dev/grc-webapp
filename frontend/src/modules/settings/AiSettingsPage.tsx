import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { aiApi, type AiProviderConfig } from "../../api/endpoints/ai";
import { useAuthStore } from "../../store/auth";
import { ModuleHelp } from "../../components/ui/ModuleHelp";
import { useTranslation } from "react-i18next";

const TASKS = [
  "incident_classify",
  "gap_actions",
  "rca_draft",
  "review_summary",
  "chatbot",
  "cpv_suggestion",
  "generate_procedure",
  "cockpit_explain",
  "cockpit_assistant",
] as const;

export function AiSettingsPage() {
  const { t } = useTranslation();
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
    return <div className="p-6 text-sm text-gray-600">{t("ai.settings.insufficient_permissions")}</div>;
  }

  const cloudModels = catalog?.[form.cloud_provider] ?? [];
  const used = activeConfig?.tokens_used_month ?? 0;
  const budget = activeConfig?.monthly_token_budget ?? form.monthly_token_budget;
  const pct = budget > 0 ? Math.min(100, Math.round((used / budget) * 100)) : 100;

  return (
    <div className="p-6 max-w-4xl space-y-4">
      <div className="flex items-center gap-2">
        <h2 className="text-xl font-semibold">govrico AI</h2>
        <ModuleHelp
          title={t("ai.help.title")}
          description={t("ai.help.description")}
          steps={[
            t("ai.help.steps.1"),
            t("ai.help.steps.2"),
            t("ai.help.steps.3"),
            t("ai.help.steps.4"),
            t("ai.help.steps.5"),
            t("ai.help.steps.6"),
            t("ai.help.steps.7"),
          ]}
          connections={[
            { module: "M03 Controlli", relation: t("ai.help.connections.controls") },
            { module: "M06 Risk", relation: t("ai.help.connections.risk") },
            { module: "M09 Incidenti", relation: t("ai.help.connections.incidents") },
            { module: "M14 Fornitori", relation: t("ai.help.connections.suppliers") },
            { module: "OSINT Monitor", relation: t("ai.help.connections.osint") },
          ]}
          configNeeded={[
            t("ai.help.config_needed.1"),
            t("ai.help.config_needed.2"),
            t("ai.help.config_needed.3"),
          ]}
        />
      </div>

      {/* Provider Cloud */}
      <div className="bg-white border rounded p-4 space-y-3">
        <h3 className="font-medium">{t("ai.settings.provider_cloud")}</h3>
        <div className="grid grid-cols-2 gap-3">
          <select
            className="border rounded px-2 py-2 text-sm"
            value={form.cloud_provider}
            onChange={(e) => {
              const newProvider = e.target.value;
              const firstModel = catalog?.[newProvider]?.[0]?.[0] ?? "";
              setForm((f) => ({ ...f, cloud_provider: newProvider, cloud_model: firstModel }));
            }}
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
              placeholder={apiKeyMasked ? t("ai.settings.api_key_ph_saved") : t("ai.settings.api_key_ph_new")}
              value={form.api_key ?? ""}
              onChange={(e) => {
                setApiKeyMasked(false);
                setForm((f) => ({ ...f, api_key: e.target.value }));
              }}
            />
            {apiKeyMasked && (
              <span className="absolute right-2 top-1/2 -translate-y-1/2 text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">
                ✓ {t("ai.settings.saved_badge")}
              </span>
            )}
          </div>
          {apiKeyMasked && (
            <p className="text-xs text-gray-400">{t("ai.settings.key_encrypted_hint")}</p>
          )}
        </div>

        {/* Tasto test cloud */}
        <button
          onClick={() => { setTestResult(null); testMutation.mutate(); }}
          disabled={testMutation.isPending || !activeConfig?.id}
          className="px-3 py-1.5 border border-indigo-300 text-indigo-700 rounded text-sm hover:bg-indigo-50 disabled:opacity-40"
        >
          {testMutation.isPending ? t("ai.settings.testing") : `🔌 ${t("ai.settings.test_button")}`}
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
                  ? <span className="text-gray-600">{res.response}{res.tokens ? ` — ${res.tokens} ${t("ai.settings.token_unit")}` : ""}</span>
                  : <span className="text-red-500">{res.error}</span>
                }
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Provider Locale */}
      <div className="bg-white border rounded p-4 space-y-3">
        <h3 className="font-medium">{t("ai.settings.provider_local")}</h3>
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
        <h3 className="font-medium">{t("ai.settings.budget_token")}</h3>
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
          {t("ai.settings.reset_budget")}
        </button>
      </div>

      {/* Routing per Task */}
      <div className="bg-white border rounded p-4 space-y-3">
        <h3 className="font-medium">{t("ai.settings.routing_per_task")}</h3>
        <div className="space-y-2">
          {TASKS.map((task) => (
            <div key={task} className="grid grid-cols-3 gap-2 items-center text-sm">
              <div>{t(`ai.settings.tasks.${task}`)}</div>
              <select
                className="border rounded px-2 py-1.5"
                value={form.task_routing?.[task] ?? (task === "incident_classify" ? "ollama" : "cloud")}
                onChange={(e) => setForm((f) => ({ ...f, task_routing: { ...(f.task_routing ?? {}), [task]: e.target.value as "cloud" | "ollama" } }))}
              >
                <option value="ollama">{t("ai.settings.local")}</option>
                <option value="cloud">{t("ai.settings.cloud")}</option>
              </select>
              <div className="text-xs text-gray-500">{t("ai.settings.fallback_ollama")}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Fallback */}
      <div className="bg-white border rounded p-4 space-y-3">
        <h3 className="font-medium">{t("ai.settings.fallback")}</h3>
        <select
          className="border rounded px-2 py-2 text-sm"
          value={form.fallback_mode}
          onChange={(e) => setForm((f) => ({ ...f, fallback_mode: e.target.value as AiProviderConfig["fallback_mode"] }))}
        >
          <option value="auto">{t("ai.settings.fallback_auto")}</option>
          <option value="notify">{t("ai.settings.fallback_notify")}</option>
          <option value="disabled">{t("ai.settings.fallback_disabled")}</option>
        </select>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={() => saveMutation.mutate()}
          disabled={saveMutation.isPending}
          className="px-4 py-2 bg-indigo-600 text-white rounded text-sm disabled:opacity-50"
        >
          {saveMutation.isPending ? t("ai.settings.saving") : t("ai.settings.save_config")}
        </button>
        {saveMutation.isSuccess && (
          <span className="text-sm text-green-600">✓ {t("ai.settings.saved")}</span>
        )}
        {saveMutation.isError && (
          <span className="text-sm text-red-500">{t("ai.settings.save_error")}</span>
        )}
      </div>
    </div>
  );
}
