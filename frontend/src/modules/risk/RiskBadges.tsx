import type { RiskAssessment } from "../../api/endpoints/risk";
import { riskLevelFromScore, RISK_LEVEL_COLORS, RISK_LEVEL_ICONS, TREATMENT_BADGE, isActiveTreatment } from "./riskUtils";
import { useTranslation } from "react-i18next";
import i18n from "../../i18n";
import { usePlantToday } from "../../utils/dates";

export function RiskLevelBadge({ score }: { score: number | null }) {
  const { t } = useTranslation();
  if (score === null) return <span className="text-gray-400 text-xs">—</span>;
  const level = riskLevelFromScore(score);
  const cls = RISK_LEVEL_COLORS[level];
  const label = level === "rosso" ? t("risk.level_critical") : level === "giallo" ? t("eval_assistant.risk.zones.yellow.label") : t("eval_assistant.risk.zones.green.label");
  return <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${cls}`}>{score} — {label}</span>;
}

export function RiskInherentResidualBadges({ assessment }: { assessment: RiskAssessment }) {
  const { t } = useTranslation();
  if (!assessment.inherent_score && !assessment.score) return null;

  return (
    <div className="flex flex-wrap items-center gap-3 px-6 py-3 bg-gray-50 border-t border-gray-100">
      {assessment.inherent_score != null && (
        <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium ${RISK_LEVEL_COLORS[assessment.inherent_risk_level ?? "verde"]}`}>
          <span>{RISK_LEVEL_ICONS[assessment.inherent_risk_level ?? "verde"]}</span>
          <span>{t("risk.score_inherent", { score: assessment.inherent_score })}</span>
        </div>
      )}
      {assessment.inherent_score != null && assessment.score != null && (
        <span className="text-gray-400 text-sm">→</span>
      )}
      {assessment.score != null && (
        <div
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium ${RISK_LEVEL_COLORS[riskLevelFromScore(assessment.score)]}`}
        >
          <span>{RISK_LEVEL_ICONS[riskLevelFromScore(assessment.score)]}</span>
          <span>{t("risk.score_residual", { score: assessment.score })}</span>
        </div>
      )}
    </div>
  );
}

export function TreatmentDeadlineBadge({ assessment }: { assessment: RiskAssessment }) {
  const { t } = useTranslation();
  const { plan_due_date, treatment, mitigation_plans_count, mitigation_plans_completed, last_plan_completed_at } = assessment;

  const todayStr = usePlantToday();
  const isActive = isActiveTreatment(treatment);
  if (!plan_due_date) return <span className="text-gray-300 text-xs">—</span>;

  const overdue = plan_due_date < todayStr;
  const diffDays = Math.floor((new Date(plan_due_date).getTime() - new Date(todayStr).getTime()) / 86400000);
  const allDone = mitigation_plans_count > 0 && mitigation_plans_completed === mitigation_plans_count;
  const hasPlans = mitigation_plans_count > 0;

  let completionStatus: "on_time" | "late" | null = null;
  if (allDone && last_plan_completed_at) {
    const completedDate = last_plan_completed_at.slice(0, 10);
    completionStatus = completedDate <= plan_due_date ? "on_time" : "late";
  }

  const dateDisplay = new Date(plan_due_date + "T12:00:00").toLocaleDateString(i18n.language || "it");

  let deadlineColor = "bg-green-50 text-green-700 border-green-200";
  if (overdue && !allDone) deadlineColor = "bg-red-50 text-red-700 border-red-200";
  else if (!overdue && diffDays <= 30 && !allDone) deadlineColor = "bg-amber-50 text-amber-700 border-amber-200";

  return (
    <div className="space-y-1.5">
      <div className={`inline-flex items-center gap-1 px-2 py-1 rounded border text-xs font-medium ${deadlineColor}`}>
        <span>📅</span>
        <span>{dateDisplay}</span>
        {overdue && !allDone && (
          <span className="ml-1 px-1.5 py-0.5 rounded-full bg-red-100 text-red-700 text-[10px] font-semibold">
            {t("risk.plan_due_date_overdue")}
          </span>
        )}
        {!overdue && diffDays <= 30 && !allDone && (
          <span className="ml-1 px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700 text-[10px] font-semibold">
            {t("risk.plan_due_date_soon")}
          </span>
        )}
      </div>

      {isActive && hasPlans && (
        <div className="text-xs">
          {completionStatus === "on_time" && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-100 text-green-700 font-medium">
              ✓ {t("risk.mitigation_on_time")}
            </span>
          )}
          {completionStatus === "late" && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-orange-100 text-orange-700 font-medium">
              ⚠ {t("risk.mitigation_late")}
            </span>
          )}
          {!completionStatus && (
            <span className="text-gray-500">
              {t("risk.mitigation_progress", { completed: mitigation_plans_completed, total: mitigation_plans_count })}
            </span>
          )}
        </div>
      )}

      {isActive && !hasPlans && (
        <div className="text-[10px] text-gray-400">{t("risk.mitigation_no_plans")}</div>
      )}
    </div>
  );
}

export function EffectiveStatusBadge({ assessment: a }: { assessment: RiskAssessment }) {
  const { t } = useTranslation();

  const isActive = isActiveTreatment(a.treatment);
  const allPlansDone = a.mitigation_plans_count > 0 && a.mitigation_plans_completed === a.mitigation_plans_count;
  const hasPlans = a.mitigation_plans_count > 0;
  const isVerde = a.risk_level === "verde" || (a.score !== null && riskLevelFromScore(a.score) === "verde");

  let label: string;
  let cls: string;

  if (a.status === "archiviato") {
    label = t("risk.eff_status.archiviato");
    cls = "bg-gray-100 text-gray-600";
  } else if (a.risk_accepted_formally) {
    if (isActive && !allPlansDone) {
      label = t("risk.eff_status.accettato_azioni_in_corso");
      cls = "bg-amber-100 text-amber-700";
    } else {
      label = t("risk.eff_status.completato");
      cls = "bg-green-100 text-green-800";
    }
  } else if (a.status === "completato" && isActive) {
    if (!hasPlans) {
      label = t("risk.eff_status.da_pianificare");
      cls = "bg-orange-100 text-orange-700";
    } else if (allPlansDone) {
      // Verde: si chiude senza accettazione formale
      if (isVerde) {
        label = t("risk.eff_status.completato");
        cls = "bg-green-100 text-green-800";
      } else {
        label = t("risk.eff_status.in_accettazione");
        cls = "bg-teal-100 text-teal-700";
      }
    } else {
      label = t("risk.eff_status.in_trattamento", { done: a.mitigation_plans_completed, total: a.mitigation_plans_count });
      cls = "bg-blue-100 text-blue-700";
    }
  } else if (a.status === "completato" && (a.treatment === "accettare" || a.treatment === "evitare")) {
    // Verde: completato senza accettazione formale
    if (isVerde) {
      label = t("risk.eff_status.completato");
      cls = "bg-green-100 text-green-800";
    } else {
      label = t("risk.eff_status.in_accettazione");
      cls = "bg-amber-100 text-amber-700";
    }
  } else if (a.status === "completato") {
    label = t("risk.eff_status.valutato");
    cls = "bg-blue-100 text-blue-700";
  } else {
    label = t("risk.eff_status.in_valutazione");
    cls = "bg-gray-100 text-gray-500";
  }

  return (
    <div className="space-y-1.5">
      {a.treatment && (
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${TREATMENT_BADGE[a.treatment] ?? "bg-gray-100 text-gray-600"}`}>
          {t(`risk.treatment_${a.treatment}`)}
        </span>
      )}
      <div className="flex items-center gap-1.5 flex-wrap">
        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${cls}`}>
          {label}
        </span>
        {a.needs_revaluation && (
          <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-semibold bg-amber-100 text-amber-700">
            ⚠ {t("risk.eff_status.rivalutare")}
          </span>
        )}
      </div>
      {(label === t("risk.eff_status.in_accettazione") || label === t("risk.eff_status.accettato_azioni_in_corso")) && !a.risk_accepted_formally && !isVerde && (
        <p className="text-[10px] text-gray-400 mt-0.5">▼ {t("risk.eff_status.hint_accettazione")}</p>
      )}
    </div>
  );
}
