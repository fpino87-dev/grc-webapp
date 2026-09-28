import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { bcpApi, type BcpPlan } from "../../api/endpoints/bcp";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { ResultBadge, TestStateLabel, fmtDate, hours } from "./shared";

interface Props {
  plantId?: string;
  plantLabel: (id: string | null) => string;
  onEdit: (plan: BcpPlan) => void;
  onRecordTest: (plan: BcpPlan) => void;
}

export function BcpPlansTab({ plantId, plantLabel, onEdit, onRecordTest }: Props) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [showArchived, setShowArchived] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["bcp", "plans", plantId],
    queryFn: () => bcpApi.list(plantId ? { plant: plantId } : undefined),
    retry: false,
  });

  const onError = (err: unknown) =>
    setActionError(
      (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? t("bcp.form.save_error"),
    );
  const onSuccess = () => {
    setActionError(null);
    qc.invalidateQueries({ queryKey: ["bcp"] });
  };
  const approve = useMutation({ mutationFn: bcpApi.approve, onSuccess, onError });
  const archive = useMutation({ mutationFn: bcpApi.archive, onSuccess, onError });
  const remove = useMutation({ mutationFn: bcpApi.delete, onSuccess, onError });

  const all = data?.results ?? [];
  const archivedCount = all.filter(p => p.status === "archiviato").length;
  const plans = showArchived ? all : all.filter(p => p.status !== "archiviato");

  if (isLoading) return <div className="p-8 text-center text-gray-400">{t("bcp.loading")}</div>;

  return (
    <div className="space-y-3">
      {archivedCount > 0 && (
        <label className="flex items-center gap-2 text-sm text-gray-600">
          <input type="checkbox" checked={showArchived} onChange={e => setShowArchived(e.target.checked)} />
          {t("bcp.plans.show_archived", { count: archivedCount })}
        </label>
      )}
      {actionError && <p className="text-sm text-red-600">{actionError}</p>}

      <div className="bg-white rounded-lg border border-gray-200 overflow-x-auto">
        {plans.length === 0 ? (
          <div className="p-8 text-center text-gray-400">{t("bcp.plans.empty")}</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("bcp.plans.col_plan")}</th>
                <th className="text-left px-3 py-3 font-medium text-gray-600">{t("bcp.plans.col_document")}</th>
                <th className="text-left px-3 py-3 font-medium text-gray-600">{t("bcp.plans.col_status")}</th>
                <th className="text-left px-3 py-3 font-medium text-gray-600">{t("bcp.plans.col_test")}</th>
                <th className="text-left px-3 py-3 font-medium text-gray-600">RTO / RPO</th>
                <th className="px-3 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {plans.map(plan => {
                const archived = plan.status === "archiviato";
                return (
                  <tr key={plan.id} className="hover:bg-gray-50 align-top">
                    <td className="px-4 py-3">
                      <div className="font-medium text-gray-800">
                        {plan.title} <span className="text-xs font-normal text-gray-400">v{plan.version}</span>
                      </div>
                      <div className="text-[11px] text-gray-400 truncate max-w-xs" title={(plan.process_names ?? []).join(", ")}>
                        {!plantId && `${plantLabel(plan.plant)} · `}
                        {t("bcp.plans.processes", { count: plan.process_names?.length ?? 0 })}
                      </div>
                    </td>
                    <td className="px-3 py-3 text-xs">
                      {plan.document ? (
                        <Link to="/documents" className="text-primary-700 hover:underline block truncate max-w-[14rem]" title={plan.document_title ?? ""}>
                          {plan.document_code || plan.document_title}
                        </Link>
                      ) : (
                        <span className="text-amber-700">{t("bcp.plans.no_document")}</span>
                      )}
                      {plan.document_status && (
                        <span className={plan.document_status === "approvato" ? "text-green-700" : "text-gray-400"}>
                          {t(`bcp.document_status.${plan.document_status}`, { defaultValue: plan.document_status })}
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-3"><StatusBadge status={plan.status} /></td>
                    <td className="px-3 py-3 text-xs">
                      {!archived && plan.test_state && <div><TestStateLabel state={plan.test_state} /></div>}
                      {plan.last_test_result && (
                        <div className="mt-0.5 flex items-center gap-1">
                          <ResultBadge result={plan.last_test_result} />
                          <span className="text-gray-400">{fmtDate(plan.last_test_date)}</span>
                        </div>
                      )}
                      {!archived && plan.next_test_date && (
                        <div className="text-gray-400">{t("bcp.plans.next_test", { date: fmtDate(plan.next_test_date) })}</div>
                      )}
                    </td>
                    <td className="px-3 py-3 text-xs text-gray-600 whitespace-nowrap">
                      {hours(plan.rto_hours)} / {hours(plan.rpo_hours)}
                    </td>
                    <td className="px-3 py-3">
                      <div className="flex flex-wrap gap-1 justify-end">
                        {!archived && (
                          <>
                            <button onClick={() => onRecordTest(plan)} className="text-xs text-blue-700 border border-blue-300 rounded px-2 py-0.5 hover:bg-blue-50">
                              {t("bcp.actions.add_test")}
                            </button>
                            <button onClick={() => onEdit(plan)} className="text-xs text-gray-700 border border-gray-300 rounded px-2 py-0.5 hover:bg-gray-50">
                              {t("bcp.actions.edit")}
                            </button>
                          </>
                        )}
                        {plan.can_approve && (
                          <button
                            onClick={() => approve.mutate(plan.id)}
                            disabled={approve.isPending}
                            className="text-xs text-green-700 border border-green-300 rounded px-2 py-0.5 hover:bg-green-50 disabled:opacity-50"
                          >
                            {t("bcp.actions.approve")}
                          </button>
                        )}
                        {!archived && (
                          <button
                            onClick={() => { if (window.confirm(t("bcp.plans.archive_confirm"))) archive.mutate(plan.id); }}
                            disabled={archive.isPending}
                            className="text-xs text-gray-600 border border-gray-300 rounded px-2 py-0.5 hover:bg-gray-50 disabled:opacity-50"
                          >
                            {t("bcp.actions.archive")}
                          </button>
                        )}
                        <button
                          onClick={() => { if (window.confirm(t("bcp.plans.delete_confirm"))) remove.mutate(plan.id); }}
                          disabled={remove.isPending}
                          className="text-xs text-red-700 border border-red-300 rounded px-2 py-0.5 hover:bg-red-50 disabled:opacity-50"
                        >
                          {t("bcp.actions.delete")}
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
