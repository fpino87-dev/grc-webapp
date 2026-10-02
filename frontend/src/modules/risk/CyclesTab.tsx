import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { riskApi, type Cycle } from "../../api/endpoints/risk";
import type { RegisterId } from "./RiskPage";

/** Valutazioni del registro: cicli, approvazioni e valutazione precedente archiviata. */
export function CyclesTab({ registerId, cycles }: { registerId: RegisterId; cycles: Cycle[] }) {
  const { t, i18n } = useTranslation();
  const [showLegacy, setShowLegacy] = useState(false);
  const { data: legacy = [] } = useQuery({
    queryKey: ["risk-legacy", registerId],
    queryFn: () => riskApi.legacy(registerId!),
    enabled: showLegacy && !!registerId,
    retry: false,
  });
  const fmt = (d: string | null) => (d ? new Date(d).toLocaleDateString(i18n.language) : "—");

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {cycles.length === 0 ? <p className="p-6 text-center text-sm text-gray-400">{t("risk.cycles.empty")}</p> : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b text-xs text-gray-600">
              <tr>
                <th className="text-left px-3 py-2 font-medium">{t("risk.cycles.col_kind")}</th>
                <th className="text-left px-3 py-2 font-medium">{t("risk.cycles.col_status")}</th>
                <th className="text-left px-3 py-2 font-medium">{t("risk.cycles.col_started")}</th>
                <th className="text-left px-3 py-2 font-medium">{t("risk.cycles.col_approved")}</th>
                <th className="text-left px-3 py-2 font-medium">{t("risk.cycles.col_risks")}</th>
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {cycles.map(c => (
                <tr key={c.id}>
                  <td className="px-3 py-2">
                    {t(`risk.cycle.kinds.${c.kind}`)}
                    {c.trigger_reason && <span className="block text-[11px] text-gray-400 truncate max-w-xs" title={c.trigger_reason}>{c.trigger_reason}</span>}
                  </td>
                  <td className="px-3 py-2 text-xs">{t(`risk.cycles.status.${c.status}`)}</td>
                  <td className="px-3 py-2 text-xs text-gray-600">{fmt(c.started_at)}</td>
                  <td className="px-3 py-2 text-xs text-gray-600">
                    {c.approved_at ? `${fmt(c.approved_at)} · ${c.approved_by_body_name ?? ""}` : "—"}
                    {c.local_adoption_ref && <span className="block text-[11px] text-gray-400">{c.local_adoption_ref}</span>}
                  </td>
                  <td className="px-3 py-2 text-xs text-gray-600">{c.risks_count}</td>
                  <td className="px-3 py-2 text-right">
                    {c.kind === "legacy" && registerId && (
                      <button onClick={() => setShowLegacy(s => !s)} className="text-xs text-primary-600 hover:underline">
                        {t(showLegacy ? "risk.cycles.hide_legacy" : "risk.cycles.show_legacy")}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <p className="text-xs text-gray-500">{t("risk.cycles.hint")}</p>

      {showLegacy && (
        <div className="bg-white rounded-lg border border-amber-200 overflow-hidden">
          <p className="px-4 py-2 text-xs bg-amber-50 text-amber-800">{t("risk.legacy.hint")}</p>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b text-xs text-gray-600">
              <tr>
                <th className="text-left px-3 py-2 font-medium">{t("risk.legacy.name")}</th>
                <th className="text-left px-3 py-2 font-medium">{t("risk.legacy.inherent_score")}</th>
                <th className="text-left px-3 py-2 font-medium">{t("risk.legacy.score")}</th>
                <th className="text-left px-3 py-2 font-medium">{t("risk.legacy.treatment")}</th>
                <th className="text-left px-3 py-2 font-medium">{t("risk.legacy.accepted")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {legacy.map(r => {
                const s = r.legacy_snapshot as Record<string, string | number | boolean | null>;
                return (
                  <tr key={r.id}>
                    <td className="px-3 py-2">{r.name}</td>
                    <td className="px-3 py-2 text-xs">{s.inherent_score ?? "—"}</td>
                    <td className="px-3 py-2 text-xs">{s.score ?? "—"}</td>
                    <td className="px-3 py-2 text-xs">{s.treatment ? t(`risk.treatment_${s.treatment}`) : "—"}</td>
                    <td className="px-3 py-2 text-xs">{s.risk_accepted_formally ? t("common.yes") : t("common.no")}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
