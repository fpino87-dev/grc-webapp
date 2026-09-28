import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { bcpApi, type BcpCoverage, type BcpCoveragePlan } from "../../api/endpoints/bcp";
import { CoverageBadge, TestStateLabel, fmtDate, hours } from "./shared";

interface Props {
  plantId?: string;
  plantLabel: (id: string | null) => string;
  onCreatePlan: (plantId: string, processId: string) => void;
}

function PlanLine({ plan, rtoTarget }: { plan: BcpCoveragePlan; rtoTarget: number | null }) {
  const { t } = useTranslation();
  const over = rtoTarget != null && plan.rto_demonstrated != null && plan.rto_demonstrated > rtoTarget;
  return (
    <div className="text-xs">
      <span className="text-gray-800">{plan.title}</span>
      {plan.status !== "approvato" && (
        <span className="ml-1 text-gray-400">({t(`bcp.plan_status.${plan.status}`)})</span>
      )}
      {plan.status === "approvato" && (
        <span className="ml-2" title={plan.next_test_date ? t("bcp.plans.next_test", { date: fmtDate(plan.next_test_date) }) : undefined}>
          <TestStateLabel state={plan.test_state} />
        </span>
      )}
      {plan.rto_demonstrated != null && (
        <span
          className={`ml-2 ${over ? "text-orange-700 font-medium" : "text-gray-500"}`}
          title={plan.rto_measured ? t("bcp.coverage.rto_measured") : t("bcp.coverage.rto_declared")}
        >
          RTO {plan.rto_demonstrated}h{plan.rto_measured ? "" : "*"}
        </span>
      )}
    </div>
  );
}

export function BcpCoverageTab({ plantId, plantLabel, onCreatePlan }: Props) {
  const { t } = useTranslation();
  const { data: rows = [], isLoading } = useQuery({
    queryKey: ["bcp", "coverage", plantId],
    queryFn: () => bcpApi.coverage(plantId),
    retry: false,
  });

  const counts = rows.reduce<Record<BcpCoverage, number>>(
    (acc, r) => ({ ...acc, [r.coverage]: acc[r.coverage] + 1 }),
    { covered: 0, test_expired: 0, missing: 0 },
  );

  if (isLoading) return <div className="p-8 text-center text-gray-400">{t("bcp.loading")}</div>;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {(["covered", "test_expired", "missing"] as const).map(key => (
          <div key={key} className="bg-white rounded-lg border border-gray-200 p-4">
            <p className="text-xs text-gray-500">{t(`bcp.coverage.state.${key}`)}</p>
            <p className={`text-2xl font-bold ${
              key === "covered" ? "text-green-700" : counts[key] > 0 ? (key === "missing" ? "text-red-700" : "text-yellow-700") : "text-gray-900"
            }`}>{counts[key]}</p>
            <p className="text-xs text-gray-400">{t(`bcp.coverage.hint.${key}`)}</p>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {rows.length === 0 ? (
          <div className="p-8 text-center text-gray-400">{t("bcp.coverage.empty")}</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("bcp.coverage.col_process")}</th>
                <th className="text-center px-3 py-3 font-medium text-gray-600">{t("bcp.coverage.col_criticality")}</th>
                <th className="text-left px-3 py-3 font-medium text-gray-600">{t("bcp.coverage.col_targets")}</th>
                <th className="text-left px-3 py-3 font-medium text-gray-600">{t("bcp.coverage.col_coverage")}</th>
                <th className="text-left px-3 py-3 font-medium text-gray-600">{t("bcp.coverage.col_plans")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {rows.map(row => (
                <tr key={row.process_id} className="hover:bg-gray-50 align-top">
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-800">{row.process_name}</div>
                    {!plantId && <div className="text-[11px] text-gray-400">{plantLabel(row.plant)}</div>}
                  </td>
                  <td className="px-3 py-3 text-center text-gray-700">{row.criticality}</td>
                  <td className="px-3 py-3 text-xs text-gray-600 whitespace-nowrap">
                    RTO {hours(row.rto_target_hours)} · RPO {hours(row.rpo_target_hours)}
                    {row.mtpd_hours != null && <div className="text-gray-400">MTPD {row.mtpd_hours}h</div>}
                  </td>
                  <td className="px-3 py-3"><CoverageBadge coverage={row.coverage} /></td>
                  <td className="px-3 py-3 space-y-1">
                    {row.plans.map(p => <PlanLine key={p.id} plan={p} rtoTarget={row.rto_target_hours} />)}
                    {row.coverage === "missing" && row.plant && (
                      <button
                        onClick={() => onCreatePlan(row.plant as string, row.process_id)}
                        className="text-xs text-primary-700 hover:underline"
                      >
                        {t("bcp.coverage.create_plan")}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <p className="text-xs text-gray-400">{t("bcp.coverage.footnote")}</p>
    </div>
  );
}
