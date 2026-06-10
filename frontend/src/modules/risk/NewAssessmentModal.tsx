import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { riskApi, type RiskAssessment, THREAT_CATEGORIES, PROB_LABELS, IMPACT_LABELS, NIS2_ART21_CHOICES, NIS2_RELEVANCE_CHOICES } from "../../api/endpoints/risk";
import { biaApi } from "../../api/endpoints/bia";
import { usersApi } from "../../api/endpoints/users";
import { useAuthStore } from "../../store/auth";
import { ProbImpactSelector } from "./ProbImpactSelector";
import { matrixColor } from "./riskUtils";
import { useTranslation } from "react-i18next";
import i18n from "../../i18n";

export function NewAssessmentModal({ plants, onClose }: { plants: { id: string; code: string; name: string }[]; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const selectedPlant = useAuthStore(s => s.selectedPlant);
  const [form, setForm] = useState<Partial<RiskAssessment>>({
    assessment_type: "IT",
    probability: null,
    impact: null,
    plant: selectedPlant?.id ?? "",
  });
  const [error, setError] = useState("");

  const plantId = form.plant;

  const { data: processes } = useQuery({
    queryKey: ["bia-processes", plantId],
    queryFn: () => biaApi.list(plantId ? { plant: plantId, page_size: "200" } : {}),
    enabled: !!plantId,
    retry: false,
  });

  const { data: users } = useQuery({
    queryKey: ["users"],
    queryFn: () => usersApi.list(),
    retry: false,
  });

  const mutation = useMutation({
    mutationFn: () => riskApi.create(form),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["risk-assessments"] }); onClose(); },
    onError: (e: any) => setError(e?.response?.data?.detail || JSON.stringify(e?.response?.data) || t("risk.error_generic")),
  });

  function set(field: string, value: unknown) { setForm(f => ({ ...f, [field]: value })); }

  const canSave = !!form.plant && !!form.name && !!form.probability && !!form.impact;

  const selectedProcess = processes?.results?.find(p => p.id === form.critical_process);

  // Estimate ALE locally for display (probability × impact × downtime_cost_hour)
  function estimateAle(): string | null {
    if (!selectedProcess?.downtime_cost_hour) return null;
    if (!form.probability || !form.impact) return null;
    const oreMap: Record<number, number> = {1:1, 2:4, 3:24, 4:72, 5:168};
    const probMap: Record<number, number> = {1:0.1, 2:0.3, 3:1.0, 4:3.0, 5:10.0};
    const ore = oreMap[form.impact] ?? 24;
    const prob = probMap[form.probability] ?? 1.0;
    let ale = parseFloat(selectedProcess.downtime_cost_hour) * ore * prob;
    if (selectedProcess.danno_reputazionale >= 4) ale *= 1.3;
    if (selectedProcess.danno_normativo >= 4) ale *= 1.2;
    return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(ale);
  }

  const alePreview = estimateAle();

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl flex flex-col max-h-[92vh]">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 shrink-0">
          <h3 className="text-lg font-semibold">{t("risk.new_title")}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl w-8 h-8 flex items-center justify-center rounded hover:bg-gray-100">×</button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("risk.name_label")}</label>
            <input value={form.name ?? ""} onChange={e => set("name", e.target.value)}
              placeholder={t("risk.scenario_placeholder")}
              className="w-full border rounded px-3 py-2 text-sm" />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("risk.cause_label")}</label>
              <textarea value={form.cause ?? ""} onChange={e => set("cause", e.target.value)}
                rows={2} placeholder={t("risk.cause_placeholder")}
                className="w-full border rounded px-3 py-2 text-sm resize-none" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("risk.consequence_label")}</label>
              <textarea value={form.consequence ?? ""} onChange={e => set("consequence", e.target.value)}
                rows={2} placeholder={t("risk.consequence_placeholder")}
                className="w-full border rounded px-3 py-2 text-sm resize-none" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("risk.site_label")}</label>
              <select value={form.plant ?? ""} onChange={e => { set("plant", e.target.value); set("critical_process", null); }} className="w-full border rounded px-3 py-2 text-sm">
                <option value="">{t("risk.select_placeholder")}</option>
                {plants.map(p => <option key={p.id} value={p.id}>{p.code} — {p.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("risk.threat_category_label")}</label>
              <select value={form.threat_category ?? ""} onChange={e => set("threat_category", e.target.value)} className="w-full border rounded px-3 py-2 text-sm">
                <option value="">{t("risk.select_placeholder")}</option>
                {THREAT_CATEGORIES.map(c => <option key={c.value} value={c.value}>{t(c.label)}</option>)}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("risk.asset_type_label")}</label>
              <div className="flex gap-4 mt-1">
                {(["IT", "OT"] as const).map(at => (
                  <label key={at} className="flex items-center gap-2 cursor-pointer">
                    <input type="radio" name="assessment_type" value={at} checked={form.assessment_type === at} onChange={() => set("assessment_type", at)} className="accent-primary-600" />
                    <span className="text-sm font-medium">{at}</span>
                  </label>
                ))}
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("risk.treatment_label")}</label>
              <select value={form.treatment ?? ""} onChange={e => set("treatment", e.target.value)} className="w-full border rounded px-3 py-2 text-sm">
                <option value="">{t("common.select")}</option>
                <option value="mitigare">{t("risk.treatment_mitigare")}</option>
                <option value="accettare">{t("risk.treatment_accettare")}</option>
                <option value="trasferire">{t("risk.treatment_trasferire_ext")}</option>
                <option value="evitare">{t("risk.treatment_evitare")}</option>
              </select>
            </div>
          </div>

          {/* Scadenza piano di trattamento */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("risk.plan_due_date_label")}</label>
            <input
              type="date"
              value={form.plan_due_date ?? ""}
              onChange={e => set("plan_due_date", e.target.value || null)}
              className="w-full border rounded px-3 py-2 text-sm"
            />
            <p className="text-xs text-gray-500 mt-1">{t("risk.plan_due_date_help")}</p>
          </div>

          {/* Owner rischio */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("risk.owner_label")}</label>
            <select value={form.owner ?? ""} onChange={e => set("owner", e.target.value || null)} className="w-full border rounded px-3 py-2 text-sm">
              <option value="">{t("risk.no_owner")}</option>
              {users?.map(u => (
                <option key={u.id} value={u.id}>
                  {u.first_name || u.last_name ? `${u.first_name} ${u.last_name}`.trim() : u.username} ({u.email})
                </option>
              ))}
            </select>
          </div>

          {/* Processo BIA collegato */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("risk.bia_process_label")}</label>
            <select
              value={form.critical_process ?? ""}
              onChange={e => set("critical_process", e.target.value || null)}
              disabled={!plantId}
              className="w-full border rounded px-3 py-2 text-sm disabled:bg-gray-50"
            >
              <option value="">{t("risk.no_bia_process")}</option>
              {processes?.results?.map(p => (
                <option key={p.id} value={p.id}>
                  {p.name} {t("risk.bia_criticality_bracket", { count: p.criticality })}
                </option>
              ))}
            </select>
            {selectedProcess && (
              <div className="mt-1.5 px-3 py-2 bg-blue-50 rounded text-xs text-blue-700 flex gap-3">
                <span>{t("risk.bia_downtime_cost")} <strong>{selectedProcess.downtime_cost_hour ? new Intl.NumberFormat(i18n.language, {style:"currency",currency:"EUR"}).format(parseFloat(selectedProcess.downtime_cost_hour)) : "—"}</strong></span>
                <span>{t("risk.bia_criticality_val")} <strong>{selectedProcess.criticality}</strong>/5</span>
              </div>
            )}
          </div>

          {/* P × I inerente (prima dei controlli) */}
          <div className="border border-orange-200 rounded-lg p-4 bg-orange-50/30">
            <p className="text-sm font-medium text-orange-800 mb-1">{t("risk.inherent_section")}</p>
            <p className="text-xs text-orange-600 mb-3">{t("risk.inherent_hint")}</p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">{t("risk.inherent_probability_label")}</label>
                <select
                  value={form.inherent_probability ?? ""}
                  onChange={e => set("inherent_probability", e.target.value ? Number(e.target.value) : null)}
                  className="w-full border rounded px-2 py-1.5 text-sm"
                >
                  <option value="">{t("risk.select_placeholder")}</option>
                  {[1,2,3,4,5].map(v => <option key={v} value={v}>{t(PROB_LABELS[v])}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">{t("risk.inherent_impact_label")}</label>
                <select
                  value={form.inherent_impact ?? ""}
                  onChange={e => set("inherent_impact", e.target.value ? Number(e.target.value) : null)}
                  className="w-full border rounded px-2 py-1.5 text-sm"
                >
                  <option value="">{t("risk.select_placeholder")}</option>
                  {[1,2,3,4,5].map(v => <option key={v} value={v}>{t(IMPACT_LABELS[v])}</option>)}
                </select>
              </div>
              {form.inherent_probability && form.inherent_impact && (
                <div className="col-span-2">
                  <div className={`rounded px-3 py-2 text-center text-sm font-semibold ${matrixColor(form.inherent_probability, form.inherent_impact)}`}>
                    {t("risk.inherent_score_label")} {form.inherent_probability} × {form.inherent_impact} = {form.inherent_probability * form.inherent_impact}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* P × I residuo */}
          <div className="border border-gray-200 rounded-lg p-4">
            <p className="text-sm font-medium text-gray-700 mb-3">{t("risk.residual_section")}</p>
            <ProbImpactSelector
              probability={form.probability ?? null}
              impact={form.impact ?? null}
              onChange={(field, value) => set(field, value)}
            />
          </div>

          {/* Classificazione NIS2 */}
          <details className="border border-blue-200 rounded-lg">
            <summary className="px-4 py-2 cursor-pointer text-sm font-medium text-blue-800 bg-blue-50 rounded-lg select-none">
              {t("risk.nis2_section")}
            </summary>
            <div className="px-4 py-3 space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{t("risk.nis2_art21_label")}</label>
                  <select value={form.nis2_art21_category ?? ""} onChange={e => set("nis2_art21_category", e.target.value)}
                    className="w-full border rounded px-3 py-2 text-xs">
                    <option value="">{t("risk.select_placeholder")}</option>
                    {NIS2_ART21_CHOICES.map(c => <option key={c.value} value={c.value}>{t(c.label)}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{t("risk.nis2_relevance_label")}</label>
                  <select value={form.nis2_relevance ?? ""} onChange={e => set("nis2_relevance", e.target.value)}
                    className="w-full border rounded px-3 py-2 text-xs">
                    <option value="">{t("risk.select_placeholder")}</option>
                    {NIS2_RELEVANCE_CHOICES.map(c => <option key={c.value} value={c.value}>{t(c.label)}</option>)}
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">{t("risk.impacted_systems_label")}</label>
                <input value={form.impacted_systems ?? ""} onChange={e => set("impacted_systems", e.target.value)}
                  placeholder={t("risk.impacted_systems_placeholder")}
                  className="w-full border rounded px-3 py-2 text-xs" />
              </div>
            </div>
          </details>

          {/* ALE calcolato (readonly) */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("risk.ale_label")}</label>
            {alePreview ? (
              <>
                <div className="w-full border border-dashed border-blue-300 bg-blue-50 rounded px-3 py-2 text-sm font-semibold text-blue-800">
                  {alePreview}
                </div>
                <p className="text-xs text-gray-400 mt-1">{t("risk.ale_auto_hint")}</p>
              </>
            ) : (
              <div className="w-full border border-dashed border-gray-200 bg-gray-50 rounded px-3 py-2 text-sm text-gray-400">
                {selectedProcess ? t("risk.ale_select_hint") : t("risk.ale_bia_hint")}
              </div>
            )}
          </div>
        </div>

        {error && <p className="text-sm text-red-600 bg-red-50 px-6 py-2">{error}</p>}
        <div className="flex justify-end gap-2 px-6 py-4 border-t border-gray-100 shrink-0">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">{t("actions.cancel")}</button>
          <button onClick={() => mutation.mutate()} disabled={mutation.isPending || !canSave}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50">
            {mutation.isPending ? t("common.saving") : t("risk.create_btn")}
          </button>
        </div>
      </div>
    </div>
  );
}
