import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { suppliersApi, type SupplierQuestionnaire } from "../../api/endpoints/suppliers";
import { QStatus, RiskBadge } from "./supplierBadges";
import { EvaluateModal } from "./QuestionnaireModals";
import { useTranslation } from "react-i18next";
import i18n from "../../i18n";

export function QuestionariTab() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [evaluateTarget, setEvaluateTarget] = useState<SupplierQuestionnaire | null>(null);
  const [filterStatus, setFilterStatus] = useState("");

  const params: Record<string, string> = {};
  if (filterStatus) params.status = filterStatus;

  const { data, isLoading } = useQuery({
    queryKey: ["supplier-questionnaires", filterStatus],
    queryFn: () => suppliersApi.listQuestionnaires(Object.keys(params).length ? params : undefined),
  });
  const questionnaires = data ?? [];

  const resendMutation = useMutation({
    mutationFn: (id: string) => suppliersApi.resendQuestionnaire(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["supplier-questionnaires"] }),
    onError: (e: any) => window.alert(e?.response?.data?.error || t("suppliers.quests.error_resend")),
  });

  return (
    <div>
      {evaluateTarget && <EvaluateModal questionnaire={evaluateTarget} onClose={() => setEvaluateTarget(null)} />}

      <div className="flex items-center gap-3 mb-4">
        <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)} className="border rounded px-3 py-1.5 text-sm">
          <option value="">{t("suppliers.quests.all_statuses")}</option>
          <option value="inviato">{t("suppliers.quests.waiting")}</option>
          <option value="risposto">{t("suppliers.quests.responded")}</option>
          <option value="scaduto">{t("suppliers.quests.expired")}</option>
        </select>
        <span className="text-sm text-gray-500">{t("suppliers.quests.count", { count: questionnaires.length })}</span>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-6 text-center text-gray-400">{t("common.loading")}</div>
        ) : questionnaires.length === 0 ? (
          <div className="p-6 text-center text-gray-400">{t("suppliers.quests.none")}</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("suppliers.quests.col_supplier")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("suppliers.quests.col_sent_to")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("suppliers.quests.col_first_send")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("suppliers.quests.col_last_send")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("suppliers.quests.col_status")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("suppliers.quests.col_eval_date")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("suppliers.quests.col_result")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("suppliers.quests.col_expires")}</th>
                <th className="px-4 py-3 w-28"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {questionnaires.map(q => (
                <tr key={q.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-800">{q.supplier_name}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{q.sent_to}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{new Date(q.sent_at).toLocaleDateString(i18n.language || "it")}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{new Date(q.last_sent_at).toLocaleDateString(i18n.language || "it")}</td>
                  <td className="px-4 py-3"><QStatus status={q.status} sendCount={q.send_count} /></td>
                  <td className="px-4 py-3 text-gray-600">{q.evaluation_date ? new Date(q.evaluation_date).toLocaleDateString(i18n.language || "it") : "—"}</td>
                  <td className="px-4 py-3">{q.risk_result ? <RiskBadge level={q.risk_result} /> : <span className="text-gray-400">—</span>}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{q.expires_at ? new Date(q.expires_at).toLocaleDateString(i18n.language || "it") : "—"}</td>
                  <td className="px-4 py-3 text-right space-x-1">
                    {q.status === "inviato" && (
                      <>
                        <button
                          onClick={() => resendMutation.mutate(q.id)}
                          disabled={resendMutation.isPending}
                          className="text-xs text-indigo-600 border border-indigo-200 rounded px-1.5 py-0.5 hover:bg-indigo-50 disabled:opacity-50"
                          title={q.send_count >= 3 ? t("suppliers.quests.resend_max_title") : t("suppliers.quests.resend_title", { n: q.send_count + 1 })}
                        >
                          {t("suppliers.quests.resend")} {q.send_count >= 3 ? "(3°)" : ""}
                        </button>
                        <button
                          onClick={() => setEvaluateTarget(q)}
                          className="text-xs text-green-600 border border-green-200 rounded px-1.5 py-0.5 hover:bg-green-50"
                        >
                          {t("suppliers.quests.evaluate")}
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
