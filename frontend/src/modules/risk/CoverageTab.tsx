import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { apiError, riskApi, type AssetType, type CoveragePair } from "../../api/endpoints/risk";
import { RiskIntegratedRegisters } from "./RiskIntegratedRegisters";
import { ClassBadge, ErrorBox } from "./RiskUi";
import { ReasonDialog } from "./CycleBar";
import type { RegisterId } from "./RiskPage";
import { classBadge } from "./riskClasses";

const STATE_TONE: Record<CoveragePair["state"], string> = {
  evaluated: "border-gray-200 bg-white",
  not_applicable: "border-gray-200 bg-gray-50 text-gray-400",
  draft: "border-yellow-300 bg-yellow-50",
  missing: "border-red-300 bg-red-50",
  inherited: "border-blue-200 bg-blue-50",
};

/** Copertura tipologie × minacce del catalogo (procedura §6.5). */
export function CoverageTab({ registerId, evaluating, onOpen, onEvaluate }: {
  registerId: RegisterId;
  evaluating: boolean;
  onOpen: (id: string) => void;
  onEvaluate: (assetType: AssetType, threat: string) => void;
}) {
  const { t, i18n } = useTranslation();
  const qc = useQueryClient();
  const [naPair, setNaPair] = useState<CoveragePair | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [onlyMissing, setOnlyMissing] = useState(false);
  const { data: coverage } = useQuery({
    queryKey: ["risk-coverage", registerId], queryFn: () => riskApi.coverage(registerId), retry: false,
  });
  const { data: threats = [] } = useQuery({ queryKey: ["risk-threats", "all", i18n.language], queryFn: () => riskApi.threats(), retry: false });
  const titles = new Map(threats.map(th => [th.id, th.title]));
  const markNa = useMutation({
    mutationFn: (reason: string) => riskApi.notApplicable(registerId, naPair!.asset_type, naPair!.threat_id, reason),
    onSuccess: () => {
      setNaPair(null); setError(null);
      qc.invalidateQueries({ queryKey: ["risk-coverage", registerId] });
      qc.invalidateQueries({ queryKey: ["risk-register"] });
    },
    onError: e => setError(apiError(e, t("risk.errors.generic"))),
  });

  if (!coverage) return <p className="text-sm text-gray-400">{t("common.loading")}</p>;

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex items-center justify-between text-sm mb-2">
          <span className="font-medium">{t("risk.coverage.progress", { closed: coverage.closed, total: coverage.total, pct: coverage.pct })}</span>
          <label className="flex items-center gap-1 text-xs text-gray-600">
            <input type="checkbox" checked={onlyMissing} onChange={e => setOnlyMissing(e.target.checked)} /> {t("risk.coverage.only_missing")}
          </label>
        </div>
        <div className="h-2 rounded bg-gray-100 overflow-hidden">
          <div className="h-2 bg-green-500" style={{ width: `${coverage.pct}%` }} />
        </div>
        <p className="text-[11px] text-gray-400 mt-2">{t("risk.coverage.hint")}</p>
      </div>

      {coverage.asset_types.map(type => {
        const pairs = coverage.pairs.filter(p => p.asset_type === type && (!onlyMissing || p.state === "missing" || p.state === "draft"));
        if (!pairs.length) return null;
        return (
          <div key={type} className="bg-white rounded-lg border border-gray-200 p-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-2">{t(`risk.asset_types.${type}`)}</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-2">
              {pairs.map(p => (
                <div key={p.threat_id} className={`border rounded px-2 py-1.5 text-xs ${STATE_TONE[p.state]}`}>
                  <div className="flex items-start justify-between gap-2">
                    <span className="truncate" title={titles.get(p.threat_id)}>
                      <span className="font-mono text-gray-500 mr-1">{p.threat_code}</span>{titles.get(p.threat_id)}
                    </span>
                    {p.state === "evaluated" ? <ClassBadge cls={p.worst_class} size="xs" />
                      : p.state === "inherited" ? (
                        <span className="flex items-center gap-1 whitespace-nowrap text-blue-700">
                          ⇩ {t("risk.coverage.states.inherited")}
                          {p.worst_class && <ClassBadge cls={p.worst_class} size="xs" />}
                        </span>
                      )
                      : <span className="whitespace-nowrap">{t(`risk.coverage.states.${p.state}`)}</span>}
                  </div>
                  <div className="flex gap-3 mt-1">
                    {p.risk_ids.length > 0 && (
                      <button onClick={() => onOpen(p.risk_ids[0])} className="text-primary-600 hover:underline">{t("risk.coverage.open")}</button>
                    )}
                    {p.state === "inherited" && evaluating && (
                      <button onClick={() => onEvaluate(type, p.threat_id)} className="text-gray-600 hover:underline"
                        title={t("risk.coverage.add_site_risk_hint")}>{t("risk.coverage.add_site_risk")}</button>
                    )}
                    {p.state === "missing" && evaluating && (
                      <>
                        <button onClick={() => onEvaluate(type, p.threat_id)} className="text-primary-600 hover:underline">{t("risk.coverage.evaluate")}</button>
                        <button onClick={() => setNaPair(p)} className="text-gray-600 hover:underline">{t("risk.coverage.not_applicable")}</button>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })}

      <InformationCoverage registerId={registerId} onOpen={onOpen} />

      {registerId && <RiskIntegratedRegisters plantId={registerId} />}

      {naPair && (
        <ReasonDialog
          title={t("risk.coverage.not_applicable_title", { code: naPair.threat_code })}
          label={t("risk.coverage.not_applicable_reason")}
          error={error}
          onClose={() => { setNaPair(null); setError(null); }}
          onConfirm={reason => markNa.mutate(reason)}
        />
      )}
      <ErrorBox message={naPair ? null : error} />
    </div>
  );
}

/** Classi di informazioni Confidenziali/Segrete e rischi di riservatezza che le
 *  coprono (VDA ISA 1.3.1/1.3.2): una classe scoperta è un buco della valutazione. */
function InformationCoverage({ registerId, onOpen }: { registerId: RegisterId; onOpen: (id: string) => void }) {
  const { t } = useTranslation();
  const { data: rows = [] } = useQuery({
    queryKey: ["risk-register", registerId, "information-coverage"],
    queryFn: () => riskApi.informationCoverage(registerId),
    retry: false,
  });
  if (!rows.length) return null;
  const missing = rows.filter(r => r.state === "missing").length;
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <h4 className="text-sm font-semibold text-gray-700">{t("risk.information_coverage.title")}</h4>
      <p className="text-[11px] text-gray-500 mb-2">{t("risk.information_coverage.hint")}</p>
      {missing > 0 && <p className="text-xs text-red-700 mb-2">{t("risk.information_coverage.missing", { count: missing })}</p>}
      <div className="divide-y divide-gray-100">
        {rows.map(r => (
          <div key={r.id} className="flex flex-wrap items-center gap-2 py-1.5 text-sm">
            <span className="flex-1 min-w-0 truncate">{r.name}</span>
            <span className="text-[11px] text-gray-500">{t(`risk.confidentiality_levels.${r.confidentiality}`)}</span>
            <span className={`text-[11px] px-2 py-0.5 rounded ${
              r.state === "evaluated" ? "bg-green-50 text-green-700" : r.state === "draft" ? "bg-amber-50 text-amber-700" : "bg-red-50 text-red-700"}`}>
              {t(`risk.information_coverage.states.${r.state}`)}
            </span>
            {r.worst_class && (
              <span className={`text-[11px] px-1.5 rounded border ${classBadge(r.worst_class)}`}>{t(`risk.classes.${r.worst_class}`)}</span>
            )}
            {r.risk_ids[0] && (
              <button onClick={() => onOpen(r.risk_ids[0])} className="text-xs text-primary-600 hover:underline">{t("risk.information_coverage.open")}</button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
