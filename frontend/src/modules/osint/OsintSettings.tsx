import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { osintApi, type ScanFrequency } from "../../api/endpoints/osint";
import { ModuleHelp } from "../../components/ui/ModuleHelp";

type SubdomainPolicy = "yes" | "no" | "ask";

const FREQ_OPTIONS: ScanFrequency[] = ["weekly", "monthly"];
const SUBDOMAIN_OPTIONS: SubdomainPolicy[] = ["yes", "no", "ask"];

export function OsintSettingsPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [saved, setSaved] = useState(false);

  const [form, setForm] = useState({
    score_threshold_critical: 70,
    score_threshold_warning: 50,
    score_threshold_attention: 30,
    weight_ssl: 25,
    weight_dns: 25,
    weight_reputation: 30,
    weight_grc: 20,
    ssl_expiry_warning_days: 60,
    freq_my_domains: "weekly" as ScanFrequency,
    freq_suppliers_critical: "weekly" as ScanFrequency,
    freq_suppliers_other: "monthly" as ScanFrequency,
    subdomain_auto_include: "ask" as SubdomainPolicy,
    anonymization_enabled: true,
    ct_monitoring_enabled: true,
    ct_lookback_days: 30,
    ct_expected_issuers_text: "",
    hibp_api_key: "",
    virustotal_api_key: "",
    abuseipdb_api_key: "",
    gsb_api_key: "",
    otx_api_key: "",
    abusech_api_key: "",
  });

  const { data: settings, isLoading } = useQuery({
    queryKey: ["osint-settings"],
    queryFn: osintApi.settings,
  });

  useEffect(() => {
    if (settings) {
      setForm(prev => ({
        ...prev,
        score_threshold_critical: settings.score_threshold_critical,
        score_threshold_warning: settings.score_threshold_warning,
        score_threshold_attention: settings.score_threshold_attention,
        weight_ssl: settings.weight_ssl,
        weight_dns: settings.weight_dns,
        weight_reputation: settings.weight_reputation,
        weight_grc: settings.weight_grc,
        ssl_expiry_warning_days: settings.ssl_expiry_warning_days,
        freq_my_domains: settings.freq_my_domains,
        freq_suppliers_critical: settings.freq_suppliers_critical,
        freq_suppliers_other: settings.freq_suppliers_other,
        subdomain_auto_include: settings.subdomain_auto_include,
        anonymization_enabled: settings.anonymization_enabled,
        ct_monitoring_enabled: settings.ct_monitoring_enabled,
        ct_lookback_days: settings.ct_lookback_days,
        ct_expected_issuers_text: (settings.ct_expected_issuers || []).join(", "),
      }));
    }
  }, [settings]);

  const saveMutation = useMutation({
    mutationFn: () => {
      const payload: Record<string, unknown> = {
        score_threshold_critical: form.score_threshold_critical,
        score_threshold_warning: form.score_threshold_warning,
        score_threshold_attention: form.score_threshold_attention,
        weight_ssl: form.weight_ssl,
        weight_dns: form.weight_dns,
        weight_reputation: form.weight_reputation,
        weight_grc: form.weight_grc,
        ssl_expiry_warning_days: form.ssl_expiry_warning_days,
        freq_my_domains: form.freq_my_domains,
        freq_suppliers_critical: form.freq_suppliers_critical,
        freq_suppliers_other: form.freq_suppliers_other,
        subdomain_auto_include: form.subdomain_auto_include,
        anonymization_enabled: form.anonymization_enabled,
        ct_monitoring_enabled: form.ct_monitoring_enabled,
        ct_lookback_days: form.ct_lookback_days,
        ct_expected_issuers: form.ct_expected_issuers_text
          .split(/[,\n]/)
          .map(s => s.trim())
          .filter(Boolean),
      };
      if (form.hibp_api_key) payload.hibp_api_key = form.hibp_api_key;
      if (form.virustotal_api_key) payload.virustotal_api_key = form.virustotal_api_key;
      if (form.abuseipdb_api_key) payload.abuseipdb_api_key = form.abuseipdb_api_key;
      if (form.gsb_api_key) payload.gsb_api_key = form.gsb_api_key;
      if (form.otx_api_key) payload.otx_api_key = form.otx_api_key;
      if (form.abusech_api_key) payload.abusech_api_key = form.abusech_api_key;
      return osintApi.updateSettings(payload);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["osint-settings"] });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    },
  });

  const [testingProvider, setTestingProvider] = useState<string | null>(null);
  const testMutation = useMutation({
    mutationFn: (provider?: string) => osintApi.testKeys(provider),
    onSettled: () => {
      setTestingProvider(null);
      qc.invalidateQueries({ queryKey: ["osint-settings"] });
    },
  });

  function set<K extends keyof typeof form>(k: K, v: (typeof form)[K]) {
    setForm(prev => ({ ...prev, [k]: v }));
  }

  if (isLoading) {
    return <div className="p-6 text-gray-400">{t("common.loading")}</div>;
  }

  return (
    <div className="p-4 sm:p-6 max-w-3xl space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link to="/osint" className="text-sm text-gray-500 hover:text-gray-700">← {t("osint.title")}</Link>
        <span className="text-gray-300">/</span>
        <h1 className="text-xl font-bold text-gray-900">{t("osint.settings.title")}</h1>
        <ModuleHelp
          title={t("osint.help.title")}
          description={t("osint.help.description")}
          steps={[
            t("osint.help.steps.1"),
            t("osint.help.steps.2"),
            t("osint.help.steps.3"),
            t("osint.help.steps.4"),
            t("osint.help.steps.5"),
            t("osint.help.steps.6"),
          ]}
          connections={[
            { module: "Plants", relation: t("osint.help.connections.plants") },
            { module: "M14 Fornitori", relation: t("osint.help.connections.suppliers") },
            { module: "M09 Incidenti", relation: t("osint.help.connections.incidents") },
            { module: "M08 Task", relation: t("osint.help.connections.tasks") },
            { module: "govrico AI M20", relation: t("osint.help.connections.ai") },
          ]}
          configNeeded={[
            t("osint.help.config_needed.1"),
            t("osint.help.config_needed.2"),
            t("osint.help.config_needed.3"),
            t("osint.help.config_needed.4"),
            t("osint.help.config_needed.5"),
            t("osint.help.config_needed.6"),
          ]}
        />
      </div>

      {/* Score thresholds */}
      <section className="bg-white border rounded-xl p-5 space-y-4">
        <h2 className="font-semibold text-gray-800">{t("osint.settings.thresholds")}</h2>
        <p className="text-xs text-gray-500">{t("osint.settings.thresholds_hint")}</p>
        <div className="grid grid-cols-3 gap-4">
          <label className="block">
            <span className="text-sm font-medium text-gray-700">{t("osint.settings.threshold_critical")}</span>
            <input
              type="number"
              min={1}
              max={100}
              value={form.score_threshold_critical}
              onChange={e => set("score_threshold_critical", Number(e.target.value))}
              className="mt-1 block w-full border rounded px-3 py-2 text-sm"
            />
          </label>
          <label className="block">
            <span className="text-sm font-medium text-gray-700">{t("osint.settings.threshold_warning")}</span>
            <input
              type="number"
              min={1}
              max={100}
              value={form.score_threshold_warning}
              onChange={e => set("score_threshold_warning", Number(e.target.value))}
              className="mt-1 block w-full border rounded px-3 py-2 text-sm"
            />
          </label>
          <label className="block">
            <span className="text-sm font-medium text-gray-700">{t("osint.settings.threshold_attention")}</span>
            <input
              type="number"
              min={0}
              max={100}
              value={form.score_threshold_attention}
              onChange={e => set("score_threshold_attention", Number(e.target.value))}
              className="mt-1 block w-full border rounded px-3 py-2 text-sm"
            />
          </label>
        </div>
        <div className="border-t pt-4">
          <label className="block">
            <span className="text-sm font-medium text-gray-700">{t("osint.settings.ssl_expiry_warning_days")}</span>
            <p className="text-xs text-gray-400 mt-0.5">{t("osint.settings.ssl_expiry_warning_days_hint")}</p>
            <div className="flex items-center gap-2 mt-1">
              <input
                type="number"
                min={15}
                max={365}
                value={form.ssl_expiry_warning_days}
                onChange={e => set("ssl_expiry_warning_days", Number(e.target.value))}
                className="w-24 border rounded px-3 py-2 text-sm"
              />
              <span className="text-sm text-gray-500">{t("osint.settings.days")}</span>
            </div>
          </label>
        </div>
      </section>

      {/* Score weights */}
      <section className="bg-white border rounded-xl p-5 space-y-4">
        <h2 className="font-semibold text-gray-800">{t("osint.settings.weights")}</h2>
        <p className="text-xs text-gray-500">{t("osint.settings.weights_hint")}</p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <label className="block">
            <span className="text-sm font-medium text-gray-700">{t("osint.settings.weight_ssl")}</span>
            <input
              type="number"
              min={0}
              max={100}
              value={form.weight_ssl}
              onChange={e => set("weight_ssl", Number(e.target.value))}
              className="mt-1 block w-full border rounded px-3 py-2 text-sm"
            />
          </label>
          <label className="block">
            <span className="text-sm font-medium text-gray-700">{t("osint.settings.weight_dns")}</span>
            <input
              type="number"
              min={0}
              max={100}
              value={form.weight_dns}
              onChange={e => set("weight_dns", Number(e.target.value))}
              className="mt-1 block w-full border rounded px-3 py-2 text-sm"
            />
          </label>
          <label className="block">
            <span className="text-sm font-medium text-gray-700">{t("osint.settings.weight_reputation")}</span>
            <input
              type="number"
              min={0}
              max={100}
              value={form.weight_reputation}
              onChange={e => set("weight_reputation", Number(e.target.value))}
              className="mt-1 block w-full border rounded px-3 py-2 text-sm"
            />
          </label>
          <label className="block">
            <span className="text-sm font-medium text-gray-700">{t("osint.settings.weight_grc")}</span>
            <input
              type="number"
              min={0}
              max={100}
              value={form.weight_grc}
              onChange={e => set("weight_grc", Number(e.target.value))}
              className="mt-1 block w-full border rounded px-3 py-2 text-sm"
            />
          </label>
        </div>
      </section>

      {/* Certificate Transparency monitoring */}
      <section className="bg-white border rounded-xl p-5 space-y-4">
        <h2 className="font-semibold text-gray-800">{t("osint.settings.ct_monitoring")}</h2>
        <p className="text-xs text-gray-500">{t("osint.settings.ct_monitoring_hint")}</p>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={form.ct_monitoring_enabled}
            onChange={e => set("ct_monitoring_enabled", e.target.checked)}
          />
          <span className="text-sm font-medium text-gray-700">{t("osint.settings.ct_enabled")}</span>
        </label>
        <label className="block">
          <span className="text-sm font-medium text-gray-700">{t("osint.settings.ct_lookback_days")}</span>
          <div className="flex items-center gap-2 mt-1">
            <input
              type="number"
              min={1}
              max={365}
              value={form.ct_lookback_days}
              onChange={e => set("ct_lookback_days", Number(e.target.value))}
              className="w-24 border rounded px-3 py-2 text-sm"
              disabled={!form.ct_monitoring_enabled}
            />
            <span className="text-sm text-gray-500">{t("osint.settings.days")}</span>
          </div>
        </label>
        <label className="block">
          <span className="text-sm font-medium text-gray-700">{t("osint.settings.ct_expected_issuers")}</span>
          <p className="text-xs text-gray-400 mt-0.5">{t("osint.settings.ct_expected_issuers_hint")}</p>
          <textarea
            rows={2}
            value={form.ct_expected_issuers_text}
            onChange={e => set("ct_expected_issuers_text", e.target.value)}
            className="mt-1 block w-full border rounded px-3 py-2 text-sm"
            placeholder="Let's Encrypt, DigiCert, GlobalSign"
            disabled={!form.ct_monitoring_enabled}
          />
        </label>
      </section>

      {/* Scan frequency */}
      <section className="bg-white border rounded-xl p-5 space-y-4">
        <h2 className="font-semibold text-gray-800">{t("osint.settings.frequency")}</h2>
        <div className="space-y-3">
          {(
            [
              ["freq_my_domains", "osint.settings.freq_my_domains"],
              ["freq_suppliers_critical", "osint.settings.freq_suppliers_critical"],
              ["freq_suppliers_other", "osint.settings.freq_suppliers_other"],
            ] as const
          ).map(([field, labelKey]) => (
            <div key={field} className="flex items-center justify-between">
              <span className="text-sm text-gray-700">{t(labelKey)}</span>
              <div className="flex gap-2">
                {FREQ_OPTIONS.map(opt => (
                  <button
                    key={opt}
                    onClick={() => set(field, opt)}
                    className={`px-3 py-1 text-sm rounded border ${
                      form[field] === opt
                        ? "bg-primary-600 text-white border-primary-600"
                        : "bg-white text-gray-600 border-gray-300 hover:bg-gray-50"
                    }`}
                  >
                    {t(`osint.settings.freq_${opt}`)}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Subdomain policy */}
      <section className="bg-white border rounded-xl p-5 space-y-3">
        <h2 className="font-semibold text-gray-800">{t("osint.settings.subdomain_policy")}</h2>
        <p className="text-xs text-gray-500">{t("osint.settings.subdomain_policy_hint")}</p>
        <div className="flex gap-2">
          {SUBDOMAIN_OPTIONS.map(opt => (
            <button
              key={opt}
              onClick={() => set("subdomain_auto_include", opt)}
              className={`px-4 py-2 text-sm rounded border ${
                form.subdomain_auto_include === opt
                  ? "bg-primary-600 text-white border-primary-600"
                  : "bg-white text-gray-600 border-gray-300 hover:bg-gray-50"
              }`}
            >
              {t(`osint.settings.subdomain_${opt}`)}
            </button>
          ))}
        </div>
      </section>

      {/* Privacy */}
      <section className="bg-white border rounded-xl p-5">
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={form.anonymization_enabled}
            onChange={e => set("anonymization_enabled", e.target.checked)}
            className="h-4 w-4 rounded border-gray-300 text-primary-600"
          />
          <div>
            <span className="text-sm font-medium text-gray-800">{t("osint.settings.anonymization")}</span>
            <p className="text-xs text-gray-500 mt-0.5">{t("osint.settings.anonymization_hint")}</p>
          </div>
        </label>
      </section>

      {/* API keys */}
      <section className="bg-white border rounded-xl p-5 space-y-4">
        <h2 className="font-semibold text-gray-800">{t("osint.settings.api_keys")}</h2>
        <p className="text-xs text-gray-500">{t("osint.settings.api_keys_hint")}</p>
        {(
          [
            ["hibp_api_key", "HaveIBeenPwned", settings?.has_hibp_key, "hibp"],
            ["virustotal_api_key", "VirusTotal", settings?.has_virustotal_key, "virustotal"],
            ["abuseipdb_api_key", "AbuseIPDB", settings?.has_abuseipdb_key, "abuseipdb"],
            ["gsb_api_key", "Google Safe Browsing", settings?.has_gsb_key, "gsb"],
            ["otx_api_key", "AlienVault OTX", settings?.has_otx_key, null],
            ["abusech_api_key", "abuse.ch (ThreatFox/URLhaus)", settings?.has_abusech_key, "abusech"],
          ] as const
        ).map(([field, label, hasKey, provider]) => {
          const health = provider ? settings?.enricher_health?.[provider] : undefined;
          return (
          <div key={field}>
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-2">
                {provider && <HealthDot health={health} t={t} />}
                <label className="text-sm font-medium text-gray-700">{label}</label>
              </div>
              <div className="flex items-center gap-2">
                {hasKey && (
                  <span className="text-xs text-green-600 font-medium">✓ {t("osint.settings.key_saved")}</span>
                )}
                {provider && hasKey && (
                  <button
                    type="button"
                    onClick={() => { setTestingProvider(provider); testMutation.mutate(provider); }}
                    disabled={testMutation.isPending}
                    className="text-xs px-2 py-0.5 border rounded text-gray-600 hover:bg-gray-50 disabled:opacity-50"
                  >
                    {testingProvider === provider && testMutation.isPending ? t("osint.settings.health.testing") : t("osint.settings.health.test")}
                  </button>
                )}
              </div>
            </div>
            <input
              type="password"
              value={form[field] as string}
              onChange={e => set(field, e.target.value)}
              placeholder={hasKey ? "••••••••••••" : t("osint.settings.key_placeholder")}
              className="w-full border rounded px-3 py-2 text-sm font-mono"
            />
            {provider && health && health.status !== "no_key" && (
              <p className="text-xs text-gray-400 mt-1">
                {t(`osint.settings.health.status.${health.status}`)}
                {health.checked_at && ` · ${t("osint.settings.health.checked_at", { date: new Date(health.checked_at).toLocaleString("it-IT") })}`}
              </p>
            )}
          </div>
          );
        })}
        <div className="flex justify-end pt-1">
          <button
            type="button"
            onClick={() => { setTestingProvider("__all__"); testMutation.mutate(undefined); }}
            disabled={testMutation.isPending}
            className="text-xs px-3 py-1 border rounded text-primary-700 border-primary-200 hover:bg-primary-50 disabled:opacity-50"
          >
            {testingProvider === "__all__" && testMutation.isPending ? t("osint.settings.health.testing_all") : t("osint.settings.health.test_all")}
          </button>
        </div>
      </section>

      {/* Save */}
      <div className="flex justify-end gap-3 pb-6">
        {saveMutation.isError && (
          <span className="text-sm text-red-600 self-center">{t("common.save_error")}</span>
        )}
        {saved && (
          <span className="text-sm text-green-600 self-center">✓ {t("common.saved")}</span>
        )}
        <button
          onClick={() => saveMutation.mutate()}
          disabled={saveMutation.isPending}
          className="px-5 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm font-medium disabled:opacity-50"
        >
          {saveMutation.isPending ? t("common.saving") : t("actions.save")}
        </button>
      </div>
    </div>
  );
}

const HEALTH_DOT: Record<string, string> = {
  ok: "bg-green-500",
  invalid: "bg-red-500",
  rate_limited: "bg-amber-400",
  error: "bg-amber-400",
  no_key: "bg-gray-300",
};

function HealthDot({
  health,
  t,
}: {
  health?: { status: string; detail: string; checked_at: string };
  t: (k: string, o?: Record<string, unknown>) => string;
}) {
  const status = health?.status ?? "no_key";
  const color = HEALTH_DOT[status] ?? "bg-gray-300";
  const title = health
    ? `${t(`osint.settings.health.status.${status}`)}${health.detail ? ` (${health.detail})` : ""}`
    : t("osint.settings.health.status.no_key");
  return <span className={`inline-block w-2.5 h-2.5 rounded-full ${color}`} title={title} aria-label={title} />;
}
