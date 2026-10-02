import { Fragment, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { riskApi } from "../../api/endpoints/risk";
import { RISK_CLASSES, classBadge } from "./riskClasses";
import type { RegisterId } from "./RiskPage";

/** Rischi per obiettivo aziendale (procedura §2): mostra che la valutazione
 *  parte dagli obiettivi. Clic su una riga = elenco dei rischi, clic su un
 *  rischio = scheda. */
export function ObjectivesTab({ registerId, onOpen }: { registerId: RegisterId; onOpen: (id: string) => void }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState<string | null>(null);
  const { data: rows = [], isLoading } = useQuery({
    queryKey: ["risk-register", registerId, "objectives"],
    queryFn: () => riskApi.objectives(registerId),
    retry: false,
  });
  const { data: risks = [] } = useQuery({
    queryKey: ["risk-register", registerId, true],
    queryFn: () => riskApi.list(registerId, registerId ? { include_inherited: "1" } : {}),
    retry: false,
  });
  const byId = new Map(risks.map(r => [r.id, r]));

  return (
    <div className="space-y-2">
      <p className="text-xs text-gray-500">{t("risk.objectives.hint")}</p>
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? <p className="p-6 text-center text-sm text-gray-400">{t("common.loading")}</p> : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b text-xs text-gray-600">
              <tr>
                <th className="text-left px-3 py-2 font-medium">{t("risk.objectives.col_objective")}</th>
                <th className="text-left px-3 py-2 font-medium">{t("risk.objectives.col_risks")}</th>
                <th className="text-left px-3 py-2 font-medium">{t("risk.objectives.col_worst")}</th>
                <th className="text-left px-3 py-2 font-medium">{t("risk.objectives.col_untreated")}</th>
                <th className="text-left px-3 py-2 font-medium">{t("risk.objectives.col_distribution")}</th>
                {registerId && <th className="text-left px-3 py-2 font-medium" title={t("risk.objectives.col_inherited_hint")}>{t("risk.objectives.col_inherited")}</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {rows.filter(r => r.objective || r.count || r.inherited_count).map(r => {
                const key = r.objective?.id ?? "none";
                return (
                  <Fragment key={key}>
                    <tr onClick={() => (r.count || r.inherited_count) && setOpen(open === key ? null : key)}
                      className={r.count || r.inherited_count ? "cursor-pointer hover:bg-gray-50" : ""}>
                      <td className="px-3 py-2">
                        {r.objective ? r.objective.name : <span className="text-amber-700">{t("risk.objectives.none")}</span>}
                        {r.objective && (
                          <span className="block text-[11px] text-gray-400">
                            {r.objective.impact_dimensions.map(d => t(`risk.dimensions.${d}`)).join(" · ")}
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2">{r.count}</td>
                      <td className="px-3 py-2">
                        {r.worst_class
                          ? <span className={`text-xs px-2 py-0.5 rounded border ${classBadge(r.worst_class)}`}>{t(`risk.classes.${r.worst_class}`)}</span>
                          : <span className="text-xs text-gray-400">—</span>}
                      </td>
                      <td className={`px-3 py-2 ${r.untreated_high ? "text-red-700 font-semibold" : "text-gray-500"}`}>{r.untreated_high}</td>
                      <td className="px-3 py-2 text-xs text-gray-500">
                        {[...RISK_CLASSES].reverse().filter(c => r.by_class[c]).map(c => `${t(`risk.classes.${c}`)} ${r.by_class[c]}`).join(" · ") || "—"}
                      </td>
                      {registerId && (
                        <td className="px-3 py-2 text-xs text-blue-700">
                          {r.inherited_count ? `⇩ ${r.inherited_count}${r.inherited_untreated_high ? ` (${r.inherited_untreated_high} High/Critical)` : ""}` : "—"}
                        </td>
                      )}
                    </tr>
                    {open === key && (
                      <tr>
                        <td colSpan={6} className="bg-gray-50 px-6 py-2">
                          <ul className="space-y-1">
                            {[...r.risk_ids, ...r.inherited_risk_ids].map(id => {
                              const risk = byId.get(id);
                              return (
                                <li key={id}>
                                  <button onClick={() => onOpen(id)} className="text-left text-sm hover:underline">
                                    {r.inherited_risk_ids.includes(id) && <span className="text-blue-700 mr-1">⇩</span>}
                                    <span className="font-mono text-xs text-gray-500 mr-1">{risk?.threat_code}</span>
                                    {risk?.display_name ?? id}
                                    {risk?.current_class && (
                                      <span className={`ml-2 text-[11px] px-1.5 rounded border ${classBadge(risk.current_class)}`}>
                                        {t(`risk.classes.${risk.current_class}`)}
                                      </span>
                                    )}
                                  </button>
                                </li>
                              );
                            })}
                          </ul>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
