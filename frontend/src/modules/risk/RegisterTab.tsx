import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { ASSET_TYPES, riskApi, type Risk } from "../../api/endpoints/risk";
import { RISK_CLASSES, classRank } from "./riskClasses";
import { ClassTransition } from "./RiskUi";
import type { RegisterId } from "./RiskPage";

/** Riga di stato compatta (regola UX: niente testi lunghi negli elenchi). */
function StatusLine({ r }: { r: Risk }) {
  const { t } = useTranslation();
  if (!r.applicable) return <span className="text-xs text-gray-400">{t("risk.register.not_applicable")}</span>;
  const parts: string[] = [];
  parts.push(t(r.status === "completato" ? "risk.register.status_done" : "risk.register.status_draft"));
  if (r.mitigation_plans_count) {
    parts.push(t("risk.register.plans_progress", {
      done: r.mitigation_plans_completed, total: r.mitigation_plans_count, verified: r.mitigation_plans_verified,
    }));
  }
  if (r.active_acceptance) {
    parts.push(t(r.active_acceptance.status === "active" ? "risk.register.accepted" : "risk.register.acceptance_pending"));
  }
  return <span className="text-xs text-gray-500">{parts.join(" · ")}</span>;
}

export function RegisterTab({ registerId, onOpen }: { registerId: RegisterId; onOpen: (id: string) => void }) {
  const { t } = useTranslation();
  const [assetType, setAssetType] = useState("");
  const [cls, setCls] = useState("");
  const [treatment, setTreatment] = useState("");
  const [onlyOpen, setOnlyOpen] = useState(false);
  const [showNa, setShowNa] = useState(false);
  const [inherited, setInherited] = useState(true);
  const [q, setQ] = useState("");

  const { data: risks = [], isLoading } = useQuery({
    queryKey: ["risk-register", registerId, inherited],
    queryFn: () => riskApi.list(registerId, registerId && inherited ? { include_inherited: "1" } : {}),
    retry: false,
  });

  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return risks
      .filter(r => showNa || r.applicable)
      .filter(r => !assetType || r.asset_type === assetType)
      .filter(r => !cls || r.current_class === cls)
      .filter(r => !treatment || r.treatment === treatment)
      .filter(r => !onlyOpen || r.status !== "completato"
        || (r.current_class && ["high", "critical"].includes(r.current_class) && r.active_acceptance?.status !== "active"))
      .filter(r => !needle || [r.name, r.threat_code, r.threat_title, r.asset_name, r.owner_name]
        .some(v => (v ?? "").toLowerCase().includes(needle)))
      .sort((a, b) => classRank(b.current_class) - classRank(a.current_class) || a.name.localeCompare(b.name));
  }, [risks, assetType, cls, treatment, onlyOpen, showNa, q]);

  return (
    <div>
      <div className="flex flex-wrap items-center gap-2 mb-3 text-sm">
        <input value={q} onChange={e => setQ(e.target.value)} placeholder={t("risk.register.search")}
          className="border rounded px-2 py-1.5 w-56" />
        <select value={assetType} onChange={e => setAssetType(e.target.value)} className="border rounded px-2 py-1.5">
          <option value="">{t("risk.register.all_asset_types")}</option>
          {ASSET_TYPES.map(a => <option key={a} value={a}>{t(`risk.asset_types.${a}`)}</option>)}
        </select>
        <select value={cls} onChange={e => setCls(e.target.value)} className="border rounded px-2 py-1.5">
          <option value="">{t("risk.register.all_classes")}</option>
          {[...RISK_CLASSES].reverse().map(c => <option key={c} value={c}>{t(`risk.classes.${c}`)}</option>)}
        </select>
        <select value={treatment} onChange={e => setTreatment(e.target.value)} className="border rounded px-2 py-1.5">
          <option value="">{t("risk.register.all_treatments")}</option>
          {["mitigare", "trasferire", "evitare", "accettare"].map(x => <option key={x} value={x}>{t(`risk.treatment_${x}`)}</option>)}
        </select>
        <label className="flex items-center gap-1 text-xs text-gray-600">
          <input type="checkbox" checked={onlyOpen} onChange={e => setOnlyOpen(e.target.checked)} /> {t("risk.register.only_open")}
        </label>
        <label className="flex items-center gap-1 text-xs text-gray-600">
          <input type="checkbox" checked={showNa} onChange={e => setShowNa(e.target.checked)} /> {t("risk.register.show_na")}
        </label>
        {registerId && (
          <label className="flex items-center gap-1 text-xs text-gray-600">
            <input type="checkbox" checked={inherited} onChange={e => setInherited(e.target.checked)} /> {t("risk.register.show_inherited")}
          </label>
        )}
        <span className="ml-auto text-xs text-gray-400">{t("risk.register.count", { count: rows.length })}</span>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? (
          <p className="p-8 text-center text-gray-400 text-sm">{t("common.loading")}</p>
        ) : rows.length === 0 ? (
          <p className="p-8 text-center text-gray-400 text-sm">{t("risk.register.empty")}</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200 text-xs text-gray-600">
              <tr>
                <th className="text-left px-3 py-2 font-medium">{t("risk.register.col_threat")}</th>
                <th className="text-left px-3 py-2 font-medium">{t("risk.register.col_scenario")}</th>
                <th className="text-left px-3 py-2 font-medium">{t("risk.register.col_owner")}</th>
                <th className="text-left px-3 py-2 font-medium">{t("risk.register.col_class")}</th>
                <th className="text-left px-3 py-2 font-medium">{t("risk.register.col_treatment")}</th>
                <th className="text-left px-3 py-2 font-medium">{t("risk.register.col_status")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {rows.map(r => (
                <tr key={r.id} data-row-id={r.id} onClick={() => onOpen(r.id)}
                  className={`cursor-pointer hover:bg-gray-50 ${!r.applicable ? "opacity-60" : ""}`}>
                  <td className="px-3 py-2 align-top">
                    <span className="font-mono text-xs text-gray-700" title={r.threat_title ?? ""}>{r.threat_code ?? "—"}</span>
                    <div className="text-[11px] text-gray-400">{r.asset_type ? t(`risk.asset_types.${r.asset_type}`) : ""}</div>
                  </td>
                  <td className="px-3 py-2 align-top">
                    <div className="font-medium text-gray-800 truncate max-w-md" title={r.name}>
                      {r.is_inherited && <span className="mr-1" title={t("risk.register.inherited_hint")}>⇩</span>}
                      {r.name}
                    </div>
                    <div className="text-xs text-gray-400 truncate max-w-md">
                      {[r.asset_name || r.asset_group_label, r.supplier_name, r.critical_process_name].filter(Boolean).join(" · ")}
                    </div>
                  </td>
                  <td className="px-3 py-2 align-top text-xs text-gray-600">{r.owner_name ?? <span className="text-amber-600">—</span>}</td>
                  <td className="px-3 py-2 align-top">
                    {r.applicable ? <ClassTransition current={r.current_class} expected={r.expected_class} /> : "—"}
                  </td>
                  <td className="px-3 py-2 align-top text-xs text-gray-600">
                    {r.treatment ? t(`risk.treatment_${r.treatment}`) : "—"}
                  </td>
                  <td className="px-3 py-2 align-top"><StatusLine r={r} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
