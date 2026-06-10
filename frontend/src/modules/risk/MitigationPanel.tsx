import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { riskApi, type RiskMitigationPlan } from "../../api/endpoints/risk";
import { bcpApi, type BcpPlan } from "../../api/endpoints/bcp";
import { useAuthStore } from "../../store/auth";
import { useTranslation } from "react-i18next";
import i18n from "../../i18n";
import { usePlantToday } from "../../utils/dates";

export function MitigationPanel({ assessmentId }: { assessmentId: string }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<Partial<RiskMitigationPlan>>({});
  const [editPlan, setEditPlan] = useState<RiskMitigationPlan | null>(null);
  const [editForm, setEditForm] = useState<Partial<RiskMitigationPlan>>({});
  const selectedPlant = useAuthStore(s => s.selectedPlant);

  const { data: riskContext } = useQuery({
    queryKey: ["risk-context", assessmentId],
    queryFn: () => riskApi.context(assessmentId),
  });

  const { data: plans = [] } = useQuery({
    queryKey: ["mitigation-plans", assessmentId],
    queryFn: () => riskApi.mitigationPlans(assessmentId),
  });

  const todayStr = usePlantToday();

  // Preferiamo i BCP "coerenti" trovati dal contesto (cioè legati al processo BIA del risk).
  // Se sono vuoti (es. risk senza critical_process collegato o BCP non legato al processo),
  // facciamo fallback mostrando i BCP del sito corrente.
  const contextBcpPlans = (riskContext?.bcp_plans ?? []) as Array<{
    id: string;
    title: string;
    status: string;
    last_test_date?: string | null;
    next_test_date?: string | null;
  }>;

  const { data: bcpFallbackResp } = useQuery({
    queryKey: ["bcp-fallback", selectedPlant?.id],
    queryFn: () => bcpApi.list(selectedPlant?.id ? { plant: selectedPlant.id } : {}),
    enabled: !!selectedPlant?.id,
    retry: false,
  });

  const fallbackBcpPlans = (bcpFallbackResp?.results ?? []) as BcpPlan[];

  const availableBcpPlans = contextBcpPlans.length ? contextBcpPlans : fallbackBcpPlans;
  const selectedBcpPlan =
    availableBcpPlans.find(p => p.id === (form.bcp_plan ?? "")) ?? null;

  const createMutation = useMutation({
    mutationFn: () => riskApi.createPlan({ ...form, assessment: assessmentId }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["mitigation-plans", assessmentId] }); setShowForm(false); setForm({}); },
  });

  const completeMutation = useMutation({
    mutationFn: (id: string) => riskApi.completePlan(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mitigation-plans", assessmentId] }),
  });

  const uncompleteMutation = useMutation({
    mutationFn: (id: string) => riskApi.uncompletePlan(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mitigation-plans", assessmentId] }),
  });

  const deletePlanMutation = useMutation({
    mutationFn: (id: string) => riskApi.deletePlan(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mitigation-plans", assessmentId] }),
  });

  const updateMutation = useMutation({
    mutationFn: () => {
      if (!editPlan) return Promise.reject(new Error("No plan selected"));
      return riskApi.updatePlan(editPlan.id, editForm);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mitigation-plans", assessmentId] });
      setEditPlan(null);
      setEditForm({});
    },
  });

  return (
    <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-gray-700">{t("risk.mitigation_progress", { completed: plans.filter(p => p.completed_at != null).length, total: plans.length })}</h4>
        <button onClick={() => setShowForm(s => !s)} className="text-xs px-2 py-1 bg-primary-600 text-white rounded hover:bg-primary-700">
          + {t("risk.add_plan")}
        </button>
      </div>

      {showForm && (
        <div className="bg-white border border-gray-200 rounded p-3 mb-3 space-y-2">
          <textarea
            placeholder={t("risk.action_desc_placeholder")}
            value={form.action ?? ""}
            onChange={e => setForm(p => ({ ...p, action: e.target.value }))}
            className="w-full border rounded px-2 py-1.5 text-sm" rows={2}
          />
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">{t("risk.bcp_link_label")}</label>
            <select
              value={form.bcp_plan ?? ""}
              onChange={e => {
                const id = e.target.value || null;
                const chosen = availableBcpPlans.find(p => p.id === id) ?? null;
                setForm(prev => ({
                  ...prev,
                  bcp_plan: id,
                  // Coerenza: per la mitigazione usiamo la "data dell'ultimo test valido".
                  due_date: chosen?.last_test_date ?? prev.due_date,
                }));
              }}
              className="w-full border rounded px-2 py-1.5 text-sm"
            >
              <option value="">— {t("risk.no_bcp_option")} —</option>
              {availableBcpPlans.map(p => (
                <option key={p.id} value={p.id}>
                  {p.title} · {p.status} · {t("risk.bcp_valid_until")} {p.next_test_date ?? "—"}
                </option>
              ))}
            </select>
          </div>
          <div className="flex gap-2">
            <input
              type="date"
              placeholder={t("risk.bcp_test_date_placeholder")}
              value={form.due_date ?? ""}
              onChange={e => setForm(p => ({ ...p, due_date: e.target.value }))}
              disabled={!!selectedBcpPlan?.last_test_date}
              className="border rounded px-2 py-1.5 text-sm flex-1 disabled:bg-gray-50"
            />
            <button onClick={() => createMutation.mutate()} disabled={createMutation.isPending || !form.action || !form.due_date}
              className="px-3 py-1.5 bg-primary-600 text-white text-xs rounded hover:bg-primary-700 disabled:opacity-50">{t("actions.save")}</button>
            <button onClick={() => setShowForm(false)} className="px-3 py-1.5 border rounded text-xs text-gray-600 hover:bg-gray-50">{t("actions.cancel")}</button>
          </div>
        </div>
      )}

      {editPlan && (
        <div className="bg-white border border-gray-200 rounded p-3 mb-3 space-y-2">
          <textarea
            placeholder={t("risk.action_desc_placeholder")}
            value={editForm.action ?? editPlan.action ?? ""}
            onChange={e => setEditForm(p => ({ ...p, action: e.target.value }))}
            className="w-full border rounded px-2 py-1.5 text-sm" rows={2}
          />
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">{t("risk.bcp_link_label")}</label>
            <select
              value={editForm.bcp_plan ?? editPlan.bcp_plan ?? ""}
              onChange={e => {
                const id = e.target.value || null;
                const chosen = availableBcpPlans.find(p => p.id === id) ?? null;
                setEditForm(prev => ({
                  ...prev,
                  bcp_plan: id,
                  due_date: chosen?.last_test_date ?? prev.due_date,
                }));
              }}
              className="w-full border rounded px-2 py-1.5 text-sm"
            >
              <option value="">— {t("risk.no_bcp_option")} —</option>
              {availableBcpPlans.map(p => (
                <option key={p.id} value={p.id}>
                  {p.title} · {p.status} · {t("risk.bcp_valid_until")} {p.next_test_date ?? "—"}
                </option>
              ))}
            </select>
          </div>
          <div className="flex gap-2">
            <input
              type="date"
              placeholder={t("risk.bcp_test_date_placeholder")}
              value={editForm.due_date ?? editPlan.due_date ?? ""}
              onChange={e => setEditForm(p => ({ ...p, due_date: e.target.value }))}
              disabled={!!(availableBcpPlans.find(p => p.id === (editForm.bcp_plan ?? editPlan.bcp_plan))?.last_test_date)}
              className="border rounded px-2 py-1.5 text-sm flex-1 disabled:bg-gray-50"
            />
            <button
              onClick={() => updateMutation.mutate()}
              disabled={updateMutation.isPending || !((editForm.action ?? editPlan.action) && (editForm.due_date ?? editPlan.due_date))}
              className="px-3 py-1.5 bg-primary-600 text-white text-xs rounded hover:bg-primary-700 disabled:opacity-50"
            >
              {updateMutation.isPending ? t("common.saving") : t("actions.save")}
            </button>
            <button onClick={() => { setEditPlan(null); setEditForm({}); }} className="px-3 py-1.5 border rounded text-xs text-gray-600 hover:bg-gray-50">
              {t("actions.cancel")}
            </button>
          </div>
        </div>
      )}

      {plans.length === 0 ? (
        <p className="text-xs text-gray-400">{t("risk.no_mitigation_plans")}</p>
      ) : (
        <div className="space-y-2">
          {plans.map(plan => {
            const bcpValid =
              plan.bcp_plan_next_test_date
                ? plan.bcp_plan_next_test_date >= todayStr
                : plan.due_date >= todayStr;
            const isDone = !!plan.completed_at;
            const dotColor = isDone ? "bg-green-500" : (bcpValid ? "bg-green-400" : "bg-orange-400");
            return (
            <div key={plan.id} className="flex items-center gap-3 bg-white rounded border border-gray-200 px-3 py-2 text-sm">
              <span className={`w-2 h-2 rounded-full shrink-0 ${dotColor}`} />
              <span className="flex-1 text-gray-700">{plan.action}</span>
              <span className="text-xs text-gray-400 shrink-0">
                <div className="space-y-1">
                  <div>
                    {t("risk.last_test")} {plan.due_date ? new Date(plan.due_date + "T12:00:00").toLocaleDateString(i18n.language || "it") : "—"}
                  </div>
                  <div>
                    {plan.bcp_plan_next_test_date
                      ? `${t("risk.next_test")} ${new Date(plan.bcp_plan_next_test_date + "T12:00:00").toLocaleDateString(i18n.language || "it")}`
                      : `${t("risk.next_test")} ${t("risk.next_test_no_bcp")}`}
                  </div>
                </div>
              </span>
              <span className="shrink-0 flex items-center gap-2">
                <button
                  onClick={() => {
                    setEditPlan(plan);
                    setEditForm({
                      action: plan.action,
                      due_date: plan.due_date,
                      bcp_plan: plan.bcp_plan ?? null,
                    });
                  }}
                  className="text-xs text-purple-700 border border-purple-300 rounded px-2 py-0.5 hover:bg-purple-50 whitespace-nowrap"
                >
                  {t("actions.edit")}
                </button>
                <button
                  onClick={() => {
                    if (window.confirm(t("risk.plan_delete_confirm"))) deletePlanMutation.mutate(plan.id);
                  }}
                  disabled={deletePlanMutation.isPending}
                  title={t("actions.delete")}
                  className="text-gray-400 hover:text-red-600 hover:bg-red-50 rounded p-0.5 transition-colors disabled:opacity-50"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                </button>
              </span>
              {!plan.completed_at ? (
                <button onClick={() => completeMutation.mutate(plan.id)} disabled={completeMutation.isPending} className="text-xs text-green-700 border border-green-300 rounded px-2 py-0.5 hover:bg-green-50 disabled:opacity-50 shrink-0">
                  {t("risk.plan_complete_btn")}
                </button>
              ) : (
                <button
                  onClick={() => { if (window.confirm(t("risk.plan_uncomplete_confirm"))) uncompleteMutation.mutate(plan.id); }}
                  disabled={uncompleteMutation.isPending}
                  title={t("risk.plan_uncomplete_label")}
                  className="text-xs text-green-600 border border-green-200 rounded px-2 py-0.5 hover:bg-orange-50 hover:text-orange-600 hover:border-orange-300 transition-colors shrink-0"
                >
                  ✓ {t("risk.plan_completed_label")}
                </button>
              )}
            </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
