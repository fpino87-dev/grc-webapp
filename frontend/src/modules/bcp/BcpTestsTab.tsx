import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { bcpApi } from "../../api/endpoints/bcp";
import { ResultBadge, fmtDate, hours } from "./shared";

interface Props {
  plantId?: string;
  plantLabel: (id: string | null) => string;
}

export function BcpTestsTab({ plantId, plantLabel }: Props) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [planFilter, setPlanFilter] = useState("");

  const { data: tests = [], isLoading } = useQuery({
    queryKey: ["bcp", "tests", plantId],
    queryFn: () => bcpApi.tests(plantId ? { plan__plant: plantId } : undefined),
    retry: false,
  });
  const { data: plansData } = useQuery({
    queryKey: ["bcp", "plans", plantId],
    queryFn: () => bcpApi.list(plantId ? { plant: plantId } : undefined),
    retry: false,
  });
  const targets = new Map((plansData?.results ?? []).map(p => [p.id, p]));

  const remove = useMutation({
    mutationFn: bcpApi.deleteTest,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["bcp"] }),
  });

  const planOptions = Array.from(new Map(tests.map(x => [x.plan, x.plan_title])).entries())
    .sort((a, b) => a[1].localeCompare(b[1]));
  const rows = planFilter ? tests.filter(x => x.plan === planFilter) : tests;

  if (isLoading) return <div className="p-8 text-center text-gray-400">{t("bcp.loading")}</div>;

  return (
    <div className="space-y-3">
      {planOptions.length > 1 && (
        <select value={planFilter} onChange={e => setPlanFilter(e.target.value)} className="border rounded px-3 py-1.5 text-sm">
          <option value="">{t("bcp.tests.all_plans")}</option>
          {planOptions.map(([id, title]) => <option key={id} value={id}>{title}</option>)}
        </select>
      )}
      <div className="bg-white rounded-lg border border-gray-200 overflow-x-auto">
        {rows.length === 0 ? (
          <div className="p-8 text-center text-gray-400">{t("bcp.tests.empty")}</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("bcp.tests.col_date")}</th>
                <th className="text-left px-3 py-3 font-medium text-gray-600">{t("bcp.tests.col_plan")}</th>
                <th className="text-left px-3 py-3 font-medium text-gray-600">{t("bcp.tests.col_type")}</th>
                <th className="text-left px-3 py-3 font-medium text-gray-600">{t("bcp.tests.col_result")}</th>
                <th className="text-left px-3 py-3 font-medium text-gray-600">{t("bcp.tests.col_rto")}</th>
                <th className="text-left px-3 py-3 font-medium text-gray-600">{t("bcp.tests.col_rpo")}</th>
                <th className="text-left px-3 py-3 font-medium text-gray-600">{t("bcp.tests.col_objectives")}</th>
                <th className="text-left px-3 py-3 font-medium text-gray-600">{t("bcp.tests.col_evidence")}</th>
                <th className="px-3 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {rows.map(test => {
                const plan = targets.get(test.plan);
                const rtoOver = plan?.rto_hours != null && test.rto_achieved_hours != null && test.rto_achieved_hours > plan.rto_hours;
                const rpoOver = plan?.rpo_hours != null && test.rpo_achieved_hours != null && test.rpo_achieved_hours > plan.rpo_hours;
                const met = test.objectives.filter(o => o.met).length;
                return (
                  <tr key={test.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-700 whitespace-nowrap">{fmtDate(test.test_date)}</td>
                    <td className="px-3 py-3">
                      <div className="text-gray-800 truncate max-w-[14rem]" title={test.notes || undefined}>{test.plan_title}</div>
                      {!plantId && <div className="text-[11px] text-gray-400">{plantLabel(test.plant)}</div>}
                    </td>
                    <td className="px-3 py-3 text-xs text-gray-600">{t(`bcp.test_type.${test.test_type}`)}</td>
                    <td className="px-3 py-3"><ResultBadge result={test.result} /></td>
                    <td className={`px-3 py-3 text-xs whitespace-nowrap ${rtoOver ? "text-orange-700 font-medium" : "text-gray-600"}`}
                      title={plan?.rto_hours != null ? t("bcp.record.plan_value", { value: plan.rto_hours }) : undefined}>
                      {hours(test.rto_achieved_hours)}
                    </td>
                    <td className={`px-3 py-3 text-xs whitespace-nowrap ${rpoOver ? "text-orange-700 font-medium" : "text-gray-600"}`}
                      title={plan?.rpo_hours != null ? t("bcp.record.plan_value", { value: plan.rpo_hours }) : undefined}>
                      {hours(test.rpo_achieved_hours)}
                    </td>
                    <td className="px-3 py-3 text-xs text-gray-600"
                      title={test.objectives.map(o => `${o.met ? "✓" : "✗"} ${o.text}`).join("\n") || undefined}>
                      {test.objectives.length ? `${met}/${test.objectives.length}` : "—"}
                    </td>
                    <td className="px-3 py-3 text-xs text-gray-600">{test.evidences_count || "—"}</td>
                    <td className="px-3 py-3 text-right">
                      <button
                        onClick={() => { if (window.confirm(t("bcp.tests.delete_confirm"))) remove.mutate(test.id); }}
                        disabled={remove.isPending}
                        className="text-xs text-gray-400 hover:text-red-600 disabled:opacity-50"
                      >
                        {t("bcp.actions.delete")}
                      </button>
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
