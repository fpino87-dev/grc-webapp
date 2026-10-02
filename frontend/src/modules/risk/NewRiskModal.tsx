import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { ASSET_TYPES, apiError, riskApi, type AssetType } from "../../api/endpoints/risk";
import { ErrorBox, inputCls } from "./RiskUi";
import { Modal } from "./CycleBar";
import type { RegisterId } from "./RiskPage";

export interface NewRiskPrefill {
  asset_type?: AssetType;
  threat?: string;
  critical_process?: string;
}

/** Nuovo rischio dal catalogo minacce; la valutazione si completa nella scheda. */
export function NewRiskModal({ registerId, plants, prefill, onClose, onCreated }: {
  registerId: RegisterId;
  plants: { id: string; code: string; name: string }[];
  prefill: NewRiskPrefill;
  onClose: () => void;
  onCreated: (id: string) => void;
}) {
  const { t, i18n } = useTranslation();
  const [assetType, setAssetType] = useState<AssetType | "">(prefill.asset_type ?? "");
  const [threat, setThreat] = useState(prefill.threat ?? "");
  const [name, setName] = useState("");
  const [q, setQ] = useState("");
  const [affected, setAffected] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const { data: coverage } = useQuery({
    queryKey: ["risk-coverage", registerId],
    queryFn: () => riskApi.coverage(registerId),
    retry: false,
  });
  const { data: threats = [] } = useQuery({
    queryKey: ["risk-threats", assetType, i18n.language],
    queryFn: () => riskApi.threats({ asset_type: assetType }),
    enabled: !!assetType,
    retry: false,
  });

  const states = useMemo(() => new Map(
    (coverage?.pairs ?? []).filter(p => p.asset_type === assetType).map(p => [p.threat_id, p.state]),
  ), [coverage, assetType]);
  const filtered = threats.filter(th => !q || `${th.code} ${th.title}`.toLowerCase().includes(q.toLowerCase()));
  const types = coverage?.asset_types.length ? coverage.asset_types : ASSET_TYPES;

  const create = useMutation({
    mutationFn: () => riskApi.create({
      plant: registerId, asset_type: assetType as AssetType, threat, name: name.trim() || undefined,
      critical_process: prefill.critical_process ?? null,
      ...(registerId === null ? { affected_plants: affected } : {}),
    }),
    onSuccess: risk => onCreated(risk.id),
    onError: e => setError(apiError(e, t("risk.errors.generic"))),
  });

  return (
    <Modal title={t("risk.new.title")} onClose={onClose}>
      <div className="text-sm space-y-3">
        <div>
          <p className="text-xs font-medium text-gray-600 mb-1">1. {t("risk.new.asset_type")}</p>
          <div className="flex flex-wrap gap-1.5">
            {types.map(a => (
              <button key={a} type="button" onClick={() => { setAssetType(a); setThreat(""); }}
                className={`px-2.5 py-1 rounded border text-xs ${assetType === a ? "bg-primary-600 text-white border-primary-600" : "hover:bg-gray-50"}`}>
                {t(`risk.asset_types.${a}`)}
              </button>
            ))}
          </div>
        </div>
        {assetType && (
          <div>
            <p className="text-xs font-medium text-gray-600 mb-1">2. {t("risk.new.threat")}</p>
            <input value={q} onChange={e => setQ(e.target.value)} placeholder={t("risk.new.search_threat")} className={`${inputCls} mb-1`} />
            <div className="max-h-56 overflow-y-auto border rounded divide-y">
              {filtered.map(th => {
                const state = states.get(th.id);
                return (
                  <label key={th.id} className={`flex items-start gap-2 px-2 py-1.5 cursor-pointer ${threat === th.id ? "bg-primary-50" : "hover:bg-gray-50"}`}>
                    <input type="radio" checked={threat === th.id} onChange={() => setThreat(th.id)} className="mt-0.5" />
                    <span className="flex-1">
                      <span className="font-mono text-xs text-gray-500 mr-1">{th.code}</span>{th.title}
                    </span>
                    {state && state !== "missing" && (
                      <span className="text-[11px] text-gray-400">{t(`risk.coverage.states.${state}`)}</span>
                    )}
                  </label>
                );
              })}
            </div>
          </div>
        )}
        {threat && (
          <div>
            <p className="text-xs font-medium text-gray-600 mb-1">3. {t("risk.new.name")}</p>
            <input value={name} onChange={e => setName(e.target.value)} className={inputCls}
              placeholder={threats.find(th => th.id === threat)?.title} />
            {registerId === null && (
              <div className="mt-2">
                <p className="text-xs font-medium text-gray-600 mb-1">{t("risk.new.affected_plants")}</p>
                <div className="flex flex-wrap gap-2">
                  {plants.map(p => (
                    <label key={p.id} className="flex items-center gap-1 text-xs">
                      <input type="checkbox" checked={affected.includes(p.id)}
                        onChange={e => setAffected(e.target.checked ? [...affected, p.id] : affected.filter(x => x !== p.id))} />
                      {p.code}
                    </label>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
        <ErrorBox message={error} />
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-3 py-1.5 border rounded">{t("common.cancel")}</button>
          <button onClick={() => create.mutate()} disabled={!assetType || !threat || create.isPending}
            className="px-3 py-1.5 bg-primary-600 text-white rounded disabled:opacity-50">{t("risk.new.create")}</button>
        </div>
      </div>
    </Modal>
  );
}
