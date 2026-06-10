import { PROB_LABELS, IMPACT_LABELS } from "../../api/endpoints/risk";
import { matrixColor } from "./riskUtils";
import { useTranslation } from "react-i18next";

export function ProbImpactSelector({
  probability, impact, onChange,
}: {
  probability: number | null; impact: number | null;
  onChange: (field: "probability" | "impact", value: number) => void;
}) {
  const { t } = useTranslation();
  return (
    <div className="grid grid-cols-2 gap-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">{t("risk.probability_label")}</label>
        <div className="space-y-1">
          {[1,2,3,4,5].map(v => (
            <label key={v} className={`flex items-center gap-2 px-3 py-1.5 rounded cursor-pointer border text-sm transition-colors ${probability === v ? "border-primary-500 bg-primary-50 font-medium" : "border-gray-200 hover:border-gray-300"}`}>
              <input type="radio" name="probability" value={v} checked={probability === v} onChange={() => onChange("probability", v)} className="accent-primary-600" />
              {t(PROB_LABELS[v])}
            </label>
          ))}
        </div>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">{t("risk.impact_label")}</label>
        <div className="space-y-1">
          {[1,2,3,4,5].map(v => (
            <label key={v} className={`flex items-center gap-2 px-3 py-1.5 rounded cursor-pointer border text-sm transition-colors ${impact === v ? "border-primary-500 bg-primary-50 font-medium" : "border-gray-200 hover:border-gray-300"}`}>
              <input type="radio" name="impact" value={v} checked={impact === v} onChange={() => onChange("impact", v)} className="accent-primary-600" />
              {t(IMPACT_LABELS[v])}
            </label>
          ))}
        </div>
      </div>
      {probability && impact && (
        <div className="col-span-2">
          <div className={`rounded px-3 py-2 text-center text-sm font-semibold ${matrixColor(probability, impact)}`}>
            Score: {probability} × {impact} = {probability * impact}
          </div>
        </div>
      )}
    </div>
  );
}
