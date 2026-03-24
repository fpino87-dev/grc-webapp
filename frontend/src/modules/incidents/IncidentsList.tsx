import { useEffect, useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  incidentsApi,
  type Incident,
  type NIS2Configuration,
  type NIS2Notification,
  type NIS2Timeline,
} from "../../api/endpoints/incidents";
import { plantsApi } from "../../api/endpoints/plants";
import { useAuthStore } from "../../store/auth";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { AiSuggestionBanner } from "../../components/ui/AiSuggestionBanner";
import { ModuleHelp } from "../../components/ui/ModuleHelp";
import { useTranslation } from "react-i18next";
import i18n from "../../i18n";

const ENISA_CATEGORIES = [
  { value: "malicious_code", label: "Malicious Code" },
  { value: "availability_attack", label: "Availability Attack" },
  { value: "information_gathering", label: "Information Gathering" },
  { value: "intrusion_attempt", label: "Intrusion Attempt" },
  { value: "intrusion", label: "Intrusion" },
  { value: "data_breach", label: "Information Security Breach" },
  { value: "fraud", label: "Fraud" },
  { value: "supply_chain", label: "Supply Chain Attack" },
  { value: "insider_threat", label: "Insider Threat" },
  { value: "physical", label: "Physical Attack" },
  { value: "other", label: "Other" },
];

const ENISA_SUBCATEGORIES: Record<string, { value: string; label: string }[]> = {
  malicious_code: [
    { value: "ransomware", label: "Ransomware" },
    { value: "virus", label: "Virus/Worm" },
    { value: "trojan", label: "Trojan/Backdoor" },
  ],
  availability_attack: [
    { value: "ddos", label: "DDoS" },
    { value: "dos", label: "DoS" },
    { value: "power_outage", label: "Interruzione alimentazione" },
  ],
  intrusion: [
    { value: "account_compromise", label: "Compromissione account" },
    { value: "system_compromise", label: "Compromissione sistema" },
  ],
  data_breach: [
    { value: "personal_data", label: "Dati personali (GDPR)" },
    { value: "credentials", label: "Credenziali di accesso" },
  ],
};

const CSIRT_BY_COUNTRY: Record<string, { name: string; portal: string }> = {
  IT: {
    name: "ACN — Agenzia Cybersicurezza Nazionale",
    portal: "https://www.acn.gov.it/portale/nis/notifica-incidenti",
  },
  DE: {
    name: "BSI — Bundesamt fur Sicherheit in der Informationstechnik",
    portal: "https://www.bsi.bund.de/EN/Topics/KRITIS/NIS2/nis2_node.html",
  },
  FR: { name: "ANSSI", portal: "https://www.ssi.gouv.fr/en/" },
};

