import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  kpiApi,
  type KpiAggregation,
  type KpiDirection,
  type KpiSource,
} from "../../../api/endpoints/kpi";
import { checklistsApi } from "../../../api/endpoints/checklists";
import { plantsApi } from "../../../api/endpoints/plants";

interface FormState {
  kpi_code: string;
  name: string;
  description: string;
  unit: string;
  source: KpiSource;
  checklist_template: string;
  checklist_item_filter: string;
  aggregation: KpiAggregation;
  plant: string;
  threshold_warning: string;
  threshold_critical: string;
  threshold_direction: KpiDirection;
  is_active: boolean;
  notify_on_warning: boolean;
  notify_on_critical: boolean;
}

const EMPTY: FormState = {
  kpi_code: "",
  name: "",
  description: "",
  unit: "",
  source: "checklist",
  checklist_template: "",
  checklist_item_filter: "",
  aggregation: "success_rate",
  plant: "",
  threshold_warning: "",
  threshold_critical: "",
  threshold_direction: "above",
  is_active: true,
  notify_on_warning: true,
  notify_on_critical: true,
};

const AGGREGATIONS: KpiAggregation[] = [
  "success_rate",
  "avg_value",
  "last_value",
  "count_ok",
  "count_fail",
];

export function KpiDefinitionForm() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { id } = useParams();
  const isEdit = Boolean(id);
  const [form, setForm] = useState<FormState>(EMPTY);
  const [codeError, setCodeError] = useState<string | null>(null);
  const [loadedId, setLoadedId] = useState<string | null>(null);

  const { data: plants } = useQuery({
    queryKey: ["plants"],
    queryFn: () => plantsApi.list(),
    retry: false,
  });
  const { data: templates } = useQuery({
    queryKey: ["checklist-templates", "", ""],
    queryFn: () => checklistsApi.listTemplates(),
    retry: false,
  });
  const { data: existing } = useQuery({
    queryKey: ["kpi-definition", id],
    queryFn: () => kpiApi.getKpiDefinition(id!),
    enabled: isEdit,
    retry: false,
  });

  // Popola il form dai dati caricati in modifica, una sola volta per id (pattern
  // React di adeguamento dello stato durante il render, senza effect): quando
  // `existing` arriva per l'id corrente lo sincronizziamo e marchiamo l'id.
  if (existing && loadedId !== id) {
    setLoadedId(id ?? null);
    setForm({
      kpi_code: existing.kpi_code,
      name: existing.name,
      description: existing.description ?? "",
      unit: existing.unit ?? "",
      source: existing.source,
      checklist_template: existing.checklist_template ?? "",
      checklist_item_filter: existing.checklist_item_filter ?? "",
      aggregation: existing.aggregation,
      plant: existing.plant ?? "",
      threshold_warning: existing.threshold_warning?.toString() ?? "",
      threshold_critical: existing.threshold_critical?.toString() ?? "",
      threshold_direction: existing.threshold_direction,
      is_active: existing.is_active,
      notify_on_warning: existing.notify_on_warning,
      notify_on_critical: existing.notify_on_critical,
    });
  }

  const mutation = useMutation({
    mutationFn: () => {
      const payload = {
        kpi_code: form.kpi_code.trim(),
        name: form.name.trim(),
        description: form.description,
        unit: form.unit,
        source: form.source,
        checklist_template: form.source === "checklist" && form.checklist_template ? form.checklist_template : null,
        checklist_item_filter: form.source === "checklist" ? form.checklist_item_filter : "",
        aggregation: form.aggregation,
        plant: form.plant || null,
        threshold_warning: form.threshold_warning === "" ? null : Number(form.threshold_warning),
        threshold_critical: form.threshold_critical === "" ? null : Number(form.threshold_critical),
        threshold_direction: form.threshold_direction,
        is_active: form.is_active,
        notify_on_warning: form.notify_on_warning,
        notify_on_critical: form.notify_on_critical,
      };
      return isEdit
        ? kpiApi.updateKpiDefinition(id!, payload)
        : kpiApi.createKpiDefinition(payload);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["kpi-definitions"] });
      navigate("/kpi/definitions");
    },
    onError: (err: any) => {
      const codeErr = err?.response?.data?.kpi_code;
      setCodeError(Array.isArray(codeErr) ? codeErr[0] : codeErr ?? null);
    },
  });

  function set<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  // Preview formula in italiano
  function formulaPreview(): string {
    const dir = form.threshold_direction === "above" ? t("kpi.form.dir_above_short") : t("kpi.form.dir_below_short");
    const aggLabel = t(`kpi.aggregation.${form.aggregation}`);
    if (form.source === "checklist") {
      const tpl = (templates?.results ?? []).find((x) => x.id === form.checklist_template);
      const tplName = tpl?.name ?? t("kpi.form.template_placeholder");
      const filter = form.checklist_item_filter
        ? t("kpi.form.preview_filter", { filter: form.checklist_item_filter })
        : t("kpi.form.preview_all_items");
      return t("kpi.form.preview_checklist", { agg: aggLabel, template: tplName, filter, dir });
    }
    if (form.source === "internal") {
      return t("kpi.form.preview_internal", { dir });
    }
    return t("kpi.form.preview_api", { agg: aggLabel, dir });
  }

  const canSave = form.kpi_code.trim() && form.name.trim();

  return (
    <div className="max-w-2xl">
      <button
        onClick={() => navigate("/kpi/definitions")}
        className="text-sm text-gray-500 hover:text-gray-700 mb-3"
      >
        ← {t("kpi.definitions.title")}
      </button>
      <h2 className="text-xl font-semibold text-gray-900 mb-4">
        {isEdit ? t("kpi.form.edit") : t("kpi.form.new")}
      </h2>

      <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("kpi.form.kpi_code")}</label>
            <input
              value={form.kpi_code}
              disabled={isEdit}
              onChange={(e) => { set("kpi_code", e.target.value); setCodeError(null); }}
              placeholder="backup_success_rate"
              className="w-full border rounded px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary-400 disabled:bg-gray-100"
            />
            {codeError && <p className="text-xs text-red-600 mt-1">{codeError}</p>}
            <p className="text-[11px] text-gray-400 mt-1">{t("kpi.form.kpi_code_hint")}</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("kpi.form.unit")}</label>
            <input
              value={form.unit}
              onChange={(e) => set("unit", e.target.value)}
              placeholder="%, ore, n°"
              className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{t("kpi.form.name")}</label>
          <input
            value={form.name}
            onChange={(e) => set("name", e.target.value)}
            className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{t("kpi.form.description")}</label>
          <textarea
            value={form.description}
            onChange={(e) => set("description", e.target.value)}
            rows={2}
            className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("kpi.form.source")}</label>
            <select
              value={form.source}
              onChange={(e) => set("source", e.target.value as KpiSource)}
              className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
            >
              {(["checklist", "internal", "api", "manual"] as KpiSource[]).map((s) => (
                <option key={s} value={s}>{t(`kpi.source.${s}`)}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("kpi.form.plant")}</label>
            <select
              value={form.plant}
              onChange={(e) => set("plant", e.target.value)}
              className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
            >
              <option value="">{t("kpi.form.plant_global")}</option>
              {(plants ?? []).map((p) => (
                <option key={p.id} value={p.id}>{p.code} — {p.name}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Campi condizionali per source=checklist */}
        {form.source === "checklist" && (
          <>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{t("kpi.form.template")}</label>
                <select
                  value={form.checklist_template}
                  onChange={(e) => set("checklist_template", e.target.value)}
                  className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
                >
                  <option value="">{t("common.select")}</option>
                  {(templates?.results ?? []).map((tpl) => (
                    <option key={tpl.id} value={tpl.id}>{tpl.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{t("kpi.form.aggregation")}</label>
                <select
                  value={form.aggregation}
                  onChange={(e) => set("aggregation", e.target.value as KpiAggregation)}
                  className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
                >
                  {AGGREGATIONS.map((a) => (
                    <option key={a} value={a}>{t(`kpi.aggregation.${a}`)}</option>
                  ))}
                </select>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("kpi.form.item_filter")}</label>
              <input
                value={form.checklist_item_filter}
                onChange={(e) => set("checklist_item_filter", e.target.value)}
                placeholder={t("kpi.form.item_filter_placeholder")}
                className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
              />
            </div>
          </>
        )}

        {/* Soglie */}
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("kpi.form.threshold_warning")}</label>
            <input
              type="number"
              step="any"
              value={form.threshold_warning}
              onChange={(e) => set("threshold_warning", e.target.value)}
              className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("kpi.form.threshold_critical")}</label>
            <input
              type="number"
              step="any"
              value={form.threshold_critical}
              onChange={(e) => set("threshold_critical", e.target.value)}
              className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("kpi.form.direction")}</label>
            <select
              value={form.threshold_direction}
              onChange={(e) => set("threshold_direction", e.target.value as KpiDirection)}
              className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
            >
              <option value="above">{t("kpi.form.dir_above")}</option>
              <option value="below">{t("kpi.form.dir_below")}</option>
            </select>
          </div>
        </div>

        {/* Preview formula */}
        <div className="bg-primary-50 border border-primary-100 rounded p-3">
          <p className="text-xs font-medium text-primary-800 mb-1">{t("kpi.form.preview_title")}</p>
          <p className="text-sm text-primary-900">{formulaPreview()}</p>
        </div>

        {/* Flags */}
        <div className="flex flex-wrap gap-4">
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input type="checkbox" checked={form.is_active} onChange={(e) => set("is_active", e.target.checked)}
              className="rounded border-gray-300 text-primary-600 focus:ring-primary-400" />
            {t("kpi.form.is_active")}
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input type="checkbox" checked={form.notify_on_warning} onChange={(e) => set("notify_on_warning", e.target.checked)}
              className="rounded border-gray-300 text-primary-600 focus:ring-primary-400" />
            {t("kpi.form.notify_warning")}
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input type="checkbox" checked={form.notify_on_critical} onChange={(e) => set("notify_on_critical", e.target.checked)}
              className="rounded border-gray-300 text-primary-600 focus:ring-primary-400" />
            {t("kpi.form.notify_critical")}
          </label>
        </div>

        {mutation.isError && !codeError && (
          <p className="text-sm text-red-600">{t("common.save_error")}</p>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <button
            onClick={() => navigate("/kpi/definitions")}
            className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50"
          >
            {t("actions.cancel")}
          </button>
          <button
            onClick={() => mutation.mutate()}
            disabled={!canSave || mutation.isPending}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? t("common.saving") : t("actions.save")}
          </button>
        </div>
      </div>
    </div>
  );
}
