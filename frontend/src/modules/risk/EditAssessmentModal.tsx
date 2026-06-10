import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { riskApi, type RiskAssessment, THREAT_CATEGORIES, NIS2_ART21_CHOICES, NIS2_RELEVANCE_CHOICES } from "../../api/endpoints/risk";
import { biaApi } from "../../api/endpoints/bia";
import { usersApi } from "../../api/endpoints/users";
import { ProbImpactSelector } from "./ProbImpactSelector";
import { useTranslation } from "react-i18next";

export function EditAssessmentModal({
  assessment,
  onClose,
}: {
  assessment: RiskAssessment;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const plantId = assessment.plant;

  const [form, setForm] = useState<Partial<RiskAssessment>>({
    name: assessment.name,
    threat_category: assessment.threat_category,
    assessment_type: assessment.assessment_type,
    owner: assessment.owner,
    critical_process: assessment.critical_process,
    treatment: assessment.treatment,
    plan_due_date: assessment.plan_due_date,
    inherent_probability: assessment.inherent_probability,
    inherent_impact: assessment.inherent_impact,
    probability: assessment.probability,
    impact: assessment.impact,
    cause: assessment.cause,
    consequence: assessment.consequence,
    nis2_art21_category: assessment.nis2_art21_category,
    nis2_relevance: assessment.nis2_relevance,
    impacted_systems: assessment.impacted_systems,
  });

  const [error, setError] = useState("");

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
    mutationFn: () => {
      const payload = {
        name: form.name,
        threat_category: form.threat_category,
        assessment_type: form.assessment_type,
        owner: form.owner ?? null,
        critical_process: form.critical_process ?? null,
        treatment: form.treatment ?? "",
        plan_due_date: form.plan_due_date ?? null,
        inherent_probability: form.inherent_probability ?? null,
        inherent_impact: form.inherent_impact ?? null,
        probability: form.probability ?? null,
        impact: form.impact ?? null,
        cause: form.cause ?? "",
        consequence: form.consequence ?? "",
        nis2_art21_category: form.nis2_art21_category ?? "",
        nis2_relevance: form.nis2_relevance ?? "",
        impacted_systems: form.impacted_systems ?? "",
      };
      return riskApi.update(assessment.id, payload);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["risk-assessments"] });
      onClose();
    },
    onError: (e: any) => setError(e?.response?.data?.detail || JSON.stringify(e?.response?.data) || t("risk.error_generic")),
  });

  const selectedProcess = processes?.results?.find(p => p.id === form.critical_process);

  function set(field: string, value: unknown) {
    setForm(f => ({ ...f, [field]: value }));
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl flex flex-col max-h-[92vh]">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 shrink-0">
          <h3 className="text-lg font-semibold">{t("risk.edit_title")}</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl w-8 h-8 flex items-center justify-center rounded hover:bg-gray-100"
          >
            ×
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("risk.name_label")}</label>
            <input
              value={form.name ?? ""}
              onChange={e => set("name", e.target.value)}
              className="w-full border rounded px-3 py-2 text-sm"
            />
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
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("risk.threat_category_label")}</label>
              <select
                value={form.threat_category ?? ""}
                onChange={e => set("threat_category", e.target.value)}
                className="w-full border rounded px-3 py-2 text-sm"
              >
                {THREAT_CATEGORIES.map(c => (
                  <option key={c.value} value={c.value}>
                    {t(c.label)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("risk.asset_type_label")}</label>
              <select
                value={form.assessment_type ?? "IT"}
                onChange={e => set("assessment_type", e.target.value)}
                className="w-full border rounded px-3 py-2 text-sm"
              >
                <option value="IT">IT</option>
                <option value="OT">OT</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("risk.treatment_label")}</label>
              <select
                value={form.treatment ?? ""}
                onChange={e => set("treatment", e.target.value)}
                className="w-full border rounded px-3 py-2 text-sm"
              >
                <option value="">{t("common.select")}</option>
                <option value="mitigare">{t("risk.treatment_mitigare")}</option>
                <option value="accettare">{t("risk.treatment_accettare")}</option>
                <option value="trasferire">{t("risk.treatment_trasferire")}</option>
                <option value="evitare">{t("risk.treatment_evitare")}</option>
              </select>
            </div>
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
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("risk.owner_label")}</label>
            <select
              value={form.owner ?? ""}
              onChange={e => set("owner", e.target.value || null)}
              className="w-full border rounded px-3 py-2 text-sm"
            >
              <option value="">{t("risk.no_owner")}</option>
              {users?.map(u => (
                <option key={u.id} value={u.id}>
                  {u.first_name || u.last_name ? `${u.first_name} ${u.last_name}`.trim() : u.username} ({u.email})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("risk.bia_process_edit_label")}</label>
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
              <p className="mt-2 text-xs text-gray-500">
                MTPD {selectedProcess.mtpd_hours ?? "—"}h • RTO target {selectedProcess.rto_target_hours ?? "—"}h
              </p>
            )}
          </div>

          <div className="border border-orange-200 rounded-lg p-4 bg-orange-50/30">
            <p className="text-sm font-medium text-orange-800 mb-2">{t("risk.inherent_section")}</p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">{t("risk.inherent_probability_label")}</label>
                <select
                  value={form.inherent_probability ?? ""}
                  onChange={e => set("inherent_probability", e.target.value ? Number(e.target.value) : null)}
                  className="w-full border rounded px-3 py-2 text-sm"
                >
                  <option value="">—</option>
                  {[1,2,3,4,5].map(v => <option key={v} value={v}>{v}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">{t("risk.inherent_impact_label")}</label>
                <select
                  value={form.inherent_impact ?? ""}
                  onChange={e => set("inherent_impact", e.target.value ? Number(e.target.value) : null)}
                  className="w-full border rounded px-3 py-2 text-sm"
                >
                  <option value="">—</option>
                  {[1,2,3,4,5].map(v => <option key={v} value={v}>{v}</option>)}
                </select>
              </div>
            </div>
          </div>

          <div className="border border-gray-200 rounded-lg p-4">
            <p className="text-sm font-medium text-gray-700 mb-3">{t("risk.residual_section")}</p>
            <ProbImpactSelector
              probability={form.probability ?? null}
              impact={form.impact ?? null}
              onChange={(field, value) => set(field, value)}
            />
          </div>

          {/* Classificazione NIS2 */}
          <details className="border border-blue-200 rounded-lg" open={!!(form.nis2_art21_category || form.nis2_relevance || form.impacted_systems)}>
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
        </div>

        {error && <p className="text-sm text-red-600 bg-red-50 px-6 py-2">{error}</p>}

        <div className="flex justify-end gap-2 px-6 py-4 border-t border-gray-100 shrink-0">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">
            {t("actions.cancel")}
          </button>
          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? t("common.saving") : t("actions.save")}
          </button>
        </div>
      </div>
    </div>
  );
}
