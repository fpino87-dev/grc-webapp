import { useEffect, useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  incidentsApi,
  type ClassificationMethod,
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
  const [activeTab, setActiveTab] = useState<"gestione" | "classificazione" | "metodo" | "timeline" | "config">("gestione");
  const [sentType, setSentType] = useState("formal_notification");
  const [protocolRef, setProtocolRef] = useState("");
  const [authorityResponse, setAuthorityResponse] = useState("");
  const [overrideEnabled, setOverrideEnabled] = useState(false);
  const [overrideValue, setOverrideValue] = useState<"significant" | "not_significant">("significant");
  const [overrideReason, setOverrideReason] = useState("");
  const [rcaDraftText, setRcaDraftText] = useState("");
  const [rcaDraftData, setRcaDraftData] = useState<Record<string, unknown> | null>(null);
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
  const deleteMutation = useMutation({
    mutationFn: incidentsApi.delete,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["incidents"] });
      setSelected(null);
    },
  });
  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<Incident> }) => incidentsApi.update(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["incidents"] }),
  });
  const classifyMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data?: { override?: boolean; reason?: string } }) =>
      incidentsApi.classifySignificance(id, data),
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
  const { data: classificationMethod } = useQuery({
    queryKey: ["classification-method", selected?.id],
    queryFn: () => incidentsApi.classificationMethod(selected?.id ?? ""),
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
  const thresholdUsers = Number(classificationMethod?.nis2_method.thresholds.affected_users_count ?? currentConfig?.threshold_users ?? 100);
  const thresholdHours = Number(classificationMethod?.nis2_method.thresholds.service_disruption_hours ?? currentConfig?.threshold_hours ?? 4);
  const thresholdFinancial = Number(classificationMethod?.nis2_method.thresholds.financial_impact_eur ?? currentConfig?.threshold_financial ?? 100000);
  const enisaCategories = (classificationMethod?.taxonomy.categories ?? []).map((c) => ({ value: c.code, label: c.label }));
  const enisaSubcategories: Record<string, { value: string; label: string }[]> = Object.fromEntries(
    Object.entries(classificationMethod?.taxonomy.subcategories ?? {}).map(([key, values]) => [
      key,
      values.map((entry) => ({ value: entry.code, label: entry.label })),
    ])
  );

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

  function formatRcaText(result: unknown): string {
    const data = result as Record<string, unknown>;
    const list = (value: unknown) =>
      Array.isArray(value) && value.length > 0 ? value.map((v) => `- ${String(v)}`).join("\n") : "- —";
    return [
      "1) Sommario esecutivo",
      String(data?.summary ?? "—"),
      "",
      "2) Causa radice",
      String(data?.root_cause ?? "—"),
      "",
      "3) Fattori contributivi",
      list(data?.contributing_factors),
      "",
      "4) Timeline",
      list(data?.timeline),
      "",
      "5) Azioni correttive immediate",
      list(data?.immediate_actions),
      "",
      "6) Azioni preventive lungo termine",
      list(data?.preventive_actions),
      "",
      "7) Lessons learned",
      String(data?.lessons_learned ?? "—"),
    ].join("\n");
  }

  function listText(value: unknown): string {
    return Array.isArray(value) && value.length > 0 ? value.map((v) => `• ${String(v)}`).join("\n") : "—";
  }

  function exportClassificationMethodHtml() {
    if (!selected || !classificationMethod) return;

    const rows = (classificationMethod.nis2_method.criteria ?? [])
      .map((criterion) => {
        const satisfied = isCriterionSatisfied(criterion, selected);
        const incidentRaw = (selected as Record<string, unknown>)[criterion.key];
        const incidentDisplay =
          criterion.type === "boolean" ? (incidentRaw ? "Si" : "No") : String(incidentRaw ?? 0);
        const sourceLabel =
          criterion.type === "threshold" ? "input utente + soglia sito" : "flag booleano";
        return `
          <tr>
            <td>${satisfied ? "OK" : "NO"}</td>
            <td>${criterion.label}</td>
            <td>${incidentDisplay}</td>
            <td>${criterion.type === "threshold" ? String(criterion.threshold ?? "—") : "—"}</td>
            <td>${sourceLabel}</td>
          </tr>
        `;
      })
      .join("");

    const taxRows = (classificationMethod.taxonomy.categories ?? [])
      .map((category) => {
        const subs =
          (classificationMethod.taxonomy.subcategories[category.code] ?? [])
            .map((sub) => sub.label)
            .join(", ") || "non definite";
        return `
          <tr>
            <td>${category.code}</td>
            <td>${category.label}</td>
            <td>${category.description}</td>
            <td>${subs}</td>
          </tr>
        `;
      })
      .join("");

    const expected = (classificationMethod.nis2_method.criteria ?? []).some((criterion) =>
      isCriterionSatisfied(criterion, selected)
    )
      ? "SIGNIFICATIVO"
      : "NON significativo";

    const html = `<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8" />
  <title>Metodo Classificazione NIS2</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 20px; color: #111827; font-size: 12px; }
    h1 { font-size: 18px; margin-bottom: 4px; }
    h2 { font-size: 14px; margin-top: 20px; margin-bottom: 8px; }
    table { width: 100%; border-collapse: collapse; margin-top: 8px; }
    th, td { border: 1px solid #d1d5db; padding: 6px 8px; vertical-align: top; }
    th { background: #f3f4f6; text-align: left; }
    .badge { display: inline-block; padding: 4px 8px; border-radius: 4px; background: #e5e7eb; font-weight: bold; }
  </style>
</head>
<body>
  <h1>Metodo di classificazione NIS2</h1>
  <div>Incidente: <strong>${selected.title}</strong></div>
  <div>Data export: ${new Date().toLocaleString(dateLocale)}</div>
  <div style="margin-top: 8px;">Regola: ${classificationMethod.nis2_method.rule}</div>
  <div style="margin-top: 8px;">Esito automatico atteso: <span class="badge">${expected}</span></div>

  <h2>Valutazione corrente</h2>
  <table>
    <thead>
      <tr><th>Esito</th><th>Criterio</th><th>Valore corrente</th><th>Soglia</th><th>Fonte</th></tr>
    </thead>
    <tbody>${rows}</tbody>
  </table>

  <h2>Tassonomia ENISA</h2>
  <table>
    <thead>
      <tr><th>Codice</th><th>Categoria</th><th>Descrizione</th><th>Sottocategorie</th></tr>
    </thead>
    <tbody>${taxRows}</tbody>
  </table>
</body>
</html>`;

    const blob = new Blob([html], { type: "text/html;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `NIS2_METODO_${selected.id.slice(0, 8)}.html`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function isCriterionSatisfied(
    criterion: ClassificationMethod["nis2_method"]["criteria"][number],
    incident: Incident
  ): boolean {
    if (criterion.type === "boolean") {
      return Boolean((incident as Record<string, unknown>)[criterion.key]);
    }
    const incidentValue = Number((incident as Record<string, unknown>)[criterion.key] ?? 0);
    const threshold = Number(criterion.threshold ?? 0);
    return incidentValue >= threshold;
  }

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
                    <div className="flex gap-1">
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
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          if (confirm(`Eliminare l'incidente "${inc.title}"?`)) deleteMutation.mutate(inc.id);
                        }}
                        className="text-xs text-gray-400 hover:text-red-600 border border-gray-200 rounded px-2 py-0.5 hover:border-red-300"
                      >
                        🗑
                      </button>
                    </div>
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
              {(["gestione","classificazione","metodo","timeline","config"] as const).map(tab => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-3 py-1.5 text-xs rounded ${activeTab === tab ? "bg-primary-600 text-white" : "bg-gray-100 text-gray-600"}`}
                >
                  {tab === "gestione" ? "Gestione" : tab === "classificazione" ? "Classificazione NIS2" : tab === "metodo" ? "Metodo di classificazione" : tab === "timeline" ? "Timeline NIS2 & Notifiche" : "Configurazione NIS2"}
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
                    <label className="text-xs text-gray-600">Classificazione ENISA</label>
                    <select
                      className="w-full border rounded px-3 py-2 text-sm"
                      value={selected.incident_category ?? ""}
                      onChange={e => setSelected({ ...selected, incident_category: e.target.value, incident_subcategory: "" })}
                    >
                      <option value="">— seleziona —</option>
                      {enisaCategories.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-gray-600">Dettaglio categoria</label>
                    <select
                      className="w-full border rounded px-3 py-2 text-sm"
                      value={selected.incident_subcategory ?? ""}
                      onChange={e => setSelected({ ...selected, incident_subcategory: e.target.value })}
                    >
                      <option value="">— seleziona —</option>
                      {(enisaSubcategories[selected.incident_category ?? ""] ?? []).map(s => (
                        <option key={s.value} value={s.value}>{s.label}</option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <input className="border rounded px-3 py-2 text-sm" placeholder="Utenti o sistemi coinvolti (n.)" value={selected.affected_users_count ?? ""} onChange={e => setSelected({ ...selected, affected_users_count: e.target.value ? Number(e.target.value) : null })} />
                  <input className="border rounded px-3 py-2 text-sm" placeholder="Durata interruzione servizio (ore)" value={selected.service_disruption_hours ?? ""} onChange={e => setSelected({ ...selected, service_disruption_hours: e.target.value || null })} />
                  <input className="border rounded px-3 py-2 text-sm" placeholder="Impatto economico stimato (EUR)" value={selected.financial_impact_eur ?? ""} onChange={e => setSelected({ ...selected, financial_impact_eur: e.target.value || null })} />
                </div>
                <div className="flex gap-4 text-sm">
                  <label><input type="checkbox" checked={!!selected.personal_data_involved} onChange={e => setSelected({ ...selected, personal_data_involved: e.target.checked })} /> Coinvolgimento dati personali</label>
                  <label><input type="checkbox" checked={!!selected.cross_border_impact} onChange={e => setSelected({ ...selected, cross_border_impact: e.target.checked })} /> Impatto multi-paese (cross-border)</label>
                  <label><input type="checkbox" checked={!!selected.critical_infrastructure_impact} onChange={e => setSelected({ ...selected, critical_infrastructure_impact: e.target.checked })} /> Impatto su infrastrutture critiche</label>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => updateMutation.mutate({ id: selected.id, payload: selected })}
                    disabled={updateMutation.isPending}
                    className="px-3 py-2 text-xs bg-primary-600 text-white rounded disabled:opacity-50"
                  >
                    {updateMutation.isPending ? "Aggiornamento in corso..." : "Salva aggiornamento gestione"}
                  </button>
                  {updateMutation.isSuccess && <span className="text-xs text-green-600">✓ Aggiornamento registrato</span>}
                  {updateMutation.isError && <span className="text-xs text-red-500">Errore durante l'aggiornamento</span>}
                </div>
              </div>
            )}

            {activeTab === "classificazione" && (
              <div className="p-4 space-y-3">
                {selected.is_significant === true && <div className="px-3 py-2 bg-red-50 text-red-700 rounded text-sm">Incidente classificato SIGNIFICATIVO: obbligo di notifica NIS2.</div>}
                {selected.is_significant === false && <div className="px-3 py-2 bg-green-50 text-green-700 rounded text-sm">Incidente classificato NON significativo: monitoraggio interno.</div>}
                {selected.is_significant == null && <div className="px-3 py-2 bg-yellow-50 text-yellow-700 rounded text-sm">Classificazione non ancora definita.</div>}
                <button onClick={() => classifyMutation.mutate({ id: selected.id })} className="px-3 py-2 text-xs bg-primary-600 text-white rounded">Esegui valutazione automatica</button>
                <div className="rounded border p-3 space-y-1">
                  <div className="text-xs font-medium text-gray-700">Criteri decisionali (soglie sito)</div>
                  <div className="text-xs">
                    {(selected.affected_users_count ?? 0) >= thresholdUsers ? "✅" : "❌"} Utenti colpiti: {selected.affected_users_count ?? 0} (soglia: {thresholdUsers})
                  </div>
                  <div className="text-xs">
                    {Number(selected.service_disruption_hours ?? 0) >= thresholdHours ? "✅" : "❌"} Ore interruzione: {selected.service_disruption_hours ?? 0}h (soglia: {thresholdHours}h)
                  </div>
                  <div className="text-xs">
                    {Number(selected.financial_impact_eur ?? 0) >= thresholdFinancial ? "✅" : "❌"} Impatto finanziario: {selected.financial_impact_eur ?? 0} EUR (soglia: {thresholdFinancial} EUR)
                  </div>
                  <div className="text-xs">{selected.personal_data_involved ? "✅" : "❌"} Dati personali coinvolti</div>
                  <div className="text-xs">{selected.cross_border_impact ? "✅" : "❌"} Impatto cross-border</div>
                  <div className="text-xs">{selected.critical_infrastructure_impact ? "✅" : "❌"} Infrastrutture critiche</div>
                </div>
                <div className="rounded border p-3 space-y-2">
                  <label className="text-xs flex items-center gap-2">
                    <input type="checkbox" checked={overrideEnabled} onChange={(e) => setOverrideEnabled(e.target.checked)} />
                    Applica decisione manuale (override)
                  </label>
                  {overrideEnabled && (
                    <>
                      <select
                        value={overrideValue}
                        onChange={(e) => setOverrideValue(e.target.value as "significant" | "not_significant")}
                        className="w-full border rounded px-2 py-1.5 text-sm"
                      >
                        <option value="significant">Esito manuale: Significativo</option>
                        <option value="not_significant">Esito manuale: Non significativo</option>
                      </select>
                      <textarea
                        rows={2}
                        value={overrideReason}
                        onChange={(e) => setOverrideReason(e.target.value)}
                        className="w-full border rounded px-2 py-1.5 text-sm"
                        placeholder="Business rationale della decisione (obbligatoria)"
                      />
                      <button
                        onClick={() => classifyMutation.mutate({
                          id: selected.id,
                          data: {
                            override: overrideValue === "significant",
                            reason: overrideReason,
                          },
                        })}
                        disabled={!overrideReason.trim()}
                        className="px-3 py-2 text-xs bg-amber-600 text-white rounded disabled:opacity-50"
                      >
                        Conferma decisione manuale
                      </button>
                    </>
                  )}
                </div>
              </div>
            )}

            {activeTab === "metodo" && (
              <div className="p-4 space-y-4">
                <div className="flex justify-end">
                  <button
                    onClick={exportClassificationMethodHtml}
                    disabled={!selected || !classificationMethod}
                    className="px-3 py-1.5 text-xs border rounded disabled:opacity-50"
                  >
                    Esporta metodo (HTML)
                  </button>
                </div>
                <div className="rounded border bg-blue-50 border-blue-100 p-3">
                  <div className="text-sm font-medium text-blue-900">Metodo di classificazione NIS2</div>
                  <div className="text-xs text-blue-900 mt-1">
                    {classificationMethod?.nis2_method.rule ??
                      "Incidente significativo se almeno un criterio risulta soddisfatto; override manuale con motivazione ha precedenza."}
                  </div>
                </div>

                <div className="rounded border p-3">
                  <div className="text-sm font-medium mb-2">Valutazione corrente incidente selezionato</div>
                  <div className="overflow-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="text-left text-gray-500 border-b">
                          <th className="py-1 pr-2">Esito</th>
                          <th className="py-1 pr-2">Criterio</th>
                          <th className="py-1 pr-2">Valore corrente</th>
                          <th className="py-1 pr-2">Soglia</th>
                          <th className="py-1 pr-2">Fonte</th>
                        </tr>
                      </thead>
                      <tbody>
                    {(classificationMethod?.nis2_method.criteria ?? []).map((criterion) => {
                      const satisfied = isCriterionSatisfied(criterion, selected);
                      const incidentRaw = (selected as Record<string, unknown>)[criterion.key];
                      const incidentDisplay =
                        criterion.type === "boolean"
                          ? (incidentRaw ? "Sì" : "No")
                          : String(incidentRaw ?? 0);
                      const sourceLabel = criterion.type === "threshold" ? "input utente + soglia sito" : "flag booleano";
                      return (
                        <tr key={`eval-${criterion.key}`} className="border-b last:border-b-0">
                          <td className="py-1 pr-2">{satisfied ? "✅" : "❌"}</td>
                          <td className="py-1 pr-2 text-gray-700">{criterion.label}</td>
                          <td className="py-1 pr-2 text-gray-700">{incidentDisplay}</td>
                          <td className="py-1 pr-2 text-gray-700">
                            {criterion.type === "threshold" ? String(criterion.threshold ?? "—") : "—"}
                          </td>
                          <td className="py-1 pr-2 text-gray-600">{sourceLabel}</td>
                        </tr>
                      );
                    })}
                      </tbody>
                    </table>
                  </div>
                  <div className="mt-2 text-xs font-medium">
                    Esito automatico atteso:{" "}
                    {(classificationMethod?.nis2_method.criteria ?? []).some((criterion) =>
                      isCriterionSatisfied(criterion, selected)
                    )
                      ? "SIGNIFICATIVO (almeno un criterio soddisfatto)"
                      : "NON significativo (nessun criterio soddisfatto)"}
                  </div>
                  {selected.significance_override !== null && selected.significance_override !== undefined && (
                    <div className="mt-1 text-xs text-amber-700">
                      Override manuale attivo: prevale l'esito manuale con motivazione.
                    </div>
                  )}
                </div>

                <div className="rounded border p-3">
                  <div className="text-sm font-medium mb-2">Criteri decisionali e soglie</div>
                  <div className="space-y-1">
                    {(classificationMethod?.nis2_method.criteria ?? []).map((criterion) => (
                      <div key={criterion.key} className="text-xs text-gray-700">
                        {criterion.type === "threshold"
                          ? `- ${criterion.label}: valore ${criterion.operator} ${criterion.threshold}`
                          : `- ${criterion.label}: criterio booleano`}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="rounded border p-3">
                  <div className="text-sm font-medium mb-2">Tassonomia ENISA ufficiale</div>
                  <div className="space-y-2">
                    {(classificationMethod?.taxonomy.categories ?? []).map((category) => (
                      <div key={category.code} className="rounded border bg-gray-50 p-2">
                        <div className="text-xs font-semibold">
                          {category.code} — {category.label}
                        </div>
                        <div className="text-xs text-gray-600">{category.description}</div>
                        <div className="mt-1 text-xs text-gray-700">
                          Sottocategorie:{" "}
                          {(classificationMethod?.taxonomy.subcategories[category.code] ?? [])
                            .map((sub) => sub.label)
                            .join(", ") || "non definite"}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {activeTab === "timeline" && (
              <div className="p-4 space-y-4">
                {(timeline as NIS2Timeline | undefined)?.steps?.map(step => (
                  <div key={step.step} className="border rounded p-3">
                    <div className="font-medium text-sm">{step.label}</div>
                    <div className="text-xs text-gray-500">Scadenza regolatoria: {step.deadline ? new Date(step.deadline).toLocaleString(dateLocale) : "—"}</div>
                    <div className="text-xs">Stato avanzamento: <strong>{step.status}</strong></div>
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
                        Genera documento ufficiale
                      </button>
                      <button onClick={() => setSentType(step.step)} className="text-xs border rounded px-2 py-1">Prepara registrazione invio</button>
                    </div>
                  </div>
                ))}
                <div className="border rounded p-3 space-y-2">
                  <div className="text-sm font-medium">Registra invio verso autorita</div>
                  <select value={sentType} onChange={e => setSentType(e.target.value)} className="w-full border rounded px-2 py-1.5 text-sm">
                    <option value="early_warning">Early Warning</option>
                    <option value="formal_notification">Notifica formale</option>
                    <option value="final_report">Report finale</option>
                    <option value="update">Aggiornamento</option>
                  </select>
                  <input className="w-full border rounded px-2 py-1.5 text-sm" placeholder="Protocollo autorita / riferimento pratica" value={protocolRef} onChange={e => setProtocolRef(e.target.value)} />
                  <textarea className="w-full border rounded px-2 py-1.5 text-sm" rows={2} placeholder="Esito o note dell'autorita competente" value={authorityResponse} onChange={e => setAuthorityResponse(e.target.value)} />
                  <button onClick={() => markSentMutation.mutate(selected.id)} className="px-3 py-2 text-xs bg-primary-600 text-white rounded">Conferma registrazione invio</button>
                </div>
                <div className="border rounded p-3">
                  <div className="text-sm font-medium mb-2">Registro notifiche ufficiali</div>
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
                  <div className="text-sm font-medium mb-2">Bozza RCA assistita da AI</div>
                  <AiSuggestionBanner
                    taskType="rca_draft"
                    entityId={selected.id}
                    autoTrigger={false}
                    onAccept={(res) => {
                      setRcaDraftData((res as Record<string, unknown>) ?? null);
                      setRcaDraftText(formatRcaText(res));
                    }}
                    onIgnore={() => {}}
                  />
                  {rcaDraftData && (
                    <div className="mt-3 rounded border border-indigo-100 bg-indigo-50 p-3 text-xs text-gray-800 space-y-2">
                      <div className="text-sm font-semibold text-indigo-900">Executive RCA Preview</div>
                      <div>
                        <div className="font-medium">Sommario esecutivo</div>
                        <div>{String(rcaDraftData.summary ?? "—")}</div>
                      </div>
                      <div>
                        <div className="font-medium">Causa radice</div>
                        <div>{String(rcaDraftData.root_cause ?? "—")}</div>
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <div className="font-medium">Azioni immediate</div>
                          <div className="whitespace-pre-wrap">{listText(rcaDraftData.immediate_actions)}</div>
                        </div>
                        <div>
                          <div className="font-medium">Azioni preventive</div>
                          <div className="whitespace-pre-wrap">{listText(rcaDraftData.preventive_actions)}</div>
                        </div>
                      </div>
                      <div>
                        <div className="font-medium">Lessons learned</div>
                        <div>{String(rcaDraftData.lessons_learned ?? "—")}</div>
                      </div>
                    </div>
                  )}
                  <textarea
                    className="mt-3 w-full border rounded px-3 py-2 text-xs min-h-40"
                    value={rcaDraftText}
                    onChange={(e) => setRcaDraftText(e.target.value)}
                    placeholder="Bozza RCA editabile in formato operativo."
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
                <div className="text-xs text-gray-500 bg-blue-50 border border-blue-100 rounded p-2">
                  Soglie di significatività: se l'incidente supera anche solo uno di questi valori, viene classificato come <strong>significativo NIS2</strong> con obbligo di notifica al CSIRT.
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div className="space-y-1">
                    <label className="text-xs font-medium text-gray-600">Utenti/sistemi colpiti (n°)</label>
                    <input className="w-full border rounded px-2 py-1.5 text-sm" value={configForm.threshold_users ?? currentConfig?.threshold_users ?? 100} onChange={e => setConfigForm(f => ({ ...f, threshold_users: Number(e.target.value) }))} />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-medium text-gray-600">Ore di interruzione servizio</label>
                    <input className="w-full border rounded px-2 py-1.5 text-sm" value={configForm.threshold_hours ?? currentConfig?.threshold_hours ?? 4} onChange={e => setConfigForm(f => ({ ...f, threshold_hours: Number(e.target.value) }))} />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-medium text-gray-600">Impatto finanziario (€)</label>
                    <input className="w-full border rounded px-2 py-1.5 text-sm" value={configForm.threshold_financial ?? currentConfig?.threshold_financial ?? 100000} onChange={e => setConfigForm(f => ({ ...f, threshold_financial: Number(e.target.value) }))} />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-xs font-medium text-gray-600">Settore NIS2</label>
                    <input className="w-full border rounded px-2 py-1.5 text-sm" placeholder="es. Trasporti, Energia..." value={configForm.nis2_sector ?? currentConfig?.nis2_sector ?? ""} onChange={e => setConfigForm(f => ({ ...f, nis2_sector: e.target.value }))} />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-medium text-gray-600">Sottosettore NIS2</label>
                    <input className="w-full border rounded px-2 py-1.5 text-sm" placeholder="es. Automotive, Manifatturiero..." value={configForm.nis2_subsector ?? currentConfig?.nis2_subsector ?? ""} onChange={e => setConfigForm(f => ({ ...f, nis2_subsector: e.target.value }))} />
                  </div>
                </div>
                <div className="text-xs font-medium text-gray-600 pt-1">Referente NIS2 interno</div>
                <div className="grid grid-cols-3 gap-3">
                  <div className="space-y-1">
                    <label className="text-xs text-gray-500">Nome</label>
                    <input className="w-full border rounded px-2 py-1.5 text-sm" value={configForm.internal_contact_name ?? currentConfig?.internal_contact_name ?? ""} onChange={e => setConfigForm(f => ({ ...f, internal_contact_name: e.target.value }))} />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs text-gray-500">Email</label>
                    <input className="w-full border rounded px-2 py-1.5 text-sm" value={configForm.internal_contact_email ?? currentConfig?.internal_contact_email ?? ""} onChange={e => setConfigForm(f => ({ ...f, internal_contact_email: e.target.value }))} />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs text-gray-500">Telefono</label>
                    <input className="w-full border rounded px-2 py-1.5 text-sm" value={configForm.internal_contact_phone ?? currentConfig?.internal_contact_phone ?? ""} onChange={e => setConfigForm(f => ({ ...f, internal_contact_phone: e.target.value }))} />
                  </div>
                </div>
                <div className="text-xs font-medium text-gray-600 pt-1">Entità legale</div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-xs text-gray-500">Ragione sociale</label>
                    <input className="w-full border rounded px-2 py-1.5 text-sm" value={configForm.legal_entity_name ?? currentConfig?.legal_entity_name ?? ""} onChange={e => setConfigForm(f => ({ ...f, legal_entity_name: e.target.value }))} />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs text-gray-500">Partita IVA / VAT</label>
                    <input className="w-full border rounded px-2 py-1.5 text-sm" value={configForm.legal_entity_vat ?? currentConfig?.legal_entity_vat ?? ""} onChange={e => setConfigForm(f => ({ ...f, legal_entity_vat: e.target.value }))} />
                  </div>
                </div>
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
