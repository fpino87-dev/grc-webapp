import { useEffect, useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { AxiosError } from "axios";
import {
  incidentsApi,
  type ClassificationBreakdown,
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
  const [previewBreakdown, setPreviewBreakdown] = useState<ClassificationBreakdown | null>(null);
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
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ["incidents"] });
      qc.invalidateQueries({ queryKey: ["classification-breakdown", variables.id] });
      setPreviewBreakdown(null);
    },
  });
  const classifyMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data?: { override?: boolean; reason?: string } }) =>
      incidentsApi.classifySignificance(id, data),
    onSuccess: (res: { is_significant?: boolean }, variables) => {
      qc.invalidateQueries({ queryKey: ["incidents"] });
      qc.invalidateQueries({ queryKey: ["classification-breakdown", variables.id] });
      setPreviewBreakdown(null);
      if (selected && typeof res?.is_significant === "boolean") {
        setSelected({
          ...selected,
          is_significant: res.is_significant,
          nis2_notifiable: res.is_significant ? "si" : "no",
        });
      }
      setOverrideEnabled(false);
    },
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
  const { data: serverBreakdown } = useQuery({
    queryKey: ["classification-breakdown", selected?.id],
    queryFn: () => incidentsApi.classificationBreakdown(selected!.id),
    enabled: !!selected?.id,
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
    multiplier_medium: 2,
    multiplier_high: 3,
    ptnr_threshold: 4,
    recurrence_window_days: 90,
    recurrence_score_bonus: 2,
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

  useEffect(() => {
    setPreviewBreakdown(null);
  }, [selected?.id]);

  useEffect(() => {
    if (!selected?.plant || activeTab !== "classificazione") return;
    const t = window.setTimeout(() => {
      incidentsApi
        .classificationPreview({
          plant_id: selected.plant,
          service_disruption_hours: selected.service_disruption_hours ?? null,
          financial_impact_eur: selected.financial_impact_eur ?? null,
          affected_users_count: selected.affected_users_count ?? null,
          personal_data_involved: selected.personal_data_involved ?? false,
          cross_border_impact: selected.cross_border_impact ?? false,
          critical_infrastructure_impact: selected.critical_infrastructure_impact ?? false,
          incident_category: selected.incident_category ?? "",
          severity: selected.severity ?? "bassa",
          is_recurrent_override: selected.is_recurrent ?? false,
        })
        .then(setPreviewBreakdown)
        .catch(() => setPreviewBreakdown(null));
    }, 600);
    return () => clearTimeout(t);
  }, [
    activeTab,
    selected?.plant,
    selected?.service_disruption_hours,
    selected?.financial_impact_eur,
    selected?.affected_users_count,
    selected?.personal_data_involved,
    selected?.cross_border_impact,
    selected?.critical_infrastructure_impact,
    selected?.incident_category,
    selected?.severity,
    selected?.is_recurrent,
  ]);

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
      multiplier_medium: currentConfig.multiplier_medium ?? 2,
      multiplier_high: currentConfig.multiplier_high ?? 3,
      ptnr_threshold: currentConfig.ptnr_threshold ?? 4,
      recurrence_window_days: currentConfig.recurrence_window_days ?? 90,
      recurrence_score_bonus: currentConfig.recurrence_score_bonus ?? 2,
      nis2_activity_description: currentConfig.nis2_activity_description ?? "",
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

  const breakdown = previewBreakdown ?? serverBreakdown ?? undefined;
  const plantNis2Scope = plants?.find((p) => p.id === selected?.plant)?.nis2_scope;

  function axisBarClass(score: number): string {
    if (score <= 2) return "bg-emerald-500";
    if (score === 3) return "bg-amber-400";
    if (score === 4) return "bg-orange-500";
    return "bg-red-600";
  }

  const axisOrder = ["operativo", "economico", "persone", "riservatezza", "reputazionale"] as const;

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
              <div className="p-4 space-y-4">
                {classifyMutation.isSuccess && (
                  <div className="px-3 py-2 bg-emerald-50 text-emerald-700 rounded text-sm">
                    {t("incidents.nis2_classification.classify_success")}
                  </div>
                )}
                {classifyMutation.isError && (
                  <div className="px-3 py-2 bg-red-50 text-red-700 rounded text-sm">
                    {(
                      (classifyMutation.error as AxiosError<{ error?: string }>)?.response?.data?.error ??
                      t("incidents.nis2_classification.classify_error")
                    )}
                  </div>
                )}

                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs font-medium text-gray-600">{t("incidents.nis2_classification.scope_label")}</span>
                  {plantNis2Scope === "essenziale" && (
                    <span className="px-2 py-0.5 rounded text-xs font-semibold bg-red-900 text-white">
                      {t("incidents.nis2_classification.scope.essenziale")}
                    </span>
                  )}
                  {plantNis2Scope === "importante" && (
                    <span className="px-2 py-0.5 rounded text-xs font-semibold bg-orange-600 text-white">
                      {t("incidents.nis2_classification.scope.importante")}
                    </span>
                  )}
                  {plantNis2Scope === "non_soggetto" && (
                    <span className="px-2 py-0.5 rounded text-xs font-semibold bg-gray-500 text-white">
                      {t("incidents.nis2_classification.scope.non_soggetto")}
                    </span>
                  )}
                </div>

                {plantNis2Scope === "non_soggetto" ? (
                  <div className="rounded border border-gray-200 bg-gray-50 p-3 text-sm text-gray-700">
                    {t("incidents.nis2_classification.site_non_subject")}
                  </div>
                ) : !breakdown || (!breakdown.scores && !breakdown.message) ? (
                  <div className="text-sm text-gray-500">{t("common.loading")}</div>
                ) : breakdown.message && !breakdown.scores ? (
                  <div className="rounded border border-gray-200 bg-gray-50 p-3 text-sm">{breakdown.message}</div>
                ) : breakdown.scores && breakdown.pta_ptnr && breakdown.decision ? (
                  <>
                    <div className="flex items-center justify-between gap-2">
                      <button
                        type="button"
                        onClick={() => classifyMutation.mutate({ id: selected.id })}
                        className="px-3 py-2 text-xs bg-primary-600 text-white rounded"
                      >
                        {t("incidents.nis2_classification.run_auto")}
                      </button>
                      {previewBreakdown && (
                        <span className="text-xs text-amber-700">{t("incidents.nis2_classification.preview_live")}</span>
                      )}
                    </div>

                    <div className="overflow-x-auto rounded border border-gray-200">
                      <table className="w-full text-xs">
                        <thead className="bg-gray-50 border-b border-gray-200">
                          <tr>
                            <th className="text-left px-3 py-2 font-medium text-gray-700">{t("incidents.nis2_classification.table.axis")}</th>
                            <th className="text-left px-3 py-2 font-medium text-gray-700">{t("incidents.nis2_classification.table.value")}</th>
                            <th className="text-left px-3 py-2 font-medium text-gray-700">{t("incidents.nis2_classification.table.threshold")}</th>
                            <th className="text-left px-3 py-2 font-medium text-gray-700">{t("incidents.nis2_classification.table.score")}</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                          {axisOrder.map((key) => {
                            const row = breakdown.scores![key];
                            if (!row) return null;
                            const valDisplay =
                              key === "operativo"
                                ? `${row.value ?? 0}h`
                                : key === "economico"
                                  ? `€${Number(row.value ?? 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`
                                  : key === "persone"
                                    ? String(row.value ?? 0)
                                    : "—";
                            const thr =
                              row.threshold != null
                                ? key === "operativo"
                                  ? `${row.threshold}h`
                                  : key === "economico"
                                    ? `€${Number(row.threshold).toLocaleString()}`
                                    : String(row.threshold)
                                : "—";
                            return (
                              <tr key={key}>
                                <td className="px-3 py-2 align-top font-medium text-gray-800">
                                  {t(`incidents.nis2_classification.axis.${key}`)}
                                </td>
                                <td className="px-3 py-2 align-top text-gray-700">{valDisplay}</td>
                                <td className="px-3 py-2 align-top text-gray-600">{thr}</td>
                                <td className="px-3 py-2 align-top">
                                  <div className="flex items-center gap-2">
                                    <div className="flex gap-0.5">
                                      {[1, 2, 3, 4, 5].map((i) => (
                                        <div
                                          key={i}
                                          className={`h-2 w-5 rounded-sm ${i <= row.score ? axisBarClass(row.score) : "bg-gray-200"}`}
                                        />
                                      ))}
                                    </div>
                                    <span className="text-gray-700 whitespace-nowrap">
                                      {row.score}/5
                                      {key === "riservatezza" && row.score >= 4 ? " ⚠️" : ""}
                                    </span>
                                  </div>
                                  <div className="mt-1 text-[11px] text-gray-500">{row.note}</div>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>

                    <div className="rounded border border-indigo-100 bg-indigo-50/80 p-3 space-y-1 text-xs text-gray-800">
                      <div>
                        <strong>PTA</strong> = {breakdown.pta_ptnr.PTA} ({t("incidents.nis2_classification.dominant")}:{" "}
                        {t(`incidents.nis2_classification.axis.${breakdown.pta_ptnr.asse_dominante}`)})
                      </div>
                      <div>
                        {t("incidents.nis2_classification.recurrence.label")}:{" "}
                        {breakdown.pta_ptnr.is_recurrent
                          ? t("incidents.nis2_classification.recurrence.yes_bonus", { n: breakdown.pta_ptnr.ricorrenza_bonus })
                          : t("incidents.nis2_classification.recurrence.no_bonus")}
                        {breakdown.recurrence?.auto_detected && (
                          <span className="ml-1 text-amber-800">({t("incidents.nis2_classification.recurrence.auto")})</span>
                        )}
                        {breakdown.recurrence?.manual_toggle && !breakdown.recurrence?.auto_detected && (
                          <span className="ml-1 text-amber-800">({t("incidents.nis2_classification.recurrence.manual")})</span>
                        )}
                      </div>
                      <div>
                        <strong>PTNR</strong> = {breakdown.pta_ptnr.PTNR}
                      </div>
                    </div>

                    <div className="rounded border border-gray-200 p-3 space-y-2">
                      <div className="text-xs font-semibold text-gray-800">{t("incidents.nis2_classification.fattispecie_title")}</div>
                      <div className="space-y-1">
                        {Object.entries(breakdown.fattispecie).map(([code, spec]) => (
                          <div key={code} className="flex items-start gap-2 text-xs text-gray-700">
                            <span>
                              {spec.active && spec.applicable ? "✅" : spec.applicable ? "⬜" : "🔒"}
                            </span>
                            <span>
                              {code} — {spec.label}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div
                      className={`rounded border p-3 space-y-2 ${
                        breakdown.decision.is_significant
                          ? "border-red-700 bg-red-50"
                          : "border-emerald-200 bg-emerald-50"
                      }`}
                    >
                      {breakdown.decision.is_significant ? (
                        <>
                          <div className="text-sm font-bold text-red-800">{t("incidents.nis2_classification.decision.significant_title")}</div>
                          <div className="text-xs text-red-900">{t("incidents.nis2_classification.decision.significant_sub")}</div>
                        </>
                      ) : (
                        <>
                          <div className="text-sm font-bold text-emerald-800">{t("incidents.nis2_classification.decision.not_significant_title")}</div>
                          <div className="text-xs text-emerald-900">{t("incidents.nis2_classification.decision.not_significant_sub")}</div>
                          <div className="text-xs text-gray-600">{t("incidents.nis2_classification.decision.voluntary_note")}</div>
                        </>
                      )}
                      <div className="text-xs text-gray-800 whitespace-pre-wrap">{breakdown.decision.rationale}</div>
                      {breakdown.decision.is_significant && (
                        <button
                          type="button"
                          onClick={() => setActiveTab("timeline")}
                          className="mt-1 px-3 py-1.5 text-xs bg-red-800 text-white rounded"
                        >
                          {t("incidents.nis2_classification.timeline_cta")}
                        </button>
                      )}
                    </div>

                    <div className="rounded border border-dashed border-gray-300 p-3 space-y-2 text-xs text-gray-700">
                      <div className="font-medium text-gray-800">{t("incidents.nis2_classification.recurrence.section_title")}</div>
                      <p>
                        {breakdown.recurrence?.auto_detected
                          ? t("incidents.nis2_classification.recurrence.auto_yes")
                          : t("incidents.nis2_classification.recurrence.auto_no")}
                        {breakdown.recurrence?.last_similar_closed_at && (
                          <>
                            {" "}
                            {new Date(breakdown.recurrence.last_similar_closed_at).toLocaleString(dateLocale)}
                          </>
                        )}
                      </p>
                      <label className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={!!selected.is_recurrent}
                          onChange={(e) => {
                            const v = e.target.checked;
                            setSelected({ ...selected, is_recurrent: v });
                            updateMutation.mutate({ id: selected.id, payload: { is_recurrent: v } });
                          }}
                        />
                        {t("incidents.nis2_classification.recurrence.manual_toggle")}
                      </label>
                    </div>
                  </>
                ) : null}

                <div className="rounded border p-3 space-y-2">
                  <label className="text-xs flex items-center gap-2">
                    <input type="checkbox" checked={overrideEnabled} onChange={(e) => setOverrideEnabled(e.target.checked)} />
                    {t("incidents.nis2_classification.override_toggle")}
                  </label>
                  {overrideEnabled && (
                    <>
                      <select
                        value={overrideValue}
                        onChange={(e) => setOverrideValue(e.target.value as "significant" | "not_significant")}
                        className="w-full border rounded px-2 py-1.5 text-sm"
                      >
                        <option value="significant">{t("incidents.nis2_classification.override_significant")}</option>
                        <option value="not_significant">{t("incidents.nis2_classification.override_not_significant")}</option>
                      </select>
                      <textarea
                        rows={2}
                        value={overrideReason}
                        onChange={(e) => setOverrideReason(e.target.value)}
                        className="w-full border rounded px-2 py-1.5 text-sm"
                        placeholder={t("incidents.nis2_classification.override_reason_ph")}
                      />
                      <button
                        type="button"
                        onClick={() =>
                          classifyMutation.mutate({
                            id: selected.id,
                            data: {
                              override: overrideValue === "significant",
                              reason: overrideReason,
                            },
                          })
                        }
                        disabled={!overrideReason.trim()}
                        className="px-3 py-2 text-xs bg-amber-600 text-white rounded disabled:opacity-50"
                      >
                        {t("incidents.nis2_classification.override_apply")}
                      </button>
                      <p className="text-[11px] text-gray-500">{t("incidents.nis2_classification.override_note")}</p>
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
                  <div className="text-sm font-medium mb-2">Punteggi correnti e obblighi</div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>PTA NIS2: <strong>{classificationMethod?.scores?.pta_nis2 ?? "—"}</strong></div>
                    <div>PTNR NIS2: <strong>{classificationMethod?.scores?.ptnr_nis2 ?? "—"}</strong></div>
                    <div>PT GDPR: <strong>{classificationMethod?.scores?.pt_gdpr ?? "—"}</strong></div>
                    <div>Categoria ACN: <strong>{classificationMethod?.scores?.acn_is_category || "—"}</strong></div>
                    <div>Obbligo CSIRT: <strong>{classificationMethod?.scores?.requires_csirt_notification ? "Sì" : "No"}</strong></div>
                    <div>Valutazione Garante Privacy: <strong>{classificationMethod?.scores?.requires_gdpr_notification ? "Sì" : "No"}</strong></div>
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
                <div className="text-sm font-semibold">{t("incidents.nis2_classification.config.calc_title")}</div>
                <div className="text-xs text-gray-500 bg-blue-50 border border-blue-100 rounded p-2">
                  {t("incidents.nis2_classification.config.ptnr_note")}
                </div>
                <div className="text-xs font-semibold text-gray-700 pt-1">{t("incidents.nis2_classification.config.base_title")}</div>
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
                <div className="text-xs font-semibold text-gray-700 pt-2">{t("incidents.nis2_classification.config.multiplier_title")}</div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-xs font-medium text-gray-600">{t("incidents.nis2_classification.config.multiplier_m")}</label>
                    <input
                      className="w-full border rounded px-2 py-1.5 text-sm"
                      type="number"
                      step="0.01"
                      value={configForm.multiplier_medium ?? currentConfig?.multiplier_medium ?? 2}
                      onChange={(e) => setConfigForm((f) => ({ ...f, multiplier_medium: Number(e.target.value) }))}
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-medium text-gray-600">{t("incidents.nis2_classification.config.multiplier_h")}</label>
                    <input
                      className="w-full border rounded px-2 py-1.5 text-sm"
                      type="number"
                      step="0.01"
                      value={configForm.multiplier_high ?? currentConfig?.multiplier_high ?? 3}
                      onChange={(e) => setConfigForm((f) => ({ ...f, multiplier_high: Number(e.target.value) }))}
                    />
                  </div>
                </div>
                <p className="text-xs text-gray-500">{t("incidents.nis2_classification.config.multiplier_note")}</p>
                <div className="text-xs font-semibold text-gray-700 pt-2">{t("incidents.nis2_classification.config.rule_title")}</div>
                <div className="max-w-xs space-y-1">
                  <label className="text-xs font-medium text-gray-600">{t("incidents.nis2_classification.config.ptnr_threshold")}</label>
                  <input
                    className="w-full border rounded px-2 py-1.5 text-sm"
                    type="number"
                    value={configForm.ptnr_threshold ?? currentConfig?.ptnr_threshold ?? 4}
                    onChange={(e) => setConfigForm((f) => ({ ...f, ptnr_threshold: Number(e.target.value) }))}
                  />
                </div>
                <div className="text-xs font-semibold text-gray-700 pt-2">{t("incidents.nis2_classification.config.recurrence_title")}</div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-xs font-medium text-gray-600">{t("incidents.nis2_classification.config.recurrence_window")}</label>
                    <input
                      className="w-full border rounded px-2 py-1.5 text-sm"
                      type="number"
                      value={configForm.recurrence_window_days ?? currentConfig?.recurrence_window_days ?? 90}
                      onChange={(e) => setConfigForm((f) => ({ ...f, recurrence_window_days: Number(e.target.value) }))}
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-medium text-gray-600">{t("incidents.nis2_classification.config.recurrence_bonus")}</label>
                    <input
                      className="w-full border rounded px-2 py-1.5 text-sm"
                      type="number"
                      value={configForm.recurrence_score_bonus ?? currentConfig?.recurrence_score_bonus ?? 2}
                      onChange={(e) => setConfigForm((f) => ({ ...f, recurrence_score_bonus: Number(e.target.value) }))}
                    />
                  </div>
                </div>
                <p className="text-xs text-gray-500">{t("incidents.nis2_classification.config.recurrence_note")}</p>
                <div className="space-y-1 pt-1">
                  <label className="text-xs font-medium text-gray-600">{t("incidents.nis2_classification.config.activity_desc")}</label>
                  <textarea
                    className="w-full border rounded px-2 py-1.5 text-sm"
                    rows={2}
                    value={configForm.nis2_activity_description ?? currentConfig?.nis2_activity_description ?? ""}
                    onChange={(e) => setConfigForm((f) => ({ ...f, nis2_activity_description: e.target.value }))}
                  />
                </div>
                <div className="text-xs font-semibold text-gray-700 pt-2 border-t border-gray-100 mt-2">Configurazione NIS2 per sito</div>
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
