import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { riskApi } from "../../api/endpoints/risk";
import { CLASS_CELL, RISK_CLASSES, riskClass } from "./riskClasses";
import { ClassTransition } from "./RiskUi";
import type { RegisterId } from "./RiskPage";

/** Matrice 5×5 della procedura con i conteggi, rischio attuale o atteso. */
export function MatrixTab({ registerId, onOpen }: { registerId: RegisterId; onOpen: (id: string) => void }) {
  const { t } = useTranslation();
  const [view, setView] = useState<"current" | "expected">("current");
  const [cell, setCell] = useState<{ p: number; i: number } | null>(null);
  const { data: cells = [] } = useQuery({
    queryKey: ["risk-matrix", registerId, view],
    queryFn: () => riskApi.matrix(registerId, view),
    retry: false,
  });
  const { data: risks = [] } = useQuery({
    queryKey: ["risk-register", registerId, true],
    queryFn: () => riskApi.list(registerId, registerId ? { include_inherited: "1" } : {}),
    retry: false,
  });
  const count = (p: number, i: number) => cells.find(c => c.probability === p && c.impact === i)?.count ?? 0;
  const inCell = cell
    ? risks.filter(r => r.applicable && r.status === "completato"
      && (view === "current" ? r.probability === cell.p && r.impact === cell.i
        : r.expected_probability === cell.p && r.expected_impact === cell.i))
    : [];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="bg-white rounded-lg border border-gray-200 p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-gray-700">{t("risk.matrix.title")}</h3>
          <div className="inline-flex rounded border overflow-hidden text-xs">
            {(["current", "expected"] as const).map(v => (
              <button key={v} onClick={() => { setView(v); setCell(null); }}
                className={`px-2.5 py-1 ${view === v ? "bg-primary-600 text-white" : "bg-white text-gray-600"}`}>
                {t(`risk.matrix.${v}`)}
              </button>
            ))}
          </div>
        </div>
        <p className="text-xs text-gray-400 mb-1">{t("risk.matrix.probability")} ↑</p>
        {[5, 4, 3, 2, 1].map(p => (
          <div key={p} className="flex gap-1 mb-1 items-center">
            <span className="text-xs text-gray-400 w-4 text-right">{p}</span>
            {[1, 2, 3, 4, 5].map(i => {
              const n = count(p, i);
              const cls = riskClass(p, i)!;
              const selected = cell?.p === p && cell?.i === i;
              return (
                <button key={i} type="button" onClick={() => setCell(n ? { p, i } : null)}
                  title={`${t(`risk.classes.${cls}`)} · ${n}`}
                  className={`w-12 h-12 rounded text-sm font-bold ${CLASS_CELL[cls]} ${n ? "" : "opacity-30"} ${selected ? "ring-2 ring-offset-1 ring-gray-800" : ""}`}>
                  {n || ""}
                </button>
              );
            })}
          </div>
        ))}
        <div className="flex gap-1 mt-1 ml-5">
          {[1, 2, 3, 4, 5].map(i => <div key={i} className="w-12 text-center text-xs text-gray-400">{i}</div>)}
        </div>
        <p className="ml-5 mt-1 text-xs text-gray-400">{t("risk.matrix.impact")} →</p>
        <div className="flex flex-wrap gap-3 mt-3 text-xs text-gray-600">
          {[...RISK_CLASSES].reverse().map(c => (
            <span key={c} className="flex items-center gap-1"><span className={`w-3 h-3 rounded ${CLASS_CELL[c]}`} />{t(`risk.classes.${c}`)}</span>
          ))}
        </div>
        <p className="text-[11px] text-gray-400 mt-2">{t("risk.matrix.note")}</p>
      </div>
      <div className="bg-white rounded-lg border border-gray-200 p-5">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">
          {cell ? t("risk.matrix.cell_title", { p: cell.p, i: cell.i }) : t("risk.matrix.pick_cell")}
        </h3>
        <ul className="divide-y">
          {inCell.map(r => (
            <li key={r.id} className="py-2 flex items-center justify-between gap-2 cursor-pointer hover:bg-gray-50" onClick={() => onOpen(r.id)}>
              <span className="text-sm">
                <span className="font-mono text-xs text-gray-500 mr-1">{r.threat_code}</span>{r.display_name}
              </span>
              <ClassTransition current={r.current_class} expected={r.expected_class} />
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
