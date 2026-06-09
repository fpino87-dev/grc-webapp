import { useMemo, useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  kpiApi,
  type KpiImportOverride,
  type KpiSuggestion,
} from "../../../api/endpoints/kpi";
import { plantsApi } from "../../../api/endpoints/plants";
import { checklistsApi } from "../../../api/endpoints/checklists";
import i18n from "../../../i18n";

interface Props {
  initialPlantId?: string;
  onClose: () => void;
  onImported: () => void;
}

function fwLabel(code: string): string {
  return code.replace(/_/g, " ");
}

export function KpiSuggestWizard({ initialPlantId, onClose, onImported }: Props) {
  const { t } = useTranslation();
  const lang = i18n.language?.slice(0, 2) || "it";

  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [plantId, setPlantId] = useState(initialPlantId ?? "");
  const [suggestions, setSuggestions] = useState<KpiSuggestion[]>([]);
  const [frameworks, setFrameworks] = useState<string[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [overrides, setOverrides] = useState<Record<string, KpiImportOverride>>({});
  const [activeCategory, setActiveCategory] = useState<string>("");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

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

  const analyzeMutation = useMutation({
    mutationFn: () => kpiApi.getKpiSuggestions(plantId || undefined, lang),
    onSuccess: (data) => {
      setSuggestions(data.suggestions);
      setFrameworks(data.plant_frameworks);
      // Default: seleziona i non già configurati; pre-popola gli override.
      const sel = new Set<string>();
      const ov: Record<string, KpiImportOverride> = {};
      for (const s of data.suggestions) {
        if (!s.already_configured) sel.add(s.kpi_code);
        ov[s.kpi_code] = {
          threshold_warning: s.threshold_warning,
          threshold_critical: s.threshold_critical,
          checklist_template: s.suggested_checklist_template?.id ?? null,
          // Se il KPI checklist non ha un template collegabile ma ha uno seed,
          // di default proponiamo di crearlo dal consiglio.
          create_template: s.can_create_template,
        };
      }
      setSelected(sel);
      setOverrides(ov);
      const cats = [...new Set(data.suggestions.map((s) => s.category))];
      setActiveCategory(cats[0] ?? "");
      setStep(2);
    },
  });

  const importMutation = useMutation({
    mutationFn: () => {
      const codes = [...selected];
      const ov: Record<string, KpiImportOverride> = {};
      for (const code of codes) ov[code] = overrides[code] ?? {};
      return kpiApi.importKpiSuggestions(plantId || null, codes, ov);
    },
  });

  const categories = useMemo(
    () => [...new Set(suggestions.map((s) => s.category))],
    [suggestions]
  );
  const configuredCount = suggestions.filter((s) => s.already_configured).length;
  const catSuggestions = suggestions.filter((s) => s.category === activeCategory);
  const selectedList = suggestions.filter((s) => selected.has(s.kpi_code) && !s.already_configured);

  function toggle(code: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return next;
    });
  }
  function toggleExpand(code: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return next;
    });
  }
  function setOverride(code: string, patch: Partial<KpiImportOverride>) {
    setOverrides((prev) => ({ ...prev, [code]: { ...prev[code], ...patch } }));
  }

  function handleImport() {
    importMutation.mutate(undefined, {
      onSuccess: () => {
        setStep(3);
      },
    });
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">{t("kpi.suggest.title")}</h3>
            <div className="flex items-center gap-2 mt-1 text-xs text-gray-400">
              {[1, 2, 3].map((n) => (
                <span key={n} className={`px-2 py-0.5 rounded ${step === n ? "bg-primary-100 text-primary-700 font-medium" : "bg-gray-100"}`}>
                  {n}. {t(`kpi.suggest.step${n}.tab`)}
                </span>
              ))}
            </div>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-700 text-xl leading-none">✕</button>
        </div>

        {/* ── STEP 1 ── */}
        {step === 1 && (
          <div className="p-6 space-y-4 overflow-y-auto">
            <p className="text-sm text-gray-600">{t("kpi.suggest.step1.intro")}</p>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("kpi.suggest.step1.plant")}</label>
              <select
                value={plantId}
                onChange={(e) => setPlantId(e.target.value)}
                className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
              >
                <option value="">{t("kpi.suggest.step1.plant_global")}</option>
                {(plants ?? []).map((p) => (
                  <option key={p.id} value={p.id}>{p.code} — {p.name}</option>
                ))}
              </select>
              <p className="text-[11px] text-gray-400 mt-1">{t("kpi.suggest.step1.plant_hint")}</p>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">
                {t("actions.cancel")}
              </button>
              <button
                onClick={() => analyzeMutation.mutate()}
                disabled={analyzeMutation.isPending}
                className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
              >
                {analyzeMutation.isPending ? t("kpi.suggest.step1.analyzing") : t("kpi.suggest.step1.analyze")}
              </button>
            </div>
          </div>
        )}

        {/* ── STEP 2 ── */}
        {step === 2 && (
          <>
            <div className="px-6 py-3 border-b border-gray-100 bg-gray-50 text-sm text-gray-600 flex flex-wrap gap-x-4 gap-y-1">
              <span>{t("kpi.suggest.step2.summary", { total: suggestions.length, configured: configuredCount, selected: selected.size })}</span>
              {frameworks.length > 0 && (
                <span className="text-gray-400">
                  {t("kpi.suggest.step2.frameworks")}: {frameworks.map(fwLabel).join(", ")}
                </span>
              )}
            </div>
            <div className="flex flex-1 min-h-0">
              {/* categorie */}
              <div className="w-44 shrink-0 border-r border-gray-100 overflow-y-auto py-2">
                {categories.map((cat) => {
                  const count = suggestions.filter((s) => s.category === cat).length;
                  return (
                    <button
                      key={cat}
                      onClick={() => setActiveCategory(cat)}
                      className={`w-full text-left px-4 py-2 text-sm transition-colors ${activeCategory === cat ? "bg-primary-50 text-primary-700 font-medium border-l-2 border-primary-500" : "text-gray-600 hover:bg-gray-50"}`}
                    >
                      {t(`kpi.suggest.categories.${cat}`)} <span className="text-gray-400">({count})</span>
                    </button>
                  );
                })}
              </div>
              {/* lista KPI categoria */}
              <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {catSuggestions.map((s) => {
                  const isSel = selected.has(s.kpi_code) || s.already_configured;
                  const ov = overrides[s.kpi_code] ?? {};
                  return (
                    <div key={s.kpi_code} className={`border rounded-lg p-3 ${s.already_configured ? "bg-gray-50 border-gray-200" : "border-gray-200"}`}>
                      <div className="flex items-start gap-3">
                        <input
                          type="checkbox"
                          checked={isSel}
                          disabled={s.already_configured}
                          onChange={() => toggle(s.kpi_code)}
                          className="mt-1 h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-400 disabled:opacity-60"
                        />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center flex-wrap gap-2">
                            <span className="text-sm font-medium text-gray-800">{s.name}</span>
                            {s.already_configured && (
                              <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-gray-200 text-gray-600">
                                {t("kpi.suggest.already_configured")}
                              </span>
                            )}
                            {s.frameworks.map((fw) => (
                              <span key={fw} className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-blue-50 text-blue-700">
                                {fwLabel(fw)}
                              </span>
                            ))}
                          </div>
                          <p className="text-xs text-gray-500 mt-0.5">{s.description}</p>

                          <div className="flex items-center gap-3 mt-1 text-xs text-gray-600">
                            {s.threshold_warning != null && <span>🟡 {s.threshold_warning}{s.unit}</span>}
                            {s.threshold_critical != null && <span>🔴 {s.threshold_critical}{s.unit}</span>}
                            <span className="text-gray-400">
                              {s.threshold_direction === "above" ? t("kpi.form.dir_above_short") : t("kpi.form.dir_below_short")}
                            </span>
                          </div>

                          {s.suggested_checklist_template && (
                            <div className="mt-2 text-xs bg-sky-50 border border-sky-100 text-sky-800 rounded px-2 py-1">
                              {t("kpi.suggest.linkable_to")}: <strong>{s.suggested_checklist_template.name}</strong>
                            </div>
                          )}

                          <button onClick={() => toggleExpand(s.kpi_code)} className="mt-2 text-xs text-primary-600 hover:text-primary-800 flex items-center gap-1">
                            <span>{expanded.has(s.kpi_code) ? "▴" : "▾"}</span> {t("kpi.suggest.rationale")}
                          </button>
                          {expanded.has(s.kpi_code) && (
                            <p className="mt-1 text-xs text-gray-500 italic border-l-2 border-gray-200 pl-2">{s.rationale}</p>
                          )}

                          {/* override inline (solo se selezionato e non già configurato) */}
                          {selected.has(s.kpi_code) && !s.already_configured && (
                            <div className="mt-2 space-y-2">
                              <div className="grid grid-cols-3 gap-2">
                                <label className="text-[11px] text-gray-500">
                                  {t("kpi.form.threshold_warning")}
                                  <input
                                    type="number" step="any"
                                    value={ov.threshold_warning ?? ""}
                                    onChange={(e) => setOverride(s.kpi_code, { threshold_warning: e.target.value === "" ? null : Number(e.target.value) })}
                                    className="w-full border rounded px-2 py-1 text-xs mt-0.5 focus:outline-none focus:ring-1 focus:ring-primary-400"
                                  />
                                </label>
                                <label className="text-[11px] text-gray-500">
                                  {t("kpi.form.threshold_critical")}
                                  <input
                                    type="number" step="any"
                                    value={ov.threshold_critical ?? ""}
                                    onChange={(e) => setOverride(s.kpi_code, { threshold_critical: e.target.value === "" ? null : Number(e.target.value) })}
                                    className="w-full border rounded px-2 py-1 text-xs mt-0.5 focus:outline-none focus:ring-1 focus:ring-primary-400"
                                  />
                                </label>
                                {s.source === "checklist" && !ov.create_template && (
                                  <label className="text-[11px] text-gray-500">
                                    {t("kpi.form.template")}
                                    <select
                                      value={ov.checklist_template ?? ""}
                                      onChange={(e) => setOverride(s.kpi_code, { checklist_template: e.target.value || null })}
                                      className="w-full border rounded px-2 py-1 text-xs mt-0.5 focus:outline-none focus:ring-1 focus:ring-primary-400"
                                    >
                                      <option value="">—</option>
                                      {(templates?.results ?? []).map((tpl) => (
                                        <option key={tpl.id} value={tpl.id}>{tpl.name}</option>
                                      ))}
                                    </select>
                                  </label>
                                )}
                              </div>
                              {/* crea template dallo seed (solo se non esiste già un collegamento) */}
                              {s.source === "checklist" && s.can_create_template && (
                                <label className="flex items-center gap-2 text-xs text-gray-600 bg-emerald-50 border border-emerald-100 rounded px-2 py-1">
                                  <input
                                    type="checkbox"
                                    checked={!!ov.create_template}
                                    onChange={(e) => setOverride(s.kpi_code, { create_template: e.target.checked, checklist_template: null })}
                                    className="rounded border-gray-300 text-emerald-600 focus:ring-emerald-400"
                                  />
                                  ➕ {t("kpi.suggest.create_template")}: <strong>{s.template_seed_name}</strong>
                                </label>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
            <div className="flex justify-between gap-2 px-6 py-4 border-t border-gray-200">
              <button onClick={() => setStep(1)} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">
                ← {t("kpi.suggest.back")}
              </button>
              <button
                onClick={() => setStep(3)}
                disabled={selected.size === 0}
                className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
              >
                {t("kpi.suggest.step2.next")} ({selected.size}) →
              </button>
            </div>
          </>
        )}

        {/* ── STEP 3 ── */}
        {step === 3 && (
          <div className="p-6 overflow-y-auto">
            {!importMutation.isSuccess ? (
              <>
                <p className="text-sm text-gray-600 mb-3">{t("kpi.suggest.step3.intro", { count: selectedList.length })}</p>
                <ul className="border border-gray-200 rounded-lg divide-y divide-gray-100 mb-4">
                  {selectedList.map((s) => {
                    const willCreate = !!overrides[s.kpi_code]?.create_template && s.can_create_template;
                    return (
                      <li key={s.kpi_code} className="px-4 py-2 text-sm flex items-center justify-between gap-2">
                        <span className="text-gray-800">
                          {s.name}
                          {willCreate && (
                            <span className="ml-2 text-xs text-emerald-700">
                              ➕ {t("kpi.suggest.will_create_template", { name: s.template_seed_name })}
                            </span>
                          )}
                        </span>
                        <span className="text-xs text-gray-400 font-mono">{s.kpi_code}</span>
                      </li>
                    );
                  })}
                </ul>
                {importMutation.isError && <p className="text-sm text-red-600 mb-2">{t("common.save_error")}</p>}
                <div className="flex justify-between gap-2">
                  <button onClick={() => setStep(2)} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">
                    ← {t("kpi.suggest.back")}
                  </button>
                  <button
                    onClick={handleImport}
                    disabled={importMutation.isPending}
                    className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
                  >
                    {importMutation.isPending ? t("kpi.suggest.step3.importing") : t("kpi.suggest.step3.import_btn", { count: selectedList.length })}
                  </button>
                </div>
              </>
            ) : (
              <div className="text-center py-6">
                <div className="text-4xl mb-2">✅</div>
                <p className="text-lg font-medium text-gray-900">
                  {t("kpi.suggest.import_success", { count: importMutation.data?.created.length ?? 0 })}
                </p>
                {(importMutation.data?.skipped.length ?? 0) > 0 && (
                  <p className="text-sm text-gray-500 mt-1">
                    {t("kpi.suggest.step3.skipped", { count: importMutation.data?.skipped.length })}
                  </p>
                )}
                {(importMutation.data?.errors.length ?? 0) > 0 && (
                  <div className="mt-3 text-sm text-red-600">
                    {t("kpi.suggest.step3.errors")}:
                    <ul className="mt-1">
                      {importMutation.data?.errors.map((e) => (
                        <li key={e.kpi_code} className="font-mono text-xs">{e.kpi_code}: {e.error}</li>
                      ))}
                    </ul>
                  </div>
                )}
                <button
                  onClick={() => { onImported(); onClose(); }}
                  className="mt-5 px-5 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700"
                >
                  {t("actions.close")}
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
