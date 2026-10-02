import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { riskApi } from "../../api/endpoints/risk";
import { ClassBadge } from "./RiskUi";
import type { RegisterId } from "./RiskPage";

/** Accettazioni del registro: attive, in scadenza, da firmare o da esprimere parere. */
export function AcceptancesTab({ registerId, onOpen }: { registerId: RegisterId; onOpen: (id: string) => void }) {
  const { t, i18n } = useTranslation();
  const [filter, setFilter] = useState<"awaiting_me" | "pending" | "active" | "closed">("active");
  const params: Record<string, string> = { plant: registerId ?? "null" };
  if (filter === "awaiting_me") params.awaiting_me = "1";
  else if (filter === "closed") params.status = "rejected,revoked,expired";
  else params.status = filter;
  const { data: rows = [], isLoading } = useQuery({
    queryKey: ["risk-acceptances", registerId, filter],
    queryFn: () => riskApi.acceptances(params),
    retry: false,
  });
  const soon = new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10);
  const fmt = (d: string | null) => (d ? new Date(d).toLocaleDateString(i18n.language) : "—");

  return (
    <div>
      <div className="flex gap-2 mb-3">
        {(["awaiting_me", "pending", "active", "closed"] as const).map(f => (
          <button key={f} onClick={() => setFilter(f)}
            className={`px-2.5 py-1 rounded border text-xs ${filter === f ? "bg-primary-600 text-white border-primary-600" : "bg-white"}`}>
            {t(`risk.acceptance.filters.${f}`)}
          </button>
        ))}
      </div>
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? <p className="p-6 text-center text-sm text-gray-400">{t("common.loading")}</p>
          : rows.length === 0 ? <p className="p-6 text-center text-sm text-gray-400">{t("risk.acceptance.empty")}</p> : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b text-xs text-gray-600">
              <tr>
                <th className="text-left px-3 py-2 font-medium">{t("risk.acceptance.col_risk")}</th>
                <th className="text-left px-3 py-2 font-medium">{t("risk.acceptance.col_class")}</th>
                <th className="text-left px-3 py-2 font-medium">{t("risk.acceptance.col_status")}</th>
                <th className="text-left px-3 py-2 font-medium">{t("risk.acceptance.col_expires")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {rows.map(a => (
                <tr key={a.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => onOpen(a.risk)}>
                  <td className="px-3 py-2"><span className="truncate block max-w-md" title={a.rationale}>{a.risk_name}</span></td>
                  <td className="px-3 py-2"><ClassBadge cls={a.risk_class} /></td>
                  <td className="px-3 py-2 text-xs text-gray-600">
                    {t(`risk.acceptance.status.${a.status}`)}
                    {a.status === "pending" && a.upper_opinion === "pending" && ` · ${t("risk.acceptance.awaiting_opinion")}`}
                    {(a.can_sign || a.can_give_opinion) && <span className="ml-1 text-amber-700">· {t("risk.acceptance.your_turn")}</span>}
                  </td>
                  <td className={`px-3 py-2 text-xs ${a.status === "active" && a.expires_on <= soon ? "text-amber-700 font-medium" : "text-gray-600"}`}>
                    {fmt(a.expires_on)}
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
