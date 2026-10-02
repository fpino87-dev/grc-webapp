import { Fragment, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { riskApi, type Cycle, type Risk } from "../../api/endpoints/risk";
import type { RegisterId } from "./RiskPage";

/** Valutazioni del registro: cicli, approvazioni e valutazione precedente archiviata. */
export function CyclesTab({ registerId, cycles, onOpen }: {
  registerId: RegisterId; cycles: Cycle[]; onOpen: (riskId: string) => void;
}) {
  const { t, i18n } = useTranslation();
  const [showLegacy, setShowLegacy] = useState(false);
  const { data: legacy = [] } = useQuery({
    queryKey: ["risk-legacy", registerId],
    queryFn: () => riskApi.legacy(registerId!),
    enabled: showLegacy && !!registerId,
    retry: false,
  });
  const fmt = (d: string | null) => (d ? new Date(d).toLocaleDateString(i18n.language) : "—");
  const download = async (c: Cycle) => {
    const resp = await riskApi.exportCycle(c.id);
    const url = window.URL.createObjectURL(new Blob([resp.data]));
    const a = document.createElement("a");
    a.href = url;
    a.download = `valutazione_rischi_${c.plant_name ?? "gruppo"}_${(c.approved_at ?? "").slice(0, 10)}.xlsx`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

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
                <Fragment key={c.id}>
                <tr>
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
                  <td className="px-3 py-2 text-right whitespace-nowrap">
                    {c.approved_at && c.kind !== "legacy" && (
                      <button onClick={() => download(c)} className="text-xs text-green-700 hover:underline mr-3">
                        ⬇ {t("risk.cycles.export")}
                      </button>
                    )}
                    {c.kind === "legacy" && registerId && (
                      <button onClick={() => setShowLegacy(s => !s)} className="text-xs text-primary-600 hover:underline">
                        {t(showLegacy ? "risk.cycles.hide_legacy" : "risk.cycles.show_legacy")}
                      </button>
                    )}
                  </td>
                </tr>
                {c.kind === "legacy" && showLegacy && (
                  <tr>
                    <td colSpan={6} className="p-0">
                      <LegacyTable risks={legacy} onOpen={onOpen} />
                    </td>
                  </tr>
                )}
                </Fragment>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <p className="text-xs text-gray-500">{t("risk.cycles.hint")}</p>

    </div>
  );
}

/** Registro con il metodo superato: sola lettura, clic = scheda con i valori congelati. */
function LegacyTable({ risks, onOpen }: { risks: Risk[]; onOpen: (riskId: string) => void }) {
  const { t } = useTranslation();
  return (
    <div className="bg-amber-50/40 border-t border-amber-200">
      <p className="px-4 py-2 text-xs text-amber-800">{t("risk.legacy.hint")}</p>
      <table className="w-full text-sm">
        <thead className="border-y border-amber-200 text-xs text-gray-600">
          <tr>
            <th className="text-left px-3 py-2 font-medium">{t("risk.legacy.name")}</th>
            <th className="text-left px-3 py-2 font-medium">{t("risk.legacy.probability_impact")}</th>
            <th className="text-left px-3 py-2 font-medium">{t("risk.legacy.inherent_score")}</th>
            <th className="text-left px-3 py-2 font-medium">{t("risk.legacy.score")}</th>
            <th className="text-left px-3 py-2 font-medium">{t("risk.legacy.treatment")}</th>
            <th className="text-left px-3 py-2 font-medium">{t("risk.legacy.accepted")}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-amber-100 bg-white">
          {risks.map(r => {
            const s = r.legacy_snapshot as Record<string, string | number | boolean | null>;
            return (
              <tr key={r.id} onClick={() => onOpen(r.id)} className="cursor-pointer hover:bg-amber-50">
                <td className="px-3 py-2">{r.name}</td>
                <td className="px-3 py-2 text-xs">{`${s.probability ?? "—"} × ${s.impact ?? "—"}`}</td>
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
  );
}
