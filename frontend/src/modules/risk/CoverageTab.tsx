import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { apiError, riskApi, type AssetType, type CoveragePair } from "../../api/endpoints/risk";
import { RiskIntegratedRegisters } from "./RiskIntegratedRegisters";
import { ClassBadge, ErrorBox } from "./RiskUi";
import { ReasonDialog } from "./CycleBar";
import type { RegisterId } from "./RiskPage";

const STATE_TONE: Record<CoveragePair["state"], string> = {
  evaluated: "border-gray-200 bg-white",
  not_applicable: "border-gray-200 bg-gray-50 text-gray-400",
  draft: "border-yellow-300 bg-yellow-50",
  missing: "border-red-300 bg-red-50",
};

/** Copertura tipologie × minacce del catalogo (procedura §6.5). */
export function CoverageTab({ registerId, evaluating, onOpen, onEvaluate }: {
  registerId: RegisterId;
  evaluating: boolean;
  onOpen: (id: string) => void;
  onEvaluate: (assetType: AssetType, threat: string) => void;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [naPair, setNaPair] = useState<CoveragePair | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [onlyMissing, setOnlyMissing] = useState(false);
  const { data: coverage } = useQuery({
    queryKey: ["risk-coverage", registerId], queryFn: () => riskApi.coverage(registerId), retry: false,
  });
  const { data: threats = [] } = useQuery({ queryKey: ["risk-threats", "all"], queryFn: () => riskApi.threats(), retry: false });
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
                      : <span className="whitespace-nowrap">{t(`risk.coverage.states.${p.state}`)}</span>}
                  </div>
                  <div className="flex gap-3 mt-1">
                    {p.risk_ids.length > 0 && (
                      <button onClick={() => onOpen(p.risk_ids[0])} className="text-primary-600 hover:underline">{t("risk.coverage.open")}</button>
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
