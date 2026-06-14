import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { AxiosError } from "axios";
import {
  incidentsApi,
  type ClassificationBreakdown,
  type ClassificationMethod,
  type Incident,
  type NIS2Notification,
  type NIS2Timeline,
} from "../../api/endpoints/incidents";
import type { Plant } from "../../api/endpoints/plants";
import { AiSuggestionBanner } from "../../components/ui/AiSuggestionBanner";
import { useTranslation } from "react-i18next";
import i18n from "../../i18n";

export function IncidentDetailModal({
  incident: selected,
  plants,
  onChange,
  onClose,
}: {
  incident: Incident;
  plants: Plant[] | undefined;
  onChange: (updated: Incident) => void;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState<"gestione" | "classificazione" | "metodo" | "timeline">("gestione");
  const [sentType, setSentType] = useState("formal_notification");
  const [protocolRef, setProtocolRef] = useState("");
  const [authorityResponse, setAuthorityResponse] = useState("");
  const [overrideEnabled, setOverrideEnabled] = useState(false);
  const [overrideValue, setOverrideValue] = useState<"significant" | "not_significant">("significant");
  const [overrideReason, setOverrideReason] = useState("");
  const [previewBreakdown, setPreviewBreakdown] = useState<ClassificationBreakdown | null>(null);
  const [rcaDraftText, setRcaDraftText] = useState("");
  const [rcaDraftData, setRcaDraftData] = useState<Record<string, unknown> | null>(null);
  const dateLocale = i18n.language || "it";

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
      if (typeof res?.is_significant === "boolean") {
        onChange({
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
      qc.invalidateQueries({ queryKey: ["nis2-notifications", selected.id] });
      qc.invalidateQueries({ queryKey: ["incidents"] });
      setProtocolRef("");
      setAuthorityResponse("");
    },
  });

  const { data: rca } = useQuery({
    queryKey: ["rca", selected.id],
    queryFn: () => incidentsApi.getRca(selected.id),
  });
  const saveRcaMutation = useMutation({
    mutationFn: () =>
      rca
        ? incidentsApi.updateRca(rca.id, { summary: rcaDraftText })
        : incidentsApi.createRca({ incident: selected.id, summary: rcaDraftText }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rca", selected.id] }),
  });
  const approveRcaMutation = useMutation({
    mutationFn: () => incidentsApi.approveRca(rca!.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rca", selected.id] }),
  });

  const { data: timeline } = useQuery({
    queryKey: ["nis2-timeline", selected.id],
    queryFn: () => incidentsApi.timeline(selected.id),
  });
  const { data: classificationMethod } = useQuery({
    queryKey: ["classification-method", selected.id],
    queryFn: () => incidentsApi.classificationMethod(selected.id),
  });
  const { data: notifications } = useQuery({
    queryKey: ["nis2-notifications", selected.id],
    queryFn: () => incidentsApi.notifications(selected.id),
  });
  const {
    data: serverBreakdown,
    isFetching: breakdownFetching,
    isError: breakdownError,
  } = useQuery({
    queryKey: ["classification-breakdown", selected.id],
    queryFn: () => incidentsApi.classificationBreakdown(selected.id),
  });

  useEffect(() => {
    setPreviewBreakdown(null);
  }, [selected.id]);

  // Precarica il testo RCA salvato (se l'utente non sta già scrivendo).
  useEffect(() => {
    if (rca?.summary) setRcaDraftText((prev) => prev || rca.summary);
  }, [rca?.summary]);

  useEffect(() => {
    if (!selected.plant || activeTab !== "classificazione") return;
    const timer = window.setTimeout(() => {
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
    return () => clearTimeout(timer);
  }, [
    activeTab,
    selected.plant,
    selected.service_disruption_hours,
    selected.financial_impact_eur,
    selected.affected_users_count,
    selected.personal_data_involved,
    selected.cross_border_impact,
    selected.critical_infrastructure_impact,
    selected.incident_category,
    selected.severity,
    selected.is_recurrent,
  ]);

  const enisaCategories = (classificationMethod?.taxonomy.categories ?? []).map((c) => ({ value: c.code, label: c.label }));
  const enisaSubcategories: Record<string, { value: string; label: string }[]> = Object.fromEntries(
    Object.entries(classificationMethod?.taxonomy.subcategories ?? {}).map(([key, values]) => [
      key,
      values.map((entry) => ({ value: entry.code, label: entry.label })),
    ])
  );

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

  function escapeHtml(s: string): string {
    return s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function isCriterionSatisfied(
    criterion: ClassificationMethod["nis2_method"]["criteria"][number],
    incident: Incident
  ): boolean {
    if (criterion.type === "boolean") {
      return Boolean((incident as unknown as Record<string, unknown>)[criterion.key]);
    }
    const incidentValue = Number((incident as unknown as Record<string, unknown>)[criterion.key] ?? 0);
    const threshold = Number(criterion.threshold ?? 0);
    return incidentValue >= threshold;
  }

  function exportClassificationMethodHtml() {
    if (!classificationMethod) return;

    const th = classificationMethod.nis2_method.thresholds;
    const dec = serverBreakdown?.decision;

    const rows = (classificationMethod.nis2_method.criteria ?? [])
      .map((criterion) => {
        const satisfied = isCriterionSatisfied(criterion, selected);
        const incidentRaw = (selected as unknown as Record<string, unknown>)[criterion.key];
        const incidentDisplay =
          criterion.type === "boolean" ? (incidentRaw ? t("common.yes") : t("common.no")) : String(incidentRaw ?? 0);
        const sourceLabel =
          criterion.type === "threshold"
            ? t("incidents.nis2_classification.method_tab.source_threshold")
            : t("incidents.nis2_classification.method_tab.source_flag");
        const reachCell = criterion.type === "boolean" ? "—" : satisfied ? t("common.yes") : t("common.no");
        return `
          <tr>
            <td>${escapeHtml(reachCell)}</td>
            <td>${escapeHtml(criterion.label)}</td>
            <td>${escapeHtml(incidentDisplay)}</td>
            <td>${criterion.type === "threshold" ? String(criterion.threshold ?? "—") : "—"}</td>
            <td>${escapeHtml(sourceLabel)}</td>
          </tr>
        `;
      })
      .join("");

    const taxRows = (classificationMethod.taxonomy.categories ?? [])
      .map((category) => {
        const subs =
          (classificationMethod.taxonomy.subcategories[category.code] ?? [])
            .map((sub) => sub.label)
            .join(", ") || t("incidents.method_extra.none_defined");
        return `
          <tr>
            <td>${escapeHtml(category.code)}</td>
            <td>${escapeHtml(category.label)}</td>
            <td>${escapeHtml(category.description)}</td>
            <td>${escapeHtml(subs)}</td>
          </tr>
        `;
      })
      .join("");

    const expectedLabel =
      dec != null
        ? dec.is_significant
          ? t("incidents.nis2_classification.method_tab.export_significant")
          : t("incidents.nis2_classification.method_tab.export_not_significant")
        : t("incidents.nis2_classification.method_tab.export_no_breakdown");
    const rationaleHtml = dec?.rationale
      ? `<div style="margin-top:8px;"><strong>${t("incidents.nis2_classification.method_tab.export_rationale")}:</strong> ${escapeHtml(dec.rationale)}</div>`
      : "";
    const ptnrLine =
      serverBreakdown?.pta_ptnr != null
        ? `<div style="margin-top:8px;">PTA=${serverBreakdown.pta_ptnr.PTA}, PTNR=${serverBreakdown.pta_ptnr.PTNR}</div>`
        : "";

    const configBlock = `
  <h2>${t("incidents.nis2_classification.method_tab.export_config_h2")}</h2>
  <table>
    <tbody>
      <tr><th>${t("incidents.nis2_classification.method_tab.config_users")}</th><td>${th.affected_users_count}</td></tr>
      <tr><th>${t("incidents.nis2_classification.method_tab.config_hours")}</th><td>${th.service_disruption_hours}</td></tr>
      <tr><th>${t("incidents.nis2_classification.method_tab.config_financial")}</th><td>${th.financial_impact_eur}</td></tr>
      <tr><th>${t("incidents.nis2_classification.method_tab.config_mult_m")}</th><td>${th.multiplier_medium ?? "—"}</td></tr>
      <tr><th>${t("incidents.nis2_classification.method_tab.config_mult_h")}</th><td>${th.multiplier_high ?? "—"}</td></tr>
      <tr><th>${t("incidents.nis2_classification.method_tab.config_ptnr")}</th><td>${th.ptnr_trigger_csirt ?? "—"}</td></tr>
      <tr><th>${t("incidents.nis2_classification.method_tab.config_rec_window")}</th><td>${th.recurrence_window_days ?? "—"}</td></tr>
      <tr><th>${t("incidents.nis2_classification.method_tab.config_rec_bonus")}</th><td>${th.recurrence_score_bonus ?? "—"}</td></tr>
    </tbody>
  </table>`;

    const html = `<!DOCTYPE html>
<html lang="${i18n.language || "it"}">
<head>
  <meta charset="UTF-8" />
  <title>${t("incidents.nis2_classification.method_tab.export_doc_title")}</title>
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
  <h1>${t("incidents.nis2_classification.method_tab.export_h1")}</h1>
  <div>${t("incidents.nis2_classification.method_tab.export_incident")}: <strong>${escapeHtml(selected.title)}</strong></div>
  <div>${t("incidents.nis2_classification.method_tab.export_date")}: ${new Date().toLocaleString(dateLocale)}</div>
  <div style="margin-top: 8px;"><strong>${t("incidents.nis2_classification.method_tab.export_rule_label")}:</strong> ${escapeHtml(classificationMethod.nis2_method.rule)}</div>
  <div style="margin-top: 8px;"><strong>${t("incidents.nis2_classification.method_tab.export_model_label")}:</strong> ${classificationMethod.nis2_method.decision_model ?? "ptnr_or_fattispecie"}</div>
  ${
    classificationMethod.nis2_method.criteria_disclaimer
      ? `<p style="margin-top:8px; font-size:11px; color:#4b5563;">${escapeHtml(classificationMethod.nis2_method.criteria_disclaimer)}</p>`
      : ""
  }
  <div style="margin-top: 8px;"><strong>${t("incidents.nis2_classification.method_tab.export_engine_label")}:</strong> <span class="badge">${escapeHtml(expectedLabel)}</span></div>
  ${ptnrLine}
  ${rationaleHtml}
  ${configBlock}
  <p style="margin-top:12px; font-size:11px; color:#4b5563;">${t("incidents.nis2_classification.method_tab.export_inputs_note")}</p>

  <h2>${t("incidents.nis2_classification.method_tab.export_inputs_h2")}</h2>
  <table>
    <thead>
      <tr><th>${t("incidents.nis2_classification.method_tab.col_reaches_base")}</th><th>${t("incidents.nis2_classification.method_tab.export_col_criterion")}</th><th>${t("incidents.nis2_classification.method_tab.export_col_value")}</th><th>${t("incidents.nis2_classification.method_tab.export_col_threshold")}</th><th>${t("incidents.nis2_classification.method_tab.export_col_source")}</th></tr>
    </thead>
    <tbody>${rows}</tbody>
  </table>

  <h2>${t("incidents.nis2_classification.method_tab.export_taxonomy_h2")}</h2>
  <table>
    <thead>
      <tr><th>${t("incidents.nis2_classification.method_tab.export_col_code")}</th><th>${t("incidents.nis2_classification.method_tab.export_col_category")}</th><th>${t("incidents.nis2_classification.method_tab.export_col_desc")}</th><th>${t("incidents.nis2_classification.method_tab.export_col_subs")}</th></tr>
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

  const breakdown = previewBreakdown ?? serverBreakdown ?? undefined;
  const plantNis2Scope = plants?.find((p) => p.id === selected.plant)?.nis2_scope;

  function axisBarClass(score: number): string {
    if (score <= 2) return "bg-emerald-500";
    if (score === 3) return "bg-amber-400";
    if (score === 4) return "bg-orange-500";
    return "bg-red-600";
  }

  const axisOrder = ["operativo", "economico", "persone", "riservatezza", "reputazionale"] as const;

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg w-full max-w-5xl max-h-[92vh] overflow-auto">
        <div className="p-4 border-b flex items-center justify-between">
          <h3 className="text-lg font-semibold">{selected.title}</h3>
          <button onClick={onClose} className="text-gray-500">×</button>
        </div>
        <div className="px-4 pt-3 flex flex-wrap gap-2">
          {(["gestione", "classificazione", "metodo", "timeline"] as const).map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={`px-3 py-1.5 text-xs rounded ${activeTab === tab ? "bg-primary-600 text-white" : "bg-gray-100 text-gray-600"}`}
            >
              {tab === "gestione"
                ? t("incidents.detail_tabs.management")
                : tab === "classificazione"
                  ? t("incidents.detail_tabs.classification")
                  : tab === "metodo"
                    ? t("incidents.detail_tabs.method")
                    : t("incidents.detail_tabs.timeline")}
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
                onChange({
                  ...selected,
                  incident_category: r.category ?? selected.incident_category,
                  severity: r.severity ?? selected.severity,
                });
              }}
              onIgnore={() => {}}
            />
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-gray-600">{t("incidents.management.enisa_label")}</label>
                <select
                  className="w-full border rounded px-3 py-2 text-sm"
                  value={selected.incident_category ?? ""}
                  onChange={e => onChange({ ...selected, incident_category: e.target.value, incident_subcategory: "" })}
                >
                  <option value="">{t("incidents.management.select_placeholder")}</option>
                  {enisaCategories.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-600">{t("incidents.management.enisa_detail_label")}</label>
                <select
                  className="w-full border rounded px-3 py-2 text-sm"
                  value={selected.incident_subcategory ?? ""}
                  onChange={e => onChange({ ...selected, incident_subcategory: e.target.value })}
                >
                  <option value="">{t("incidents.management.select_placeholder")}</option>
                  {(enisaSubcategories[selected.incident_category ?? ""] ?? []).map(s => (
                    <option key={s.value} value={s.value}>{s.label}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <input className="border rounded px-3 py-2 text-sm" placeholder={t("incidents.management.affected_users_ph")} value={selected.affected_users_count ?? ""} onChange={e => onChange({ ...selected, affected_users_count: e.target.value ? Number(e.target.value) : null })} />
              <input className="border rounded px-3 py-2 text-sm" placeholder={t("incidents.management.disruption_hours_ph")} value={selected.service_disruption_hours ?? ""} onChange={e => onChange({ ...selected, service_disruption_hours: e.target.value || null })} />
              <input className="border rounded px-3 py-2 text-sm" placeholder={t("incidents.management.financial_impact_ph")} value={selected.financial_impact_eur ?? ""} onChange={e => onChange({ ...selected, financial_impact_eur: e.target.value || null })} />
            </div>
            <div className="flex gap-4 text-sm">
              <label><input type="checkbox" checked={!!selected.personal_data_involved} onChange={e => onChange({ ...selected, personal_data_involved: e.target.checked })} /> {t("incidents.management.personal_data")}</label>
              <label><input type="checkbox" checked={!!selected.cross_border_impact} onChange={e => onChange({ ...selected, cross_border_impact: e.target.checked })} /> {t("incidents.management.cross_border")}</label>
              <label><input type="checkbox" checked={!!selected.critical_infrastructure_impact} onChange={e => onChange({ ...selected, critical_infrastructure_impact: e.target.checked })} /> {t("incidents.management.critical_infra")}</label>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => updateMutation.mutate({ id: selected.id, payload: selected })}
                disabled={updateMutation.isPending}
                className="px-3 py-2 text-xs bg-primary-600 text-white rounded disabled:opacity-50"
              >
                {updateMutation.isPending ? t("incidents.management.saving") : t("incidents.management.save_btn")}
              </button>
              {updateMutation.isSuccess && <span className="text-xs text-green-600">{t("incidents.management.saved")}</span>}
              {updateMutation.isError && <span className="text-xs text-red-500">{t("incidents.management.save_error")}</span>}
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
                        onChange({ ...selected, is_recurrent: v });
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
                disabled={!classificationMethod}
                className="px-3 py-1.5 text-xs border rounded disabled:opacity-50"
              >
                {t("incidents.nis2_classification.method_tab.export_button")}
              </button>
            </div>
            <div className="rounded border bg-blue-50 border-blue-100 p-3">
              <div className="text-sm font-medium text-blue-900">
                {t("incidents.nis2_classification.method_tab.page_title")}
              </div>
              {classificationMethod?.nis2_method.decision_model && (
                <div className="text-[11px] text-blue-800 mt-1 font-mono">
                  {t("incidents.nis2_classification.method_tab.decision_model_label")}:{" "}
                  {classificationMethod.nis2_method.decision_model}
                </div>
              )}
              <div className="text-xs text-blue-900 mt-1">
                {classificationMethod?.nis2_method.rule ?? t("incidents.nis2_classification.method_tab.rule_fallback")}
              </div>
              {classificationMethod?.nis2_method.criteria_disclaimer && (
                <p className="text-[11px] text-blue-900/90 mt-2 leading-relaxed">
                  {t("incidents.nis2_classification.method_tab.criteria_disclaimer")}
                </p>
              )}
            </div>

            {classificationMethod?.nis2_method.thresholds && (
              <div className="rounded border p-3 bg-gray-50/80">
                <div className="text-sm font-medium mb-2">
                  {t("incidents.nis2_classification.method_tab.config_title")}
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1 text-xs text-gray-800">
                  <div>
                    {t("incidents.nis2_classification.method_tab.config_users")}:{" "}
                    <strong>{classificationMethod.nis2_method.thresholds.affected_users_count}</strong>
                  </div>
                  <div>
                    {t("incidents.nis2_classification.method_tab.config_hours")}:{" "}
                    <strong>{classificationMethod.nis2_method.thresholds.service_disruption_hours}</strong>
                  </div>
                  <div>
                    {t("incidents.nis2_classification.method_tab.config_financial")}:{" "}
                    <strong>{classificationMethod.nis2_method.thresholds.financial_impact_eur}</strong>
                  </div>
                  <div>
                    {t("incidents.nis2_classification.method_tab.config_mult_m")}:{" "}
                    <strong>{classificationMethod.nis2_method.thresholds.multiplier_medium ?? "—"}</strong>
                  </div>
                  <div>
                    {t("incidents.nis2_classification.method_tab.config_mult_h")}:{" "}
                    <strong>{classificationMethod.nis2_method.thresholds.multiplier_high ?? "—"}</strong>
                  </div>
                  <div>
                    {t("incidents.nis2_classification.method_tab.config_ptnr")}:{" "}
                    <strong>{classificationMethod.nis2_method.thresholds.ptnr_trigger_csirt ?? "—"}</strong>
                  </div>
                  <div>
                    {t("incidents.nis2_classification.method_tab.config_rec_window")}:{" "}
                    <strong>{classificationMethod.nis2_method.thresholds.recurrence_window_days ?? "—"}</strong>
                  </div>
                  <div>
                    {t("incidents.nis2_classification.method_tab.config_rec_bonus")}:{" "}
                    <strong>{classificationMethod.nis2_method.thresholds.recurrence_score_bonus ?? "—"}</strong>
                  </div>
                </div>
              </div>
            )}

            {breakdownError ? (
              <div className="text-xs text-red-700 rounded border border-red-200 bg-red-50 p-2">
                {t("incidents.nis2_classification.method_tab.engine_unavailable")}
              </div>
            ) : serverBreakdown?.decision ? (
              <div className="rounded border border-emerald-200 bg-emerald-50 p-3">
                <div className="text-sm font-medium text-emerald-900">
                  {t("incidents.nis2_classification.method_tab.engine_title")}
                </div>
                <div className="text-base font-semibold text-emerald-950 mt-1">
                  {serverBreakdown.decision.is_significant
                    ? t("incidents.nis2_classification.decision.significant_title")
                    : t("incidents.nis2_classification.decision.not_significant_title")}
                </div>
                <div className="text-xs text-emerald-900 mt-1">
                  {serverBreakdown.pta_ptnr != null && (
                    <>PTA {serverBreakdown.pta_ptnr.PTA} · PTNR {serverBreakdown.pta_ptnr.PTNR} · </>
                  )}
                  {t("incidents.nis2_classification.config.ptnr_threshold")}{" "}
                  {String(
                    (serverBreakdown.config_used?.ptnr_threshold as number | undefined) ??
                      classificationMethod?.nis2_method.thresholds.ptnr_trigger_csirt ??
                      "—"
                  )}
                </div>
                <p className="text-xs text-gray-800 mt-2 leading-relaxed">{serverBreakdown.decision.rationale}</p>
              </div>
            ) : (
              <div className="text-xs text-gray-500 rounded border border-dashed p-2">
                {breakdownFetching
                  ? t("incidents.nis2_classification.method_tab.engine_loading")
                  : t("incidents.nis2_classification.method_tab.engine_unavailable")}
              </div>
            )}

            <div className="rounded border p-3">
              <div className="text-sm font-medium mb-1">
                {t("incidents.nis2_classification.method_tab.scores_snapshot_title")}
              </div>
              <p className="text-[11px] text-gray-500 mb-2">
                {t("incidents.nis2_classification.method_tab.scores_snapshot_note")}
              </p>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>PTA NIS2: <strong>{classificationMethod?.scores?.pta_nis2 ?? "—"}</strong></div>
                <div>PTNR NIS2: <strong>{classificationMethod?.scores?.ptnr_nis2 ?? "—"}</strong></div>
                <div>PT GDPR: <strong>{classificationMethod?.scores?.pt_gdpr ?? "—"}</strong></div>
                <div>{t("incidents.method_extra.acn_category")}: <strong>{classificationMethod?.scores?.acn_is_category || "—"}</strong></div>
                <div>{t("incidents.method_extra.csirt_required")}: <strong>{classificationMethod?.scores?.requires_csirt_notification ? t("common.yes") : t("common.no")}</strong></div>
                <div>{t("incidents.method_extra.gdpr_required")}: <strong>{classificationMethod?.scores?.requires_gdpr_notification ? t("common.yes") : t("common.no")}</strong></div>
              </div>
            </div>

            <div className="rounded border p-3">
              <div className="text-sm font-medium mb-1">{t("incidents.nis2_classification.method_tab.raw_inputs_title")}</div>
              <p className="text-[11px] text-gray-600 mb-2">{t("incidents.nis2_classification.method_tab.raw_inputs_note")}</p>
              <div className="overflow-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-left text-gray-500 border-b">
                      <th className="py-1 pr-2">{t("incidents.nis2_classification.method_tab.col_reaches_base")}</th>
                      <th className="py-1 pr-2">{t("incidents.nis2_classification.method_tab.col_criterion")}</th>
                      <th className="py-1 pr-2">{t("incidents.nis2_classification.method_tab.col_value")}</th>
                      <th className="py-1 pr-2">{t("incidents.nis2_classification.method_tab.col_threshold")}</th>
                      <th className="py-1 pr-2">{t("incidents.nis2_classification.method_tab.col_source")}</th>
                    </tr>
                  </thead>
                  <tbody>
                {(classificationMethod?.nis2_method.criteria ?? []).map((criterion) => {
                  const satisfied = isCriterionSatisfied(criterion, selected);
                  const incidentRaw = (selected as unknown as Record<string, unknown>)[criterion.key];
                  const incidentDisplay =
                    criterion.type === "boolean"
                      ? (incidentRaw ? t("common.yes") : t("common.no"))
                      : String(incidentRaw ?? 0);
                  const sourceLabel = criterion.type === "threshold"
                    ? t("incidents.nis2_classification.method_tab.source_threshold")
                    : t("incidents.nis2_classification.method_tab.source_flag");
                  const reachCell =
                    criterion.type === "boolean"
                      ? t("incidents.nis2_classification.method_tab.boolean_na")
                      : satisfied
                        ? t("common.yes")
                        : t("common.no");
                  return (
                    <tr key={`eval-${criterion.key}`} className="border-b last:border-b-0">
                      <td className="py-1 pr-2 text-gray-800">{reachCell}</td>
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
              {selected.significance_override !== null && selected.significance_override !== undefined && (
                <div className="mt-2 text-xs text-amber-700">
                  {t("incidents.nis2_classification.method_tab.override_active")}
                </div>
              )}
            </div>

            <div className="rounded border p-3">
              <div className="text-sm font-medium mb-1">{t("incidents.nis2_classification.method_tab.criteria_list_title")}</div>
              <p className="text-[11px] text-gray-500 mb-2">{t("incidents.nis2_classification.method_tab.criteria_list_note")}</p>
              <p className="text-[11px] text-gray-600 mb-2">{t("incidents.nis2_classification.config.multiplier_note")}</p>
              <div className="space-y-1">
                {(classificationMethod?.nis2_method.criteria ?? []).map((criterion) => (
                  <div key={criterion.key} className="text-xs text-gray-700">
                    {criterion.type === "threshold"
                      ? `- ${criterion.label}: ${t("incidents.method_extra.criterion_value_line")} ${criterion.operator} ${criterion.threshold}`
                      : `- ${criterion.label}: ${t("incidents.method_extra.criterion_boolean_line")}`}
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded border p-3">
              <div className="text-sm font-medium mb-2">{t("incidents.method_extra.taxonomy_title")}</div>
              <div className="space-y-2">
                {(classificationMethod?.taxonomy.categories ?? []).map((category) => (
                  <div key={category.code} className="rounded border bg-gray-50 p-2">
                    <div className="text-xs font-semibold">
                      {category.code} — {category.label}
                    </div>
                    <div className="text-xs text-gray-600">{category.description}</div>
                    <div className="mt-1 text-xs text-gray-700">
                      {t("incidents.method_extra.subcategories_label")}:{" "}
                      {(classificationMethod?.taxonomy.subcategories[category.code] ?? [])
                        .map((sub) => sub.label)
                        .join(", ") || t("incidents.method_extra.none_defined")}
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
                <div className="text-xs text-gray-500">{t("incidents.timeline_tab.reg_deadline")}: {step.deadline ? new Date(step.deadline).toLocaleString(dateLocale) : "—"}</div>
                <div className="text-xs">{t("incidents.timeline_tab.step_status")}: <strong>{step.status}</strong></div>
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
                    {t("incidents.timeline_tab.generate_doc")}
                  </button>
                  <button onClick={() => setSentType(step.step)} className="text-xs border rounded px-2 py-1">{t("incidents.timeline_tab.prepare_send")}</button>
                </div>
              </div>
            ))}
            <div className="border rounded p-3 space-y-2">
              <div className="text-sm font-medium">{t("incidents.timeline_tab.register_title")}</div>
              <select value={sentType} onChange={e => setSentType(e.target.value)} className="w-full border rounded px-2 py-1.5 text-sm">
                <option value="early_warning">{t("incidents.timeline_tab.type_early")}</option>
                <option value="formal_notification">{t("incidents.timeline_tab.type_formal")}</option>
                <option value="final_report">{t("incidents.timeline_tab.type_final")}</option>
                <option value="update">{t("incidents.timeline_tab.type_update")}</option>
              </select>
              <input className="w-full border rounded px-2 py-1.5 text-sm" placeholder={t("incidents.timeline_tab.protocol_ph")} value={protocolRef} onChange={e => setProtocolRef(e.target.value)} />
              <textarea className="w-full border rounded px-2 py-1.5 text-sm" rows={2} placeholder={t("incidents.timeline_tab.response_ph")} value={authorityResponse} onChange={e => setAuthorityResponse(e.target.value)} />
              <button onClick={() => markSentMutation.mutate(selected.id)} className="px-3 py-2 text-xs bg-primary-600 text-white rounded">{t("incidents.timeline_tab.confirm_send")}</button>
            </div>
            <div className="border rounded p-3">
              <div className="text-sm font-medium mb-2">{t("incidents.timeline_tab.registry_title")}</div>
              <table className="w-full text-xs">
                <thead><tr><th className="text-left">{t("incidents.timeline_tab.col_type")}</th><th className="text-left">{t("incidents.timeline_tab.col_csirt")}</th><th className="text-left">{t("incidents.timeline_tab.col_sent_at")}</th><th className="text-left">{t("incidents.timeline_tab.col_protocol")}</th></tr></thead>
                <tbody>
                  {(notifications as NIS2Notification[] | undefined)?.map(n => (
                    <tr key={n.id}><td>{n.notification_type}</td><td>{n.csirt_name}</td><td>{n.sent_at ? new Date(n.sent_at).toLocaleString(dateLocale) : "—"}</td><td>{n.protocol_ref || "—"}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="border rounded p-3">
              <div className="text-sm font-medium mb-2">{t("incidents.timeline_tab.rca_title")}</div>
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
                  <div className="text-sm font-semibold text-indigo-900">{t("incidents.timeline_tab.rca_preview_title")}</div>
                  <div>
                    <div className="font-medium">{t("incidents.timeline_tab.rca_summary")}</div>
                    <div>{String(rcaDraftData.summary ?? "—")}</div>
                  </div>
                  <div>
                    <div className="font-medium">{t("incidents.timeline_tab.rca_root_cause")}</div>
                    <div>{String(rcaDraftData.root_cause ?? "—")}</div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <div className="font-medium">{t("incidents.timeline_tab.rca_immediate")}</div>
                      <div className="whitespace-pre-wrap">{listText(rcaDraftData.immediate_actions)}</div>
                    </div>
                    <div>
                      <div className="font-medium">{t("incidents.timeline_tab.rca_preventive")}</div>
                      <div className="whitespace-pre-wrap">{listText(rcaDraftData.preventive_actions)}</div>
                    </div>
                  </div>
                  <div>
                    <div className="font-medium">{t("incidents.timeline_tab.rca_lessons")}</div>
                    <div>{String(rcaDraftData.lessons_learned ?? "—")}</div>
                  </div>
                </div>
              )}
              <textarea
                className="mt-3 w-full border rounded px-3 py-2 text-xs min-h-40"
                value={rcaDraftText}
                onChange={(e) => setRcaDraftText(e.target.value)}
                placeholder={t("incidents.timeline_tab.rca_placeholder")}
                disabled={!!rca?.approved_at}
              />
              <div className="mt-2 flex items-center gap-2 flex-wrap">
                {rca?.approved_at ? (
                  <span className="px-2 py-1 text-xs rounded bg-green-100 text-green-800">
                    {t("incidents.timeline_tab.rca_approved_on", {
                      date: new Date(rca.approved_at).toLocaleString(dateLocale),
                    })}
                  </span>
                ) : (
                  <>
                    <button
                      onClick={() => saveRcaMutation.mutate()}
                      disabled={!rcaDraftText.trim() || saveRcaMutation.isPending}
                      className="px-3 py-2 text-xs bg-primary-600 text-white rounded disabled:opacity-50"
                    >
                      {saveRcaMutation.isPending
                        ? t("incidents.timeline_tab.rca_saving")
                        : t("incidents.timeline_tab.rca_save")}
                    </button>
                    <button
                      onClick={() => approveRcaMutation.mutate()}
                      disabled={!rca || approveRcaMutation.isPending}
                      title={!rca ? t("incidents.timeline_tab.rca_save_first") : undefined}
                      className="px-3 py-2 text-xs bg-green-600 text-white rounded disabled:opacity-50"
                    >
                      {approveRcaMutation.isPending
                        ? t("incidents.timeline_tab.rca_approving")
                        : t("incidents.timeline_tab.rca_approve")}
                    </button>
                    <span className="text-xs text-gray-500">{t("incidents.timeline_tab.rca_gate_hint")}</span>
                  </>
                )}
                {saveRcaMutation.isError && (
                  <span className="text-xs text-red-600">{t("incidents.timeline_tab.rca_save_error")}</span>
                )}
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
