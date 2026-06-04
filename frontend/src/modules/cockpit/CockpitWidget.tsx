import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { cockpitApi, type CockpitInsight, type InsightSeverity } from "../../api/endpoints/cockpit";
import { useAuthStore } from "../../store/auth";

const SEV_DOT: Record<InsightSeverity, string> = {
  critical: "bg-red-500",
  warning: "bg-amber-400",
  info: "bg-sky-400",
};

function scoreColor(score: number): string {
  if (score >= 70) return "text-red-600";
  if (score >= 40) return "text-amber-600";
  if (score >= 15) return "text-yellow-600";
  return "text-green-600";
}

/** Widget Centro Operativo per la Dashboard: Posture Score + top 5 insight.
 *  Se l'utente non ha i permessi (403) o non ci sono dati, non renderizza nulla. */
export function CockpitWidget() {
  const { t } = useTranslation();
  const selectedPlant = useAuthStore(s => s.selectedPlant);

  const { data, isError } = useQuery({
    queryKey: ["cockpit-widget", selectedPlant?.id ?? null],
    queryFn: () => cockpitApi.insights(selectedPlant?.id),
    retry: false,
  });

  if (isError || !data) return null;

  const top: CockpitInsight[] = data.insights.slice(0, 5);

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 mb-6">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-700">🎛 {t("cockpit.title")}</h3>
        <Link to="/cockpit" className="text-xs text-primary-600 hover:underline">{t("cockpit.open")} →</Link>
      </div>
      <div className="flex items-center gap-5">
        <div className="text-center shrink-0">
          <div className={`text-3xl font-bold ${scoreColor(data.posture.total)}`}>{data.posture.total}</div>
          <div className="text-[10px] text-gray-500 uppercase">{t("cockpit.posture.score")}</div>
        </div>
        <div className="flex-1 min-w-0">
          {top.length === 0 ? (
            <p className="text-sm text-gray-400">✅ {t("cockpit.empty")}</p>
          ) : (
            <ul className="space-y-1">
              {top.map(i => (
                <li key={i.fingerprint} className="flex items-center gap-2 text-sm">
                  <span className={`w-2 h-2 rounded-full shrink-0 ${SEV_DOT[i.severity]}`} />
                  <span className="text-gray-700 truncate">
                    {t(`cockpit.insights.${i.code}.title`, { ...i.params, defaultValue: i.code })}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
