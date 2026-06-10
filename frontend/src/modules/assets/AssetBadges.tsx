import type { AssetIT, AssetOT, AssetSW } from "../../api/endpoints/assets";
import { useTranslation } from "react-i18next";
import i18n from "../../i18n";

export function CriticalityBadge({ value }: { value: number }) {
  const { t } = useTranslation();
  const colors: Record<number, string> = {
    1: "bg-green-100 text-green-800",
    2: "bg-green-100 text-green-700",
    3: "bg-yellow-100 text-yellow-800",
    4: "bg-orange-100 text-orange-800",
    5: "bg-red-100 text-red-800",
  };
  const labelKey = value >= 1 && value <= 5 ? `assets.criticality_${value}_label` : null;
  const descKey = value >= 1 && value <= 5 ? `assets.criticality_${value}_desc` : null;
  const lvl = {
    label: labelKey ? t(labelKey) : String(value),
    color: colors[value] ?? "bg-gray-100 text-gray-600",
    desc: descKey ? t(descKey) : "",
  };
  return (
    <div className="relative group inline-flex">
      <span
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded
                        text-xs font-medium cursor-help ${lvl.color}`}
      >
        {value} — {lvl.label}
      </span>
      {lvl.desc && (
        <div
          className="absolute bottom-full left-0 mb-1 w-60 bg-gray-900
                        text-white text-xs rounded p-2 shadow-lg
                        hidden group-hover:block z-50 pointer-events-none"
        >
          {lvl.desc}
        </div>
      )}
    </div>
  );
}

export function ChangeBadges({ asset }: { asset: AssetIT | AssetOT }) {
  const { t } = useTranslation();
  return (
    <>
      {asset.has_recent_change && (
        <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 border border-amber-300 ml-2">
          {t("assets.change_days_ago", { days: asset.change_age_days })}
        </span>
      )}
      {asset.needs_revaluation && (
        <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-700 border border-red-300 ml-2">
          {t("assets.reassessment_required")}
        </span>
      )}
    </>
  );
}

export const APPROVAL_STATUS_COLORS: Record<string, string> = {
  approvato: "bg-green-100 text-green-800",
  in_valutazione: "bg-yellow-100 text-yellow-800",
  deprecato: "bg-orange-100 text-orange-800",
  vietato: "bg-red-100 text-red-800",
};

export function EosBadge({ asset }: { asset: AssetSW }) {
  const { t } = useTranslation();
  if (!asset.end_of_support) return <span className="text-gray-400">—</span>;
  if (asset.is_eos) return (
    <span className="text-xs px-2 py-0.5 rounded bg-red-100 text-red-700 font-medium">
      {t("assets.sw.eos_expired")}
    </span>
  );
  if (asset.days_to_eos !== null && asset.days_to_eos <= 90) return (
    <span className="text-xs px-2 py-0.5 rounded bg-orange-100 text-orange-700 font-medium">
      {t("assets.sw.eos_in_days", { days: asset.days_to_eos })}
    </span>
  );
  return <span className="text-xs text-gray-500">{new Date(asset.end_of_support).toLocaleDateString(i18n.language || "it")}</span>;
}
