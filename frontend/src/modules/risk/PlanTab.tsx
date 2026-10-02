import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { riskApi } from "../../api/endpoints/risk";
import type { RegisterId } from "./RiskPage";

/** Tutte le misure del piano di trattamento del registro, con i ritardi. */
export function PlanTab({ registerId, onOpen }: { registerId: RegisterId; onOpen: (id: string) => void }) {
  const { t, i18n } = useTranslation();
  const [filter, setFilter] = useState<"open" | "all" | "overdue" | "to_verify">("open");
  const { data: plans = [], isLoading } = useQuery({
    queryKey: ["risk-plans-register", registerId],
    queryFn: () => riskApi.plans({ plant: registerId ?? "null" }),
    retry: false,
  });
  const { data: risks = [] } = useQuery({
    queryKey: ["risk-register", registerId, false],
    queryFn: () => riskApi.list(registerId),
    retry: false,
  });
  const names = useMemo(() => new Map(risks.map(r => [r.id, r])), [risks]);
  const today = new Date().toISOString().slice(0, 10);
  const rows = plans.filter(p => {
    if (filter === "open") return !p.completed_at;
    if (filter === "overdue") return !p.completed_at && p.due_date < today;
    if (filter === "to_verify") return !!p.completed_at && !p.verified_at;
    return true;
  });
  const fmt = (d: string | null) => (d ? new Date(d).toLocaleDateString(i18n.language) : "—");

  return (
    <div>
      <div className="flex gap-2 mb-3 text-sm">
        {(["open", "overdue", "to_verify", "all"] as const).map(f => (
          <button key={f} onClick={() => setFilter(f)}
            className={`px-2.5 py-1 rounded border text-xs ${filter === f ? "bg-primary-600 text-white border-primary-600" : "bg-white"}`}>
            {t(`risk.plan.filters.${f}`)}
          </button>
        ))}
        <span className="ml-auto text-xs text-gray-400">{t("risk.plan.count", { count: rows.length })}</span>
      </div>
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? <p className="p-6 text-center text-sm text-gray-400">{t("common.loading")}</p>
          : rows.length === 0 ? <p className="p-6 text-center text-sm text-gray-400">{t("risk.plan.empty")}</p> : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b text-xs text-gray-600">
              <tr>
                <th className="text-left px-3 py-2 font-medium">{t("risk.plan.col_measure")}</th>
                <th className="text-left px-3 py-2 font-medium">{t("risk.plan.col_risk")}</th>
                <th className="text-left px-3 py-2 font-medium">{t("risk.plan.col_owner")}</th>
                <th className="text-left px-3 py-2 font-medium">{t("risk.plan.col_due")}</th>
                <th className="text-left px-3 py-2 font-medium">{t("risk.plan.col_status")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {rows.map(p => {
                const overdue = !p.completed_at && p.due_date < today;
                const risk = names.get(p.assessment);
                return (
                  <tr key={p.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => onOpen(p.assessment)}>
                    <td className="px-3 py-2"><span className="truncate block max-w-sm" title={p.action}>{p.action}</span>
                      {p.control_title && <span className="text-[11px] text-gray-400">{p.control_title}</span>}</td>
                    <td className="px-3 py-2 text-xs text-gray-600">{risk ? `${risk.threat_code ?? ""} ${risk.display_name}` : "—"}</td>
                    <td className="px-3 py-2 text-xs text-gray-600">{p.owner_name ?? "—"}</td>
                    <td className={`px-3 py-2 text-xs ${overdue ? "text-red-700 font-medium" : "text-gray-600"}`}>{fmt(p.due_date)}</td>
                    <td className="px-3 py-2 text-xs">
                      {p.verified_at ? <span className="text-green-700">✓ {t("risk.drawer.verified")}</span>
                        : p.completed_at ? <span className="text-blue-700">{t("risk.drawer.completed")}</span>
                        : overdue ? <span className="text-red-700">{t("risk.drawer.overdue")}</span>
                        : <span className="text-gray-500">{t("risk.drawer.open")}</span>}
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
