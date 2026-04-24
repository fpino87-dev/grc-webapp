import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { osintApi, type OsintSettings, type ScanFrequency } from "../../api/endpoints/osint";
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
    freq_my_domains: "weekly" as ScanFrequency,
    freq_suppliers_critical: "weekly" as ScanFrequency,
    freq_suppliers_other: "monthly" as ScanFrequency,
    subdomain_auto_include: "ask" as SubdomainPolicy,
    anonymization_enabled: true,
    hibp_api_key: "",
    virustotal_api_key: "",
    abuseipdb_api_key: "",
    gsb_api_key: "",
    otx_api_key: "",
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
        freq_my_domains: settings.freq_my_domains,
        freq_suppliers_critical: settings.freq_suppliers_critical,
        freq_suppliers_other: settings.freq_suppliers_other,
        subdomain_auto_include: settings.subdomain_auto_include,
        anonymization_enabled: settings.anonymization_enabled,
      }));
    }
  }, [settings]);

  const saveMutation = useMutation({
    mutationFn: () => {
      const payload: Record<string, unknown> = {
        score_threshold_critical: form.score_threshold_critical,
        score_threshold_warning: form.score_threshold_warning,
        freq_my_domains: form.freq_my_domains,
        freq_suppliers_critical: form.freq_suppliers_critical,
        freq_suppliers_other: form.freq_suppliers_other,
        subdomain_auto_include: form.subdomain_auto_include,
        anonymization_enabled: form.anonymization_enabled,
      };
      if (form.hibp_api_key) payload.hibp_api_key = form.hibp_api_key;
      if (form.virustotal_api_key) payload.virustotal_api_key = form.virustotal_api_key;
      if (form.abuseipdb_api_key) payload.abuseipdb_api_key = form.abuseipdb_api_key;
      if (form.gsb_api_key) payload.gsb_api_key = form.gsb_api_key;
      if (form.otx_api_key) payload.otx_api_key = form.otx_api_key;
      return osintApi.updateSettings(payload);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["osint-settings"] });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
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
          title="OSINT Monitor — Chiavi API enricher"
          description="Le chiavi API abilitano arricchimenti aggiuntivi durante le scansioni. Tutte sono opzionali: il modulo funziona anche senza, usando solo SSL/DNS/WHOIS (gratuiti e senza registrazione)."
          steps={[
            "HaveIBeenPwned (HIBP) — Breach email: haveibeenpwned.com/API/Key → piano a pagamento (~3,50$/mese). Solo per 'Miei domini'.",
            "VirusTotal — Reputazione dominio/IP: virustotal.com/gui/join-us → piano Free (1000 req/giorno). API Key in 'My API Key'.",
            "AbuseIPDB — Blacklist IP: abuseipdb.com/register → piano Free (1000 req/giorno). API Key nel profilo.",
            "Google Safe Browsing — URL malevoli: console.cloud.google.com → Abilita 'Safe Browsing API' → Credenziali → Chiave API.",
            "AlienVault OTX — Threat intelligence: otx.alienvault.com → Registrati gratis → Profilo → OTX Key. Nessun costo.",
          ]}
          connections={[
            { module: "Plants", relation: "Dominio principale e domini aggiuntivi monitorati" },
            { module: "M14 Fornitori", relation: "Sito web fornitore → entità OSINT tipo supplier" },
            { module: "M09 Incidenti", relation: "Alert critici su miei domini → incidente automatico" },
            { module: "M08 Task", relation: "Alert su fornitori → task di verifica" },
            { module: "AI Engine M20", relation: "Analisi AI con dati anonimizzati" },
          ]}
          configNeeded={[
            "VirusTotal Free: virustotal.com/gui/join-us",
            "AbuseIPDB Free: abuseipdb.com/register",
            "AlienVault OTX Free: otx.alienvault.com (registrazione gratuita)",
            "Google Safe Browsing: console.cloud.google.com (serve progetto GCP)",
            "HaveIBeenPwned: haveibeenpwned.com/API/Key (a pagamento, ~3,50$/mese)",
          ]}
        />
      </div>

      {/* Score thresholds */}
      <section className="bg-white border rounded-xl p-5 space-y-4">
        <h2 className="font-semibold text-gray-800">{t("osint.settings.thresholds")}</h2>
        <p className="text-xs text-gray-500">{t("osint.settings.thresholds_hint")}</p>
        <div className="grid grid-cols-2 gap-4">
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
        </div>
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
            ["hibp_api_key", "HaveIBeenPwned", settings?.has_hibp_key],
            ["virustotal_api_key", "VirusTotal", settings?.has_virustotal_key],
            ["abuseipdb_api_key", "AbuseIPDB", settings?.has_abuseipdb_key],
            ["gsb_api_key", "Google Safe Browsing", settings?.has_gsb_key],
            ["otx_api_key", "AlienVault OTX", settings?.has_otx_key],
          ] as const
        ).map(([field, label, hasKey]) => (
          <div key={field}>
            <div className="flex items-center justify-between mb-1">
              <label className="text-sm font-medium text-gray-700">{label}</label>
              {hasKey && (
                <span className="text-xs text-green-600 font-medium">✓ {t("osint.settings.key_saved")}</span>
              )}
            </div>
            <input
              type="password"
              value={form[field] as string}
              onChange={e => set(field, e.target.value)}
              placeholder={hasKey ? "••••••••••••" : t("osint.settings.key_placeholder")}
              className="w-full border rounded px-3 py-2 text-sm font-mono"
            />
          </div>
        ))}
      </section>

      {/* Save */}
      <div className="flex justify-end gap-3 pb-6">
        {saveMutation.isError && (
          <span className="text-sm text-red-600 self-center">{t("common.error_generic")}</span>
        )}
        {saved && (
          <span className="text-sm text-green-600 self-center">✓ {t("common.saved")}</span>
        )}
        <button
          onClick={() => saveMutation.mutate()}
          disabled={saveMutation.isPending}
          className="px-5 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm font-medium disabled:opacity-50"
        >
          {saveMutation.isPending ? t("common.saving") : t("common.save")}
        </button>
      </div>
    </div>
  );
}