function NewIncidentForm({
  plants,
  onClose,
}: {
  plants: { id: string; code: string; name: string }[];
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [form, setForm] = useState<Partial<Incident>>({
    severity: "media",
    nis2_notifiable: "da_valutare",
    detected_at: new Date().toISOString().slice(0, 16),
  });

  const mutation = useMutation({
    mutationFn: incidentsApi.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["incidents"] });
      onClose();
    },
  });

  function handleChange(
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6">
        <h3 className="text-lg font-semibold mb-4">{t("incidents.new.title")}</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("incidents.fields.plant")}</label>
            <select name="plant" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
              <option value="">{t("common.select")}</option>
              {plants.map((p) => (
                <option key={p.id} value={p.id}>{p.code} — {p.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("incidents.fields.title")}</label>
            <input name="title" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("incidents.fields.description")}</label>
            <textarea name="description" onChange={handleChange} rows={3} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("incidents.fields.severity")}</label>
              <select name="severity" onChange={handleChange} defaultValue="media" className="w-full border rounded px-3 py-2 text-sm">
                {["bassa", "media", "alta", "critica"].map((s) => (
                  <option key={s} value={s}>{t(`status.${s}`)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("incidents.fields.nis2_notifiable")}</label>
              <select name="nis2_notifiable" onChange={handleChange} defaultValue="da_valutare" className="w-full border rounded px-3 py-2 text-sm">
                {["si", "no", "da_valutare"].map((s) => (
                  <option key={s} value={s}>{t(`status.${s}`)}</option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("incidents.fields.detected_at")}</label>
            <input type="datetime-local" name="detected_at" defaultValue={form.detected_at as string} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
        </div>
        {mutation.isError && (
          <p className="text-sm text-red-600 mt-2">{t("common.save_error")}</p>
        )}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">
            {t("actions.cancel")}
          </button>
          <button
            onClick={() => mutation.mutate(form)}
            disabled={mutation.isPending}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? t("common.saving") : t("incidents.new.submit")}
          </button>
        </div>
      </div>
    </div>
  );
}

export function IncidentsList() {
  const { t } = useTranslation();
  const [showNew, setShowNew] = useState(false);
  const [selected, setSelected] = useState<Incident | null>(null);
  const [activeTab, setActiveTab] = useState<"gestione" | "classificazione" | "timeline" | "config">("gestione");
  const [sentType, setSentType] = useState("formal_notification");
  const [protocolRef, setProtocolRef] = useState("");
  const [authorityResponse, setAuthorityResponse] = useState("");
  const qc = useQueryClient();
  const selectedPlant = useAuthStore(s => s.selectedPlant);
  const user = useAuthStore(s => s.user);

  const params: Record<string, string> = {};
  if (selectedPlant?.id) params.plant = selectedPlant.id;

  const { data, isLoading } = useQuery({
    queryKey: ["incidents", selectedPlant?.id],
    queryFn: () => incidentsApi.list(params),
    retry: false,
  });

  const { data: plants } = useQuery({
    queryKey: ["plants"],
    queryFn: () => plantsApi.list(),
    retry: false,
  });

  const closeMutation = useMutation({
    mutationFn: incidentsApi.close,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["incidents"] }),
  });
  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<Incident> }) => incidentsApi.update(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["incidents"] }),
  });
  const classifyMutation = useMutation({
    mutationFn: (id: string) => incidentsApi.classifySignificance(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["incidents"] }),
  });
  const markSentMutation = useMutation({
    mutationFn: (id: string) =>
      incidentsApi.markSent(id, {
        notification_type: sentType,
        protocol_ref: protocolRef,
        authority_response: authorityResponse,
      }),
    onSuccess: () => {
      if (selected) {
        qc.invalidateQueries({ queryKey: ["nis2-notifications", selected.id] });
        qc.invalidateQueries({ queryKey: ["incidents"] });
      }
      setProtocolRef("");
      setAuthorityResponse("");
    },
  });

  const incidents = data?.results ?? [];
  const { data: timeline } = useQuery({
    queryKey: ["nis2-timeline", selected?.id],
    queryFn: () => incidentsApi.timeline(selected?.id ?? ""),
    enabled: !!selected,
  });
  const { data: notifications } = useQuery({
    queryKey: ["nis2-notifications", selected?.id],
    queryFn: () => incidentsApi.notifications(selected?.id ?? ""),
    enabled: !!selected,
  });
  const canSeeConfig = user?.role === "super_admin" || user?.role === "compliance_officer";
  const { data: configData } = useQuery({
    queryKey: ["nis2-config", selectedPlant?.id],
    queryFn: () => incidentsApi.listConfig(selectedPlant?.id ?? ""),
    enabled: !!selectedPlant?.id && canSeeConfig,
  });
  const currentConfig = configData?.[0];
  const [configForm, setConfigForm] = useState<Partial<NIS2Configuration>>({
    threshold_users: 100,
    threshold_hours: 4,
    threshold_financial: 100000,
  });
  const configMutation = useMutation({
    mutationFn: () => {
      if (!selectedPlant?.id) {
        throw new Error("Plant non selezionato");
      }
      const payload = { ...configForm, plant: selectedPlant.id } as NIS2Configuration;
      if (currentConfig?.id) return incidentsApi.updateConfig(currentConfig.id, payload);
      return incidentsApi.createConfig(payload);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["nis2-config", selectedPlant?.id] }),
  });
  const dateLocale = i18n.language || "it";

  const selectedPlantCountry = useMemo(() => {
    return plants?.find(p => p.id === selectedPlant?.id)?.country ?? "IT";
  }, [plants, selectedPlant?.id]);

  useEffect(() => {
    if (!currentConfig) return;
    setConfigForm({
      threshold_users: currentConfig.threshold_users,
      threshold_hours: currentConfig.threshold_hours,
      threshold_financial: currentConfig.threshold_financial,
      nis2_sector: currentConfig.nis2_sector,
      nis2_subsector: currentConfig.nis2_subsector,
      internal_contact_name: currentConfig.internal_contact_name,
      internal_contact_email: currentConfig.internal_contact_email,
      internal_contact_phone: currentConfig.internal_contact_phone,
      legal_entity_name: currentConfig.legal_entity_name,
      legal_entity_vat: currentConfig.legal_entity_vat,
    });
  }, [currentConfig]);

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900 flex items-center">
          {t("incidents.title")}
          <ModuleHelp
            title={t("incidents.help.title")}
            description={t("incidents.help.description")}
            steps={[
              t("incidents.help.steps.1"),
              t("incidents.help.steps.2"),
              t("incidents.help.steps.3"),
              t("incidents.help.steps.4"),
              t("incidents.help.steps.5"),
            ]}
            connections={[
              { module: t("incidents.help.connections.pdca.module"), relation: t("incidents.help.connections.pdca.relation") },
              { module: t("incidents.help.connections.lessons.module"), relation: t("incidents.help.connections.lessons.relation") },
              { module: t("incidents.help.connections.tasks.module"), relation: t("incidents.help.connections.tasks.relation") },
            ]}
            configNeeded={[t("incidents.help.config_needed.1")]}
          />
        </h2>
        <button
          onClick={() => setShowNew(true)}
          className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700"
        >
          {t("incidents.new.open")}
        </button>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">{t("common.loading")}</div>
        ) : incidents.length === 0 ? (
          <div className="p-8 text-center text-gray-400">{t("incidents.empty")}</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("incidents.table.title")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("incidents.table.severity")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("incidents.table.nis2")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("incidents.table.status")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("incidents.table.detected_at")}</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {incidents.map((inc) => (
                <tr key={inc.id} className="hover:bg-gray-50 transition-colors cursor-pointer" onClick={() => setSelected(inc)}>
                  <td className="px-4 py-3 font-medium text-gray-800">{inc.title}</td>
                  <td className="px-4 py-3"><StatusBadge status={inc.severity} /></td>
                  <td className="px-4 py-3"><StatusBadge status={inc.nis2_notifiable} /></td>
                  <td className="px-4 py-3"><StatusBadge status={inc.status} /></td>
                  <td className="px-4 py-3 text-gray-500 text-xs">
                    {new Date(inc.detected_at).toLocaleString(dateLocale)}
                  </td>
                  <td className="px-4 py-3">
                    {inc.status !== "chiuso" && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          closeMutation.mutate(inc.id);
                        }}
                        className="text-xs text-gray-500 hover:text-red-600 border border-gray-300 rounded px-2 py-0.5 hover:border-red-300"
                      >
                        {t("common.close")}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showNew && plants && (
        <NewIncidentForm plants={plants} onClose={() => setShowNew(false)} />
      )}

      {selected && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg w-full max-w-5xl max-h-[92vh] overflow-auto">
            <div className="p-4 border-b flex items-center justify-between">
              <h3 className="text-lg font-semibold">{selected.title}</h3>
              <button onClick={() => setSelected(null)} className="text-gray-500">×</button>
            </div>
            <div className="px-4 pt-3 flex gap-2">
              {(["gestione","classificazione","timeline","config"] as const).map(tab => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-3 py-1.5 text-xs rounded ${activeTab === tab ? "bg-primary-600 text-white" : "bg-gray-100 text-gray-600"}`}
                >
                  {tab === "gestione" ? "Gestione" : tab === "classificazione" ? "Classificazione NIS2" : tab === "timeline" ? "Timeline NIS2 & Notifiche" : "Configurazione NIS2"}
                </button>
              ))}
            </div>

            {activeTab === "gestione" && (
              <div className="p-4 space-y-3">
                <AiSuggestionBanner
                  taskType="incident_classify"
                  entityId={selected.id}
                  autoTrigger={true}
                  onAccept={(res) => {
                    const r = res as { category?: string; severity?: Incident["severity"] };
                    setSelected({
                      ...selected,
                      incident_category: r.category ?? selected.incident_category,
                      severity: r.severity ?? selected.severity,
                    });
                  }}
                  onIgnore={() => {}}
                />
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-gray-600">Categoria ENISA</label>
                    <select
                      className="w-full border rounded px-3 py-2 text-sm"
                      value={selected.incident_category ?? ""}
                      onChange={e => setSelected({ ...selected, incident_category: e.target.value, incident_subcategory: "" })}
                    >
                      <option value="">— seleziona —</option>
                      {ENISA_CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-gray-600">Sottocategoria</label>
                    <select
                      className="w-full border rounded px-3 py-2 text-sm"
                      value={selected.incident_subcategory ?? ""}
                      onChange={e => setSelected({ ...selected, incident_subcategory: e.target.value })}
                    >
                      <option value="">— seleziona —</option>
                      {(ENISA_SUBCATEGORIES[selected.incident_category ?? ""] ?? []).map(s => (
                        <option key={s.value} value={s.value}>{s.label}</option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <input className="border rounded px-3 py-2 text-sm" placeholder="Utenti/sistemi colpiti" value={selected.affected_users_count ?? ""} onChange={e => setSelected({ ...selected, affected_users_count: e.target.value ? Number(e.target.value) : null })} />
                  <input className="border rounded px-3 py-2 text-sm" placeholder="Ore di interruzione" value={selected.service_disruption_hours ?? ""} onChange={e => setSelected({ ...selected, service_disruption_hours: e.target.value || null })} />
                  <input className="border rounded px-3 py-2 text-sm" placeholder="Impatto finanziario EUR" value={selected.financial_impact_eur ?? ""} onChange={e => setSelected({ ...selected, financial_impact_eur: e.target.value || null })} />
                </div>
                <div className="flex gap-4 text-sm">
                  <label><input type="checkbox" checked={!!selected.personal_data_involved} onChange={e => setSelected({ ...selected, personal_data_involved: e.target.checked })} /> Dati personali coinvolti</label>
                  <label><input type="checkbox" checked={!!selected.cross_border_impact} onChange={e => setSelected({ ...selected, cross_border_impact: e.target.checked })} /> Impatto cross-border</label>
                  <label><input type="checkbox" checked={!!selected.critical_infrastructure_impact} onChange={e => setSelected({ ...selected, critical_infrastructure_impact: e.target.checked })} /> Infrastrutture critiche</label>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => updateMutation.mutate({ id: selected.id, payload: selected })}
                    disabled={updateMutation.isPending}
                    className="px-3 py-2 text-xs bg-primary-600 text-white rounded disabled:opacity-50"
                  >
                    {updateMutation.isPending ? "Salvataggio..." : "Salva gestione"}
                  </button>
                  {updateMutation.isSuccess && <span className="text-xs text-green-600">✓ Salvato</span>}
                  {updateMutation.isError && <span className="text-xs text-red-500">Errore nel salvataggio</span>}
                </div>
              </div>
            )}

            {activeTab === "classificazione" && (
              <div className="p-4 space-y-3">
                {selected.is_significant === true && <div className="px-3 py-2 bg-red-50 text-red-700 rounded text-sm">Incidente SIGNIFICATIVO — obbligo di notifica NIS2</div>}
                {selected.is_significant === false && <div className="px-3 py-2 bg-green-50 text-green-700 rounded text-sm">Incidente non significativo — nessun obbligo</div>}
                {selected.is_significant == null && <div className="px-3 py-2 bg-yellow-50 text-yellow-700 rounded text-sm">Classificazione in attesa</div>}
                <button onClick={() => classifyMutation.mutate(selected.id)} className="px-3 py-2 text-xs bg-primary-600 text-white rounded">Classifica automaticamente</button>
              </div>
            )}

            {activeTab === "timeline" && (
              <div className="p-4 space-y-4">
                {(timeline as NIS2Timeline | undefined)?.steps?.map(step => (
                  <div key={step.step} className="border rounded p-3">
                    <div className="font-medium text-sm">{step.label}</div>
                    <div className="text-xs text-gray-500">Scadenza: {step.deadline ? new Date(step.deadline).toLocaleString(dateLocale) : "—"}</div>
                    <div className="text-xs">Stato: <strong>{step.status}</strong></div>
                    <div className="mt-2 flex gap-2">
                      <button
                        onClick={async () => {
                          try {
                            const out = await incidentsApi.generateDocument(selected.id, step.step);
                            const blob = new Blob([out.text], { type: "text/html;charset=utf-8" });
                            const url = URL.createObjectURL(blob);
                            const a = document.createElement("a");
                            a.href = url;
                            a.download = `NIS2_${step.step}_${selected.id.slice(0, 8)}.html`;
                            a.click();
                            URL.revokeObjectURL(url);
                          } catch {
                            // Keep UX simple: errors are visible in network/console.
                          }
                        }}
                        className="text-xs border rounded px-2 py-1"
                      >
                        Genera documento
                      </button>
                      <button onClick={() => setSentType(step.step)} className="text-xs border rounded px-2 py-1">Seleziona invio</button>
                    </div>
                  </div>
                ))}
                <div className="border rounded p-3 space-y-2">
                  <div className="text-sm font-medium">Segna come inviato</div>
                  <select value={sentType} onChange={e => setSentType(e.target.value)} className="w-full border rounded px-2 py-1.5 text-sm">
                    <option value="early_warning">Early Warning</option>
                    <option value="formal_notification">Notifica formale</option>
                    <option value="final_report">Report finale</option>
                    <option value="update">Aggiornamento</option>
                  </select>
                  <input className="w-full border rounded px-2 py-1.5 text-sm" placeholder="Numero protocollo" value={protocolRef} onChange={e => setProtocolRef(e.target.value)} />
                  <textarea className="w-full border rounded px-2 py-1.5 text-sm" rows={2} placeholder="Note risposta autorita" value={authorityResponse} onChange={e => setAuthorityResponse(e.target.value)} />
                  <button onClick={() => markSentMutation.mutate(selected.id)} className="px-3 py-2 text-xs bg-primary-600 text-white rounded">Conferma invio</button>
                </div>
                <div className="border rounded p-3">
                  <div className="text-sm font-medium mb-2">Registro notifiche</div>
                  <table className="w-full text-xs">
                    <thead><tr><th className="text-left">Tipo</th><th className="text-left">CSIRT</th><th className="text-left">Data invio</th><th className="text-left">Protocollo</th></tr></thead>
                    <tbody>
                      {(notifications as NIS2Notification[] | undefined)?.map(n => (
                        <tr key={n.id}><td>{n.notification_type}</td><td>{n.csirt_name}</td><td>{n.sent_at ? new Date(n.sent_at).toLocaleString(dateLocale) : "—"}</td><td>{n.protocol_ref || "—"}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="border rounded p-3">
                  <div className="text-sm font-medium mb-2">Bozza RCA con AI</div>
                  <AiSuggestionBanner
                    taskType="rca_draft"
                    entityId={selected.id}
                    autoTrigger={false}
                    onAccept={() => {}}
                    onIgnore={() => {}}
                  />
                </div>
              </div>
            )}

            {activeTab === "config" && !canSeeConfig && (
              <div className="p-4 text-sm text-gray-500">Permessi insufficienti per la configurazione NIS2.</div>
            )}
            {activeTab === "config" && canSeeConfig && !selectedPlant && (
              <div className="p-4 text-sm text-amber-700 bg-amber-50 rounded m-4 border border-amber-200">
                Seleziona un sito dal menu in alto per configurare i parametri NIS2.
              </div>
            )}
            {activeTab === "config" && canSeeConfig && selectedPlant && (
              <div className="p-4 space-y-3">
                <div className="text-sm font-semibold">Configurazione NIS2 per sito</div>
                <div className="grid grid-cols-3 gap-3">
                  <input className="border rounded px-2 py-1.5 text-sm" placeholder="Soglia utenti" value={configForm.threshold_users ?? currentConfig?.threshold_users ?? 100} onChange={e => setConfigForm(f => ({ ...f, threshold_users: Number(e.target.value) }))} />
                  <input className="border rounded px-2 py-1.5 text-sm" placeholder="Soglia ore" value={configForm.threshold_hours ?? currentConfig?.threshold_hours ?? 4} onChange={e => setConfigForm(f => ({ ...f, threshold_hours: Number(e.target.value) }))} />
                  <input className="border rounded px-2 py-1.5 text-sm" placeholder="Soglia EUR" value={configForm.threshold_financial ?? currentConfig?.threshold_financial ?? 100000} onChange={e => setConfigForm(f => ({ ...f, threshold_financial: Number(e.target.value) }))} />
                </div>
                <input className="w-full border rounded px-2 py-1.5 text-sm" placeholder="Settore NIS2" value={configForm.nis2_sector ?? currentConfig?.nis2_sector ?? ""} onChange={e => setConfigForm(f => ({ ...f, nis2_sector: e.target.value }))} />
                <input className="w-full border rounded px-2 py-1.5 text-sm" placeholder="Sottosettore NIS2" value={configForm.nis2_subsector ?? currentConfig?.nis2_subsector ?? ""} onChange={e => setConfigForm(f => ({ ...f, nis2_subsector: e.target.value }))} />
                <input className="w-full border rounded px-2 py-1.5 text-sm" placeholder="Referente NIS2 - Nome" value={configForm.internal_contact_name ?? currentConfig?.internal_contact_name ?? ""} onChange={e => setConfigForm(f => ({ ...f, internal_contact_name: e.target.value }))} />
                <input className="w-full border rounded px-2 py-1.5 text-sm" placeholder="Referente NIS2 - Email" value={configForm.internal_contact_email ?? currentConfig?.internal_contact_email ?? ""} onChange={e => setConfigForm(f => ({ ...f, internal_contact_email: e.target.value }))} />
                <input className="w-full border rounded px-2 py-1.5 text-sm" placeholder="Referente NIS2 - Telefono" value={configForm.internal_contact_phone ?? currentConfig?.internal_contact_phone ?? ""} onChange={e => setConfigForm(f => ({ ...f, internal_contact_phone: e.target.value }))} />
                <input className="w-full border rounded px-2 py-1.5 text-sm" placeholder="Ragione sociale" value={configForm.legal_entity_name ?? currentConfig?.legal_entity_name ?? ""} onChange={e => setConfigForm(f => ({ ...f, legal_entity_name: e.target.value }))} />
                <input className="w-full border rounded px-2 py-1.5 text-sm" placeholder="Partita IVA / VAT" value={configForm.legal_entity_vat ?? currentConfig?.legal_entity_vat ?? ""} onChange={e => setConfigForm(f => ({ ...f, legal_entity_vat: e.target.value }))} />
                <button onClick={() => configMutation.mutate()} className="px-3 py-2 text-xs bg-primary-600 text-white rounded">Salva configurazione</button>
                <div className="text-xs text-gray-600 border rounded p-2 bg-gray-50">
                  CSIRT competente: <strong>{CSIRT_BY_COUNTRY[selectedPlantCountry]?.name ?? "CSIRT Nazionale"}</strong><br />
                  Portale: {CSIRT_BY_COUNTRY[selectedPlantCountry]?.portal ?? "—"}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
