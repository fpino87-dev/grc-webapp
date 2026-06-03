import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { suppliersApi, type ConcentrationRiskItem } from "../../api/endpoints/suppliers";
import { biaApi, type ResilienceGapItem } from "../../api/endpoints/bia";

const LEVEL_BADGE: Record<string, string> = {
  medio: "bg-amber-100 text-amber-800",
  alto: "bg-orange-100 text-orange-800",
  critico: "bg-red-100 text-red-800",
};

function LevelBadge({ level }: { level: string }) {
  const { t } = useTranslation();
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${LEVEL_BADGE[level] ?? "bg-gray-100 text-gray-700"}`}>
      {t(`risk.registers.level.${level}`, level)}
    </span>
  );
}

/**
 * Registri rischi integrati (P2-4): vista di sola lettura nel dashboard rischi
 * delle catene di valore fornitura→risk (concentrazione) e BIA→BCP→risk
 * (resilienza). I dati arrivano dai service get_concentration_risk_register /
 * get_resilience_gap_register, plant-scoped.
 */
export function RiskIntegratedRegisters({ plantId }: { plantId?: string }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);

  const { data: conc } = useQuery({
    queryKey: ["concentration-risks", plantId],
    queryFn: () => suppliersApi.concentrationRisks(plantId),
    retry: false,
  });
  const { data: resil } = useQuery({
    queryKey: ["resilience-gaps", plantId],
    queryFn: () => biaApi.resilienceGaps(plantId),
    retry: false,
  });

  const concAttention = conc?.attention ?? 0;
  const resilAttention = resil?.attention ?? 0;
  const totalAttention = concAttention + resilAttention;
  const totalItems = (conc?.count ?? 0) + (resil?.count ?? 0);

  // Nessuna voce in nessuno dei due registri → non mostrare nulla (evita rumore).
  if (totalItems === 0) return null;

  return (
    <div className="mb-4 border border-gray-200 rounded-lg bg-white">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-3 text-left"
      >
        <span className="flex items-center gap-2 text-sm font-semibold text-gray-800">
          <span>🔗</span> {t("risk.registers.title")}
          {totalAttention > 0 && (
            <span className="inline-block px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
              {t("risk.registers.attention_count", { count: totalAttention })}
            </span>
          )}
        </span>
        <span className="text-gray-400 text-sm">{open ? "▾" : "▸"}</span>
      </button>

      {open && (
        <div className="px-4 pb-4 grid gap-4 md:grid-cols-2">
          {/* Concentrazione fornitura */}
          <section className="border border-gray-100 rounded p-3">
            <h4 className="text-sm font-semibold text-gray-700 mb-2">
              {t("risk.registers.concentration_title")}
              <span className="ml-2 text-xs font-normal text-gray-400">{conc?.count ?? 0}</span>
            </h4>
            <p className="text-xs text-gray-400 mb-2">{t("risk.registers.concentration_hint")}</p>
            {(conc?.items.length ?? 0) === 0 ? (
              <p className="text-xs text-gray-400">{t("risk.registers.empty")}</p>
            ) : (
              <ul className="space-y-1.5">
                {conc!.items.map((it: ConcentrationRiskItem) => (
                  <li key={it.supplier_id} className="flex items-center justify-between gap-2 text-sm">
                    <span className="truncate">
                      {it.supplier_name}
                      <span className="text-gray-400"> · {it.concentration_pct}%</span>
                      {it.nis2_relevant && <span className="ml-1 text-xs text-blue-600">NIS2</span>}
                    </span>
                    <LevelBadge level={it.risk_level} />
                  </li>
                ))}
              </ul>
            )}
          </section>

          {/* Resilienza BIA→BCP */}
          <section className="border border-gray-100 rounded p-3">
            <h4 className="text-sm font-semibold text-gray-700 mb-2">
              {t("risk.registers.resilience_title")}
              <span className="ml-2 text-xs font-normal text-gray-400">{resil?.count ?? 0}</span>
            </h4>
            <p className="text-xs text-gray-400 mb-2">{t("risk.registers.resilience_hint")}</p>
            {(resil?.items.length ?? 0) === 0 ? (
              <p className="text-xs text-gray-400">{t("risk.registers.empty")}</p>
            ) : (
              <ul className="space-y-1.5">
                {resil!.items.map((it: ResilienceGapItem) => (
                  <li key={it.process_id} className="flex items-center justify-between gap-2 text-sm">
                    <span className="truncate">
                      {it.process_name}
                      <span className="text-gray-400"> · {t("risk.registers.rto", { hours: it.rto_target_hours })}</span>
                      <span className="ml-1 text-xs text-gray-500">{t(`risk.registers.gap.${it.gap}`, it.gap)}</span>
                    </span>
                    <LevelBadge level={it.risk_level} />
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
