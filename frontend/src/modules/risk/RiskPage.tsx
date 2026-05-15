import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useLocation } from "react-router-dom";
import { apiClient } from "../../api/client";
import { scrollAndHighlight } from "../../lib/scrollAndHighlight";
import { riskApi, type RiskAssessment, type RiskMitigationPlan, type SuggestResidualResult, THREAT_CATEGORIES, PROB_LABELS, IMPACT_LABELS, NIS2_ART21_CHOICES, NIS2_RELEVANCE_CHOICES } from "../../api/endpoints/risk";
import { plantsApi } from "../../api/endpoints/plants";
import { biaApi, type CriticalProcess } from "../../api/endpoints/bia";
import { usersApi, type GrcUser } from "../../api/endpoints/users";
import { useAuthStore } from "../../store/auth";
import { bcpApi, type BcpPlan } from "../../api/endpoints/bcp";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { AssistenteValutazione } from "../../components/ui/AssistenteValutazione";
import { ModuleHelp } from "../../components/ui/ModuleHelp";
import { RiskContinuityWizard } from "./RiskContinuityWizard";
import { useTranslation } from "react-i18next";
import i18n from "../../i18n";

function matrixColor(p: number, i: number): string {
  const s = p * i;
  // Allineamento con la logica backend di RiskAssessment.risk_level:
  // - <= 7 verde
  // - <= 14 giallo
  // - > 14 rosso
  if (s <= 7) return "bg-green-100 text-green-800";
  if (s <= 14) return "bg-yellow-100 text-yellow-800";
  return "bg-red-100 text-red-800";
}

function RiskLevelBadge({ score }: { score: number | null }) {
  const { t } = useTranslation();
  if (score === null) return <span className="text-gray-400 text-xs">—</span>;
  // Allineamento con il backend (RiskAssessment.risk_level):
  // - <= 7 verde
  // - <= 14 giallo
  // - > 14 rosso
  const cls = score > 14 ? "bg-red-100 text-red-800" : score > 7 ? "bg-yellow-100 text-yellow-800" : "bg-green-100 text-green-800";
  const label = score > 14 ? t("risk.level_critical") : score > 7 ? t("eval_assistant.risk.zones.yellow.label") : t("eval_assistant.risk.zones.green.label");
  return <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${cls}`}>{score} — {label}</span>;
}

function formatAle(ale: string | null) {
  if (!ale) return "—";
  const n = parseFloat(ale);
  return isNaN(n) ? ale : new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(n);
}

function ProbImpactSelector({
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
              {PROB_LABELS[v]}
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
              {IMPACT_LABELS[v]}
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

const RISK_LEVEL_COLORS: Record<string, string> = {
  verde:  "bg-green-100 text-green-800",
  giallo: "bg-yellow-100 text-yellow-800",
  rosso:  "bg-red-100 text-red-800",
};
const RISK_LEVEL_ICONS: Record<string, string> = {
  verde: "🟢", giallo: "🟡", rosso: "🔴",
};

function RiskInherentResidualBadges({ assessment }: { assessment: RiskAssessment }) {
  const { t } = useTranslation();
  if (!assessment.inherent_score && !assessment.score) return null;

  function riskLevelFromScore(score: number): "verde" | "giallo" | "rosso" {
    if (score <= 7) return "verde";
    if (score <= 14) return "giallo";
    return "rosso";
  }

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

function TreatmentDeadlineBadge({ assessment }: { assessment: RiskAssessment }) {
  const { t } = useTranslation();
  const { plan_due_date, treatment, mitigation_plans_count, mitigation_plans_completed, last_plan_completed_at } = assessment;

  const isActiveTreatment = treatment === "mitigare" || treatment === "trasferire";
  if (!plan_due_date) return <span className="text-gray-300 text-xs">—</span>;

  const todayStr = new Date().toISOString().slice(0, 10);
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

      {isActiveTreatment && hasPlans && (
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

      {isActiveTreatment && !hasPlans && (
        <div className="text-[10px] text-gray-400">{t("risk.mitigation_no_plans")}</div>
      )}
    </div>
  );
}

const TREATMENT_BADGE: Record<string, string> = {
  mitigare:   "bg-blue-100 text-blue-800",
  trasferire: "bg-purple-100 text-purple-800",
  accettare:  "bg-yellow-100 text-yellow-800",
  evitare:    "bg-gray-100 text-gray-700",
};

function EffectiveStatusBadge({ assessment: a }: { assessment: RiskAssessment }) {
  const { t } = useTranslation();

  const isActive = a.treatment === "mitigare" || a.treatment === "trasferire";
  const allPlansDone = a.mitigation_plans_count > 0 && a.mitigation_plans_completed === a.mitigation_plans_count;
  const hasPlans = a.mitigation_plans_count > 0;
  const isVerde = a.risk_level === "verde" || (a.score !== null && a.score <= 7);

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

function SuggestResidualPanel({ assessment }: { assessment: RiskAssessment }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [suggestion, setSuggestion] = useState<SuggestResidualResult | null>(null);

  const { refetch, isFetching } = useQuery({
    queryKey: ["suggest-residual", assessment.id],
    queryFn: () => riskApi.suggestResidual(assessment.id),
    enabled: false,
  });

  async function handleSuggest() {
    const { data } = await refetch();
    if (data) setSuggestion(data);
  }

  return (
    <div className="px-6 py-3 border-t border-gray-100">
      <div className="flex items-center gap-3">
        <button
          onClick={handleSuggest}
          disabled={isFetching}
          className="text-xs px-3 py-1.5 border border-indigo-300 text-indigo-600 rounded hover:bg-indigo-50 disabled:opacity-50"
        >
          {isFetching ? t("common.loading") : t("risk.suggest_residual")}
        </button>
        {suggestion && (
          <span className="text-xs text-gray-600">{suggestion.reason}</span>
        )}
      </div>
      {suggestion && (
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <span className="text-xs text-green-700 bg-green-50 border border-green-200 px-2 py-1 rounded">
            {t("risk.controls_reduction")} {suggestion.reduction_pct ?? 0}%
          </span>
          <span className="text-xs text-green-800 bg-green-50 border border-green-200 px-2 py-1 rounded">
            {t("risk.bcp_extra")} {suggestion.bcp_extra_pct ?? 0}%
          </span>
          <span className="text-xs text-gray-700 bg-gray-50 border border-gray-200 px-2 py-1 rounded">
            {t("risk.total_label")} {Math.min(70, (suggestion.reduction_pct ?? 0) + (suggestion.bcp_extra_pct ?? 0))}%
          </span>
          <span className="text-xs text-gray-500">
            (Il suggeritore ricalcola da `inerente` usando controlli `compliant` e BCP validi: se risultano 0 o scaduti, la riduzione suggerita può differire dal valore attuale.)
          </span>
        </div>
      )}
    </div>
  );
}

function FormalAcceptancePanel({ assessment }: { assessment: RiskAssessment }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [renewOpen, setRenewOpen] = useState(false);
  const [note, setNote] = useState("");
  // Default: +1 anno da oggi (ISO 27001 — revisione annuale accettazione rischio)
  const defaultExpiry = new Date(new Date().setFullYear(new Date().getFullYear() + 1)).toISOString().slice(0, 10);
  const [expiry, setExpiry] = useState(defaultExpiry);
  const [renewExpiry, setRenewExpiry] = useState(defaultExpiry);
  const [err, setErr] = useState("");

  const mutation = useMutation({
    mutationFn: () => riskApi.acceptRisk(assessment.id, note, expiry || undefined),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["risk-assessments"] }); setOpen(false); },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { error?: string } } })?.response?.data?.error ?? t("risk.error_generic");
      setErr(msg);
    },
  });

  const renewMutation = useMutation({
    mutationFn: () => riskApi.renewAcceptance(assessment.id, renewExpiry),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["risk-assessments"] }); setRenewOpen(false); },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { error?: string } } })?.response?.data?.error ?? t("risk.error_generic");
      setErr(msg);
    },
  });

  const resetMutation = useMutation({
    mutationFn: () => riskApi.resetAcceptance(assessment.id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["risk-assessments"] }); },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { error?: string } } })?.response?.data?.error ?? t("risk.error_generic");
      setErr(msg);
    },
  });

  if (assessment.risk_level === "verde" && !assessment.risk_accepted_formally) return null;

  if (assessment.risk_accepted_formally) {
    const expiryStr = assessment.risk_acceptance_expiry ?? null;
    const todayStr = new Date().toISOString().slice(0, 10);
    const expired = expiryStr ? expiryStr < todayStr : false;
    const expiryDisplay = expiryStr ? new Date(expiryStr + "T12:00:00").toLocaleDateString(i18n.language || "it") : null;
    return (
      <div className="px-6 py-3 border-t border-gray-100 space-y-2">
        <div className={`flex items-center gap-2 text-xs px-3 py-2 rounded-lg ${expired ? "bg-red-50 text-red-700" : "bg-green-50 text-green-700"}`}>
          <span>{expired ? "⚠️" : "✅"}</span>
          <span>
            {t("risk.accepted_by_on", { name: assessment.accepted_by_name ?? "—", date: assessment.risk_accepted_at ? new Date(assessment.risk_accepted_at).toLocaleDateString(i18n.language || "it") : "—" })}
            {expiryDisplay && <> — {expired ? t("risk.expired_on") : t("risk.expires_on")} <strong>{expiryDisplay}</strong></>}
          </span>
        </div>
        {assessment.risk_acceptance_note && (
          <p className="text-xs text-gray-500 italic px-1">"{assessment.risk_acceptance_note}"</p>
        )}
        <div className="flex gap-2 flex-wrap">
          {!renewOpen ? (
            <button onClick={() => setRenewOpen(true)}
              className="text-xs px-3 py-1.5 border border-blue-300 text-blue-700 rounded hover:bg-blue-50">
              {t("risk.renew_acceptance")}
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <input type="date" value={renewExpiry} min={todayStr}
                onChange={e => setRenewExpiry(e.target.value)}
                className="border rounded px-2 py-1 text-xs" />
              <button onClick={() => renewMutation.mutate()} disabled={renewMutation.isPending}
                className="text-xs px-3 py-1.5 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
                {renewMutation.isPending ? t("common.saving") : t("risk.renew_confirm")}
              </button>
              <button onClick={() => setRenewOpen(false)} className="text-xs px-2 py-1.5 border rounded text-gray-600 hover:bg-gray-50">
                {t("actions.cancel")}
              </button>
            </div>
          )}
          <button
            onClick={() => { if (window.confirm(t("risk.reset_acceptance_confirm"))) resetMutation.mutate(); }}
            disabled={resetMutation.isPending}
            className="text-xs px-3 py-1.5 border border-orange-300 text-orange-700 rounded hover:bg-orange-50 disabled:opacity-50">
            {t("risk.reset_acceptance")}
          </button>
        </div>
        {err && <p className="text-xs text-red-600">⛔ {err}</p>}
      </div>
    );
  }

  return (
    <div className="px-6 py-3 border-t border-gray-100">
      {!open ? (
        <button
          onClick={() => setOpen(true)}
          className="text-xs px-3 py-1.5 border border-yellow-300 text-yellow-700 rounded hover:bg-yellow-50"
        >
          {t("risk.accept_risk_prompt")}
        </button>
      ) : (
        <div className="space-y-2 max-w-lg">
          <p className="text-xs font-medium text-gray-700">{t("risk.accept_risk_title")}</p>
          <textarea
            value={note}
            onChange={e => { setNote(e.target.value); setErr(""); }}
            placeholder={`${t("risk.accept_note_label")}${assessment.risk_level === "rosso" ? ` ${t("risk.accept_note_critical_hint")}` : ""}`}
            className="w-full border rounded px-2 py-1.5 text-xs resize-none"
            rows={3}
          />
          <input
            type="date"
            value={expiry}
            onChange={e => setExpiry(e.target.value)}
            className="border rounded px-2 py-1.5 text-xs w-full"
            placeholder={t("risk.acceptance_expiry_placeholder")}
          />
          {err && <p className="text-xs text-red-600">⛔ {err}</p>}
          <div className="flex gap-2">
            <button
              onClick={() => mutation.mutate()}
              disabled={mutation.isPending}
              className="px-3 py-1.5 bg-yellow-600 text-white text-xs rounded hover:bg-yellow-700 disabled:opacity-50"
            >
              {mutation.isPending ? t("common.saving") : t("risk.confirm_acceptance")}
            </button>
            <button onClick={() => setOpen(false)} className="px-3 py-1.5 border rounded text-xs text-gray-600 hover:bg-gray-50">
              {t("actions.cancel")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function MitigationPanel({ assessmentId }: { assessmentId: string }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<Partial<RiskMitigationPlan>>({});
  const [editPlan, setEditPlan] = useState<RiskMitigationPlan | null>(null);
  const [editForm, setEditForm] = useState<Partial<RiskMitigationPlan>>({});
  const selectedPlant = useAuthStore(s => s.selectedPlant);

  const { data: riskContext } = useQuery({
    queryKey: ["risk-context", assessmentId],
    queryFn: () => riskApi.context(assessmentId),
  });

  const { data: plans = [] } = useQuery({
    queryKey: ["mitigation-plans", assessmentId],
    queryFn: () => riskApi.mitigationPlans(assessmentId),
  });

  const todayStr = new Date().toISOString().slice(0, 10);

  // Preferiamo i BCP "coerenti" trovati dal contesto (cioè legati al processo BIA del risk).
  // Se sono vuoti (es. risk senza critical_process collegato o BCP non legato al processo),
  // facciamo fallback mostrando i BCP del sito corrente.
  const contextBcpPlans = (riskContext?.bcp_plans ?? []) as Array<{
    id: string;
    title: string;
    status: string;
    last_test_date?: string | null;
    next_test_date?: string | null;
  }>;

  const { data: bcpFallbackResp } = useQuery({
    queryKey: ["bcp-fallback", selectedPlant?.id],
    queryFn: () => bcpApi.list(selectedPlant?.id ? { plant: selectedPlant.id } : {}),
    enabled: !!selectedPlant?.id,
    retry: false,
  });

  const fallbackBcpPlans = (bcpFallbackResp?.results ?? []) as BcpPlan[];

  const availableBcpPlans = contextBcpPlans.length ? contextBcpPlans : fallbackBcpPlans;
  const selectedBcpPlan =
    availableBcpPlans.find(p => p.id === (form.bcp_plan ?? "")) ?? null;

  const createMutation = useMutation({
    mutationFn: () => riskApi.createPlan({ ...form, assessment: assessmentId }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["mitigation-plans", assessmentId] }); setShowForm(false); setForm({}); },
  });

  const completeMutation = useMutation({
    mutationFn: (id: string) => riskApi.completePlan(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mitigation-plans", assessmentId] }),
  });

  const uncompleteMutation = useMutation({
    mutationFn: (id: string) => riskApi.uncompletePlan(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mitigation-plans", assessmentId] }),
  });

  const deletePlanMutation = useMutation({
    mutationFn: (id: string) => riskApi.deletePlan(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mitigation-plans", assessmentId] }),
  });

  const updateMutation = useMutation({
    mutationFn: () => {
      if (!editPlan) return Promise.reject(new Error("No plan selected"));
      return riskApi.updatePlan(editPlan.id, editForm);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mitigation-plans", assessmentId] });
      setEditPlan(null);
      setEditForm({});
    },
  });

  return (
    <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-gray-700">Piani di mitigazione ({plans.length})</h4>
        <button onClick={() => setShowForm(s => !s)} className="text-xs px-2 py-1 bg-primary-600 text-white rounded hover:bg-primary-700">
          + Aggiungi piano
        </button>
      </div>

      {showForm && (
        <div className="bg-white border border-gray-200 rounded p-3 mb-3 space-y-2">
          <textarea
            placeholder={t("risk.action_desc_placeholder")}
            value={form.action ?? ""}
            onChange={e => setForm(p => ({ ...p, action: e.target.value }))}
            className="w-full border rounded px-2 py-1.5 text-sm" rows={2}
          />
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Collega a un BCP (opzionale)</label>
            <select
              value={form.bcp_plan ?? ""}
              onChange={e => {
                const id = e.target.value || null;
                const chosen = availableBcpPlans.find(p => p.id === id) ?? null;
                setForm(prev => ({
                  ...prev,
                  bcp_plan: id,
                  // Coerenza: per la mitigazione usiamo la "data dell'ultimo test valido".
                  due_date: chosen?.last_test_date ?? prev.due_date,
                }));
              }}
              className="w-full border rounded px-2 py-1.5 text-sm"
            >
              <option value="">— Nessun BCP —</option>
              {availableBcpPlans.map(p => (
                <option key={p.id} value={p.id}>
                  {p.title} · {p.status} · valido fino {p.next_test_date ?? "—"}
                </option>
              ))}
            </select>
          </div>
          <div className="flex gap-2">
            <input
              type="date"
              placeholder={t("risk.bcp_test_date_placeholder")}
              value={form.due_date ?? ""}
              onChange={e => setForm(p => ({ ...p, due_date: e.target.value }))}
              disabled={!!selectedBcpPlan?.last_test_date}
              className="border rounded px-2 py-1.5 text-sm flex-1 disabled:bg-gray-50"
            />
            <button onClick={() => createMutation.mutate()} disabled={createMutation.isPending || !form.action || !form.due_date}
              className="px-3 py-1.5 bg-primary-600 text-white text-xs rounded hover:bg-primary-700 disabled:opacity-50">{t("actions.save")}</button>
            <button onClick={() => setShowForm(false)} className="px-3 py-1.5 border rounded text-xs text-gray-600 hover:bg-gray-50">{t("actions.cancel")}</button>
          </div>
        </div>
      )}

      {editPlan && (
        <div className="bg-white border border-gray-200 rounded p-3 mb-3 space-y-2">
          <textarea
            placeholder={t("risk.action_desc_placeholder")}
            value={editForm.action ?? editPlan.action ?? ""}
            onChange={e => setEditForm(p => ({ ...p, action: e.target.value }))}
            className="w-full border rounded px-2 py-1.5 text-sm" rows={2}
          />
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Collega a un BCP (opzionale)</label>
            <select
              value={editForm.bcp_plan ?? editPlan.bcp_plan ?? ""}
              onChange={e => {
                const id = e.target.value || null;
                const chosen = availableBcpPlans.find(p => p.id === id) ?? null;
                setEditForm(prev => ({
                  ...prev,
                  bcp_plan: id,
                  due_date: chosen?.last_test_date ?? prev.due_date,
                }));
              }}
              className="w-full border rounded px-2 py-1.5 text-sm"
            >
              <option value="">— Nessun BCP —</option>
              {availableBcpPlans.map(p => (
                <option key={p.id} value={p.id}>
                  {p.title} · {p.status} · valido fino {p.next_test_date ?? "—"}
                </option>
              ))}
            </select>
          </div>
          <div className="flex gap-2">
            <input
              type="date"
              placeholder={t("risk.bcp_test_date_placeholder")}
              value={editForm.due_date ?? editPlan.due_date ?? ""}
              onChange={e => setEditForm(p => ({ ...p, due_date: e.target.value }))}
              disabled={!!(availableBcpPlans.find(p => p.id === (editForm.bcp_plan ?? editPlan.bcp_plan))?.last_test_date)}
              className="border rounded px-2 py-1.5 text-sm flex-1 disabled:bg-gray-50"
            />
            <button
              onClick={() => updateMutation.mutate()}
              disabled={updateMutation.isPending || !((editForm.action ?? editPlan.action) && (editForm.due_date ?? editPlan.due_date))}
              className="px-3 py-1.5 bg-primary-600 text-white text-xs rounded hover:bg-primary-700 disabled:opacity-50"
            >
              {updateMutation.isPending ? t("common.saving") : t("actions.save")}
            </button>
            <button onClick={() => { setEditPlan(null); setEditForm({}); }} className="px-3 py-1.5 border rounded text-xs text-gray-600 hover:bg-gray-50">
              {t("actions.cancel")}
            </button>
          </div>
        </div>
      )}

      {plans.length === 0 ? (
        <p className="text-xs text-gray-400">Nessun piano di mitigazione registrato</p>
      ) : (
        <div className="space-y-2">
          {plans.map(plan => (
            (() => {
              const bcpValid =
                plan.bcp_plan_next_test_date
                  ? plan.bcp_plan_next_test_date >= todayStr
                  : plan.due_date >= todayStr;
              const isDone = !!plan.completed_at;
              const dotColor = isDone ? "bg-green-500" : (bcpValid ? "bg-green-400" : "bg-orange-400");
              return (
            <div key={plan.id} className="flex items-center gap-3 bg-white rounded border border-gray-200 px-3 py-2 text-sm">
              <span className={`w-2 h-2 rounded-full shrink-0 ${dotColor}`} />
              <span className="flex-1 text-gray-700">{plan.action}</span>
              <span className="text-xs text-gray-400 shrink-0">
                <div className="space-y-1">
                  <div>
                    Ultimo test: {plan.due_date ? new Date(plan.due_date + "T12:00:00").toLocaleDateString(i18n.language || "it") : "—"}
                  </div>
                  <div>
                    {plan.bcp_plan_next_test_date
                      ? `Prossimo test: ${new Date(plan.bcp_plan_next_test_date + "T12:00:00").toLocaleDateString(i18n.language || "it")}`
                      : "Prossimo test: — (collega un BCP)"}
                  </div>
                </div>
              </span>
              <span className="shrink-0 flex items-center gap-2">
                <button
                  onClick={() => {
                    setEditPlan(plan);
                    setEditForm({
                      action: plan.action,
                      due_date: plan.due_date,
                      bcp_plan: plan.bcp_plan ?? null,
                    });
                  }}
                  className="text-xs text-purple-700 border border-purple-300 rounded px-2 py-0.5 hover:bg-purple-50 whitespace-nowrap"
                >
                  {t("actions.edit")}
                </button>
                <button
                  onClick={() => {
                    if (window.confirm(t("risk.plan_delete_confirm"))) deletePlanMutation.mutate(plan.id);
                  }}
                  disabled={deletePlanMutation.isPending}
                  title={t("actions.delete")}
                  className="text-gray-400 hover:text-red-600 hover:bg-red-50 rounded p-0.5 transition-colors disabled:opacity-50"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                </button>
              </span>
              {!plan.completed_at ? (
                <button onClick={() => completeMutation.mutate(plan.id)} disabled={completeMutation.isPending} className="text-xs text-green-700 border border-green-300 rounded px-2 py-0.5 hover:bg-green-50 disabled:opacity-50 shrink-0">
                  {t("risk.plan_complete_btn")}
                </button>
              ) : (
                <button
                  onClick={() => { if (window.confirm(t("risk.plan_uncomplete_confirm"))) uncompleteMutation.mutate(plan.id); }}
                  disabled={uncompleteMutation.isPending}
                  title={t("risk.plan_uncomplete_label")}
                  className="text-xs text-green-600 border border-green-200 rounded px-2 py-0.5 hover:bg-orange-50 hover:text-orange-600 hover:border-orange-300 transition-colors shrink-0"
                >
                  ✓ {t("risk.plan_completed_label")}
                </button>
              )}
            </div>
              );
            })()
          ))}
        </div>
      )}
    </div>
  );
}

function NewAssessmentModal({ plants, onClose }: { plants: { id: string; code: string; name: string }[]; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const selectedPlant = useAuthStore(s => s.selectedPlant);
  const [form, setForm] = useState<Partial<RiskAssessment>>({
    assessment_type: "IT",
    probability: null,
    impact: null,
    plant: selectedPlant?.id ?? "",
  });
  const [error, setError] = useState("");

  const plantId = form.plant;

  const { data: processes } = useQuery({
    queryKey: ["bia-processes", plantId],
    queryFn: () => biaApi.list(plantId ? { plant: plantId, page_size: "200" } : {}),
    enabled: !!plantId,
    retry: false,
  });

  const { data: users } = useQuery({
    queryKey: ["users"],
    queryFn: () => usersApi.list(),
    retry: false,
  });

  const mutation = useMutation({
    mutationFn: () => riskApi.create(form),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["risk-assessments"] }); onClose(); },
    onError: (e: any) => setError(e?.response?.data?.detail || JSON.stringify(e?.response?.data) || t("risk.error_generic")),
  });

  function set(field: string, value: unknown) { setForm(f => ({ ...f, [field]: value })); }

  const canSave = !!form.plant && !!form.name && !!form.probability && !!form.impact;

  const selectedProcess = processes?.results?.find(p => p.id === form.critical_process);

  // Estimate ALE locally for display (probability × impact × downtime_cost_hour)
  function estimateAle(): string | null {
    if (!selectedProcess?.downtime_cost_hour) return null;
    if (!form.probability || !form.impact) return null;
    const oreMap: Record<number, number> = {1:1, 2:4, 3:24, 4:72, 5:168};
    const probMap: Record<number, number> = {1:0.1, 2:0.3, 3:1.0, 4:3.0, 5:10.0};
    const ore = oreMap[form.impact] ?? 24;
    const prob = probMap[form.probability] ?? 1.0;
    let ale = parseFloat(selectedProcess.downtime_cost_hour) * ore * prob;
    if (selectedProcess.danno_reputazionale >= 4) ale *= 1.3;
    if (selectedProcess.danno_normativo >= 4) ale *= 1.2;
    return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(ale);
  }

  const alePreview = estimateAle();

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl flex flex-col max-h-[92vh]">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 shrink-0">
          <h3 className="text-lg font-semibold">Nuovo scenario di rischio</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl w-8 h-8 flex items-center justify-center rounded hover:bg-gray-100">×</button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nome scenario / rischio *</label>
            <input value={form.name ?? ""} onChange={e => set("name", e.target.value)}
              placeholder={t("risk.scenario_placeholder")}
              className="w-full border rounded px-3 py-2 text-sm" />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("risk.cause_label")}</label>
              <textarea value={form.cause ?? ""} onChange={e => set("cause", e.target.value)}
                rows={2} placeholder={t("risk.cause_placeholder")}
                className="w-full border rounded px-3 py-2 text-sm resize-none" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("risk.consequence_label")}</label>
              <textarea value={form.consequence ?? ""} onChange={e => set("consequence", e.target.value)}
                rows={2} placeholder={t("risk.consequence_placeholder")}
                className="w-full border rounded px-3 py-2 text-sm resize-none" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Sito *</label>
              <select value={form.plant ?? ""} onChange={e => { set("plant", e.target.value); set("critical_process", null); }} className="w-full border rounded px-3 py-2 text-sm">
                <option value="">— seleziona —</option>
                {plants.map(p => <option key={p.id} value={p.id}>{p.code} — {p.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Categoria minaccia</label>
              <select value={form.threat_category ?? ""} onChange={e => set("threat_category", e.target.value)} className="w-full border rounded px-3 py-2 text-sm">
                <option value="">— seleziona —</option>
                {THREAT_CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tipo asset</label>
              <div className="flex gap-4 mt-1">
                {(["IT", "OT"] as const).map(t => (
                  <label key={t} className="flex items-center gap-2 cursor-pointer">
                    <input type="radio" name="assessment_type" value={t} checked={form.assessment_type === t} onChange={() => set("assessment_type", t)} className="accent-primary-600" />
                    <span className="text-sm font-medium">{t}</span>
                  </label>
                ))}
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Trattamento previsto</label>
              <select value={form.treatment ?? ""} onChange={e => set("treatment", e.target.value)} className="w-full border rounded px-3 py-2 text-sm">
                <option value="">{t("common.select")}</option>
                <option value="mitigare">{t("risk.treatment_mitigare")}</option>
                <option value="accettare">{t("risk.treatment_accettare")}</option>
                <option value="trasferire">{t("risk.treatment_trasferire_ext")}</option>
                <option value="evitare">{t("risk.treatment_evitare")}</option>
              </select>
            </div>
          </div>

          {/* Scadenza piano di trattamento */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("risk.plan_due_date_label")}</label>
            <input
              type="date"
              value={form.plan_due_date ?? ""}
              onChange={e => set("plan_due_date", e.target.value || null)}
              className="w-full border rounded px-3 py-2 text-sm"
            />
            <p className="text-xs text-gray-500 mt-1">{t("risk.plan_due_date_help")}</p>
          </div>

          {/* Owner rischio */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Owner rischio</label>
            <select value={form.owner ?? ""} onChange={e => set("owner", e.target.value || null)} className="w-full border rounded px-3 py-2 text-sm">
              <option value="">— nessun owner —</option>
              {users?.map(u => (
                <option key={u.id} value={u.id}>
                  {u.first_name || u.last_name ? `${u.first_name} ${u.last_name}`.trim() : u.username} ({u.email})
                </option>
              ))}
            </select>
          </div>

          {/* Processo BIA collegato */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Processo BIA collegato (opzionale)</label>
            <select
              value={form.critical_process ?? ""}
              onChange={e => set("critical_process", e.target.value || null)}
              disabled={!plantId}
              className="w-full border rounded px-3 py-2 text-sm disabled:bg-gray-50"
            >
              <option value="">— nessun processo BIA —</option>
              {processes?.results?.map(p => (
                <option key={p.id} value={p.id}>
                  {p.name} [criticità {p.criticality}]
                </option>
              ))}
            </select>
            {selectedProcess && (
              <div className="mt-1.5 px-3 py-2 bg-blue-50 rounded text-xs text-blue-700 flex gap-3">
                <span>Costo orario fermo: <strong>{selectedProcess.downtime_cost_hour ? new Intl.NumberFormat("it-IT", {style:"currency",currency:"EUR"}).format(parseFloat(selectedProcess.downtime_cost_hour)) : "—"}</strong></span>
                <span>Criticità: <strong>{selectedProcess.criticality}</strong>/5</span>
              </div>
            )}
          </div>

          {/* P × I inerente (prima dei controlli) */}
          <div className="border border-orange-200 rounded-lg p-4 bg-orange-50/30">
            <p className="text-sm font-medium text-orange-800 mb-1">Rischio inerente (prima dei controlli)</p>
            <p className="text-xs text-orange-600 mb-3">Valuta il rischio come se non esistessero controlli di sicurezza</p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Probabilità inerente</label>
                <select
                  value={form.inherent_probability ?? ""}
                  onChange={e => set("inherent_probability", e.target.value ? Number(e.target.value) : null)}
                  className="w-full border rounded px-2 py-1.5 text-sm"
                >
                  <option value="">— seleziona —</option>
                  {[1,2,3,4,5].map(v => <option key={v} value={v}>{PROB_LABELS[v]}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Impatto inerente</label>
                <select
                  value={form.inherent_impact ?? ""}
                  onChange={e => set("inherent_impact", e.target.value ? Number(e.target.value) : null)}
                  className="w-full border rounded px-2 py-1.5 text-sm"
                >
                  <option value="">— seleziona —</option>
                  {[1,2,3,4,5].map(v => <option key={v} value={v}>{IMPACT_LABELS[v]}</option>)}
                </select>
              </div>
              {form.inherent_probability && form.inherent_impact && (
                <div className="col-span-2">
                  <div className={`rounded px-3 py-2 text-center text-sm font-semibold ${matrixColor(form.inherent_probability, form.inherent_impact)}`}>
                    Score inerente: {form.inherent_probability} × {form.inherent_impact} = {form.inherent_probability * form.inherent_impact}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* P × I residuo */}
          <div className="border border-gray-200 rounded-lg p-4">
            <p className="text-sm font-medium text-gray-700 mb-3">Rischio residuo (P × I dopo i controlli)</p>
            <ProbImpactSelector
              probability={form.probability ?? null}
              impact={form.impact ?? null}
              onChange={(field, value) => set(field, value)}
            />
          </div>

          {/* Classificazione NIS2 */}
          <details className="border border-blue-200 rounded-lg">
            <summary className="px-4 py-2 cursor-pointer text-sm font-medium text-blue-800 bg-blue-50 rounded-lg select-none">
              {t("risk.nis2_section")}
            </summary>
            <div className="px-4 py-3 space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{t("risk.nis2_art21_label")}</label>
                  <select value={form.nis2_art21_category ?? ""} onChange={e => set("nis2_art21_category", e.target.value)}
                    className="w-full border rounded px-3 py-2 text-xs">
                    <option value="">— seleziona —</option>
                    {NIS2_ART21_CHOICES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{t("risk.nis2_relevance_label")}</label>
                  <select value={form.nis2_relevance ?? ""} onChange={e => set("nis2_relevance", e.target.value)}
                    className="w-full border rounded px-3 py-2 text-xs">
                    <option value="">— seleziona —</option>
                    {NIS2_RELEVANCE_CHOICES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">{t("risk.impacted_systems_label")}</label>
                <input value={form.impacted_systems ?? ""} onChange={e => set("impacted_systems", e.target.value)}
                  placeholder={t("risk.impacted_systems_placeholder")}
                  className="w-full border rounded px-3 py-2 text-xs" />
              </div>
            </div>
          </details>

          {/* ALE calcolato (readonly) */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">ALE calcolato dalla BIA</label>
            {alePreview ? (
              <>
                <div className="w-full border border-dashed border-blue-300 bg-blue-50 rounded px-3 py-2 text-sm font-semibold text-blue-800">
                  {alePreview}
                </div>
                <p className="text-xs text-gray-400 mt-1">Calcolato automaticamente da probabilità × impatto × costo fermo BIA</p>
              </>
            ) : (
              <div className="w-full border border-dashed border-gray-200 bg-gray-50 rounded px-3 py-2 text-sm text-gray-400">
                {selectedProcess
                  ? "Seleziona probabilità e impatto per stimare l'ALE"
                  : "Collega un processo BIA per calcolare l'ALE"}
              </div>
            )}
          </div>
        </div>

        {error && <p className="text-sm text-red-600 bg-red-50 px-6 py-2">{error}</p>}
        <div className="flex justify-end gap-2 px-6 py-4 border-t border-gray-100 shrink-0">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">{t("actions.cancel")}</button>
          <button onClick={() => mutation.mutate()} disabled={mutation.isPending || !canSave}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50">
            {mutation.isPending ? t("common.saving") : "Crea scenario"}
          </button>
        </div>
      </div>
    </div>
  );
}

function EditAssessmentModal({
  assessment,
  onClose,
}: {
  assessment: RiskAssessment;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const plantId = assessment.plant;

  const [form, setForm] = useState<Partial<RiskAssessment>>({
    name: assessment.name,
    threat_category: assessment.threat_category,
    assessment_type: assessment.assessment_type,
    owner: assessment.owner,
    critical_process: assessment.critical_process,
    treatment: assessment.treatment,
    plan_due_date: assessment.plan_due_date,
    inherent_probability: assessment.inherent_probability,
    inherent_impact: assessment.inherent_impact,
    probability: assessment.probability,
    impact: assessment.impact,
    cause: assessment.cause,
    consequence: assessment.consequence,
    nis2_art21_category: assessment.nis2_art21_category,
    nis2_relevance: assessment.nis2_relevance,
    impacted_systems: assessment.impacted_systems,
  });

  const [error, setError] = useState("");

  const { data: processes } = useQuery({
    queryKey: ["bia-processes", plantId],
    queryFn: () => biaApi.list(plantId ? { plant: plantId, page_size: "200" } : {}),
    enabled: !!plantId,
    retry: false,
  });

  const { data: users } = useQuery({
    queryKey: ["users"],
    queryFn: () => usersApi.list(),
    retry: false,
  });

  const mutation = useMutation({
    mutationFn: () => {
      const payload = {
        name: form.name,
        threat_category: form.threat_category,
        assessment_type: form.assessment_type,
        owner: form.owner ?? null,
        critical_process: form.critical_process ?? null,
        treatment: form.treatment ?? "",
        plan_due_date: form.plan_due_date ?? null,
        inherent_probability: form.inherent_probability ?? null,
        inherent_impact: form.inherent_impact ?? null,
        probability: form.probability ?? null,
        impact: form.impact ?? null,
        cause: form.cause ?? "",
        consequence: form.consequence ?? "",
        nis2_art21_category: form.nis2_art21_category ?? "",
        nis2_relevance: form.nis2_relevance ?? "",
        impacted_systems: form.impacted_systems ?? "",
      };
      return riskApi.update(assessment.id, payload);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["risk-assessments"] });
      onClose();
    },
    onError: (e: any) => setError(e?.response?.data?.detail || JSON.stringify(e?.response?.data) || t("risk.error_generic")),
  });

  const selectedProcess = processes?.results?.find(p => p.id === form.critical_process);

  function set(field: string, value: unknown) {
    setForm(f => ({ ...f, [field]: value }));
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl flex flex-col max-h-[92vh]">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 shrink-0">
          <h3 className="text-lg font-semibold">Modifica scenario rischio</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl w-8 h-8 flex items-center justify-center rounded hover:bg-gray-100"
          >
            ×
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nome scenario / rischio *</label>
            <input
              value={form.name ?? ""}
              onChange={e => set("name", e.target.value)}
              className="w-full border rounded px-3 py-2 text-sm"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("risk.cause_label")}</label>
              <textarea value={form.cause ?? ""} onChange={e => set("cause", e.target.value)}
                rows={2} placeholder={t("risk.cause_placeholder")}
                className="w-full border rounded px-3 py-2 text-sm resize-none" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("risk.consequence_label")}</label>
              <textarea value={form.consequence ?? ""} onChange={e => set("consequence", e.target.value)}
                rows={2} placeholder={t("risk.consequence_placeholder")}
                className="w-full border rounded px-3 py-2 text-sm resize-none" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Categoria minaccia</label>
              <select
                value={form.threat_category ?? ""}
                onChange={e => set("threat_category", e.target.value)}
                className="w-full border rounded px-3 py-2 text-sm"
              >
                {THREAT_CATEGORIES.map(c => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tipo asset</label>
              <select
                value={form.assessment_type ?? "IT"}
                onChange={e => set("assessment_type", e.target.value)}
                className="w-full border rounded px-3 py-2 text-sm"
              >
                <option value="IT">IT</option>
                <option value="OT">OT</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Trattamento previsto</label>
              <select
                value={form.treatment ?? ""}
                onChange={e => set("treatment", e.target.value)}
                className="w-full border rounded px-3 py-2 text-sm"
              >
                <option value="mitigare">{t("risk.treatment_mitigare")}</option>
                <option value="accettare">{t("risk.treatment_accettare")}</option>
                <option value="trasferire">{t("risk.treatment_trasferire")}</option>
                <option value="evitare">{t("risk.treatment_evitare")}</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("risk.plan_due_date_label")}</label>
              <input
                type="date"
                value={form.plan_due_date ?? ""}
                onChange={e => set("plan_due_date", e.target.value || null)}
                className="w-full border rounded px-3 py-2 text-sm"
              />
              <p className="text-xs text-gray-500 mt-1">{t("risk.plan_due_date_help")}</p>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Owner</label>
            <select
              value={form.owner ?? ""}
              onChange={e => set("owner", e.target.value || null)}
              className="w-full border rounded px-3 py-2 text-sm"
            >
              <option value="">— nessun owner —</option>
              {users?.map(u => (
                <option key={u.id} value={u.id}>
                  {u.first_name || u.last_name ? `${u.first_name} ${u.last_name}`.trim() : u.username} ({u.email})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Processo BIA collegato</label>
            <select
              value={form.critical_process ?? ""}
              onChange={e => set("critical_process", e.target.value || null)}
              disabled={!plantId}
              className="w-full border rounded px-3 py-2 text-sm disabled:bg-gray-50"
            >
              <option value="">— nessun processo BIA —</option>
              {processes?.results?.map(p => (
                <option key={p.id} value={p.id}>
                  {p.name} [criticità {p.criticality}]
                </option>
              ))}
            </select>
            {selectedProcess && (
              <p className="mt-2 text-xs text-gray-500">
                MTPD {selectedProcess.mtpd_hours ?? "—"}h • RTO target {selectedProcess.rto_target_hours ?? "—"}h
              </p>
            )}
          </div>

          <div className="border border-orange-200 rounded-lg p-4 bg-orange-50/30">
            <p className="text-sm font-medium text-orange-800 mb-2">Rischio inerente (prima dei controlli)</p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Probabilità inerente</label>
                <select
                  value={form.inherent_probability ?? ""}
                  onChange={e => set("inherent_probability", e.target.value ? Number(e.target.value) : null)}
                  className="w-full border rounded px-3 py-2 text-sm"
                >
                  <option value="">—</option>
                  {[1,2,3,4,5].map(v => <option key={v} value={v}>{v}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Impatto inerente</label>
                <select
                  value={form.inherent_impact ?? ""}
                  onChange={e => set("inherent_impact", e.target.value ? Number(e.target.value) : null)}
                  className="w-full border rounded px-3 py-2 text-sm"
                >
                  <option value="">—</option>
                  {[1,2,3,4,5].map(v => <option key={v} value={v}>{v}</option>)}
                </select>
              </div>
            </div>
          </div>

          <div className="border border-gray-200 rounded-lg p-4">
            <p className="text-sm font-medium text-gray-700 mb-3">Rischio residuo (P × I dopo i controlli)</p>
            <ProbImpactSelector
              probability={form.probability ?? null}
              impact={form.impact ?? null}
              onChange={(field, value) => set(field, value)}
            />
          </div>

          {/* Classificazione NIS2 */}
          <details className="border border-blue-200 rounded-lg" open={!!(form.nis2_art21_category || form.nis2_relevance || form.impacted_systems)}>
            <summary className="px-4 py-2 cursor-pointer text-sm font-medium text-blue-800 bg-blue-50 rounded-lg select-none">
              {t("risk.nis2_section")}
            </summary>
            <div className="px-4 py-3 space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{t("risk.nis2_art21_label")}</label>
                  <select value={form.nis2_art21_category ?? ""} onChange={e => set("nis2_art21_category", e.target.value)}
                    className="w-full border rounded px-3 py-2 text-xs">
                    <option value="">— seleziona —</option>
                    {NIS2_ART21_CHOICES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{t("risk.nis2_relevance_label")}</label>
                  <select value={form.nis2_relevance ?? ""} onChange={e => set("nis2_relevance", e.target.value)}
                    className="w-full border rounded px-3 py-2 text-xs">
                    <option value="">— seleziona —</option>
                    {NIS2_RELEVANCE_CHOICES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">{t("risk.impacted_systems_label")}</label>
                <input value={form.impacted_systems ?? ""} onChange={e => set("impacted_systems", e.target.value)}
                  placeholder={t("risk.impacted_systems_placeholder")}
                  className="w-full border rounded px-3 py-2 text-xs" />
              </div>
            </div>
          </details>
        </div>

        {error && <p className="text-sm text-red-600 bg-red-50 px-6 py-2">{error}</p>}

        <div className="flex justify-end gap-2 px-6 py-4 border-t border-gray-100 shrink-0">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">
            {t("actions.cancel")}
          </button>
          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? t("common.saving") : t("actions.save")}
          </button>
        </div>
      </div>
    </div>
  );
}

interface RiskAppetitePolicy {
  id: string;
  max_acceptable_score: number;
  max_red_risks_count: number;
  max_unacceptable_score: number;
  valid_from: string;
  valid_until: string | null;
  approved_by_name: string | null;
  is_active: boolean;
  framework_code: string;
}

function RiskAppetiteCard({ plantId }: { plantId?: string }) {
  const { data: policy, isLoading, isError } = useQuery({
    queryKey: ["risk-appetite", plantId],
    queryFn: () => {
      const params = new URLSearchParams();
      if (plantId) params.set("plant", plantId);
      return apiClient.get<RiskAppetitePolicy>(
        `/risk/appetite-policies/active/?${params.toString()}`
      ).then(r => r.data);
    },
    retry: false,
  });

  if (isLoading) return null;
  if (isError || !policy) return null;

  return (
    <div className="mb-4 bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 flex flex-wrap gap-6 items-center text-sm">
      <div>
        <span className="text-xs text-blue-500 font-medium uppercase">Risk Appetite Policy</span>
        {policy.framework_code && <span className="ml-2 text-xs text-blue-400">{policy.framework_code}</span>}
      </div>
      <div className="text-gray-700">
        Score max accettabile: <strong className="text-orange-600">{policy.max_acceptable_score}</strong>
      </div>
      <div className="text-gray-700">
        Max rischi rossi: <strong className="text-red-600">{policy.max_red_risks_count}</strong>
      </div>
      <div className="text-gray-700">
        Valida fino: <strong>{policy.valid_until ? new Date(policy.valid_until + "T12:00:00").toLocaleDateString(i18n.language || "it") : "—"}</strong>
      </div>
      {policy.approved_by_name && (
        <div className="text-gray-500 text-xs">Approvata da: {policy.approved_by_name}</div>
      )}
    </div>
  );
}

export function RiskPage() {
  const { t } = useTranslation();
  const location = useLocation();
  const [typeFilter, setTypeFilter] = useState<"" | "IT" | "OT">("");
  const [statusFilter, setStatusFilter] = useState("");
  const [showNew, setShowNew] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [showWizard, setShowWizard] = useState(false);
  const [editAssessment, setEditAssessment] = useState<RiskAssessment | null>(null);
  const selectedPlant = useAuthStore(s => s.selectedPlant);
  const qc = useQueryClient();

  // Deep-link dal GRC Assistant: scrolla ed evidenzia la riga del rischio.
  useEffect(() => {
    const state = location.state as { openRiskId?: string } | null;
    if (state?.openRiskId) {
      setExpandedId(state.openRiskId);
      scrollAndHighlight(state.openRiskId);
    }
  }, [location.state]);

  const params: Record<string, string> = { page_size: "200" };
  if (typeFilter) params.assessment_type = typeFilter;
  if (statusFilter) params.status = statusFilter;
  if (selectedPlant?.id) params.plant = selectedPlant.id;

  const { data, isLoading } = useQuery({
    queryKey: ["risk-assessments", typeFilter, statusFilter, selectedPlant?.id],
    queryFn: () => riskApi.list(params),
    retry: false,
  });

  const { data: plants } = useQuery({ queryKey: ["plants"], queryFn: () => plantsApi.list(), retry: false });

  const completeMutation = useMutation({
    mutationFn: (id: string) => riskApi.complete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["risk-assessments"] }),
  });

  const acceptMutation = useMutation({
    mutationFn: (id: string) => riskApi.accept(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["risk-assessments"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => riskApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["risk-assessments"] }),
  });

  const reopenMutation = useMutation({
    mutationFn: (id: string) => riskApi.reopen(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["risk-assessments"] }),
  });

  const assessments: RiskAssessment[] = data?.results ?? [];

  return (
    <div>
      <RiskAppetiteCard plantId={selectedPlant?.id} />
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900 flex items-center">
          Risk Assessment
          <ModuleHelp
            title={i18n.t("eval_assistant.risk_module.title")}
            description={i18n.t("eval_assistant.risk_module.description")}
            steps={[
              i18n.t("eval_assistant.risk_module.steps.1"),
              i18n.t("eval_assistant.risk_module.steps.2"),
              i18n.t("eval_assistant.risk_module.steps.3"),
              i18n.t("eval_assistant.risk_module.steps.4"),
              i18n.t("eval_assistant.risk_module.steps.5"),
              i18n.t("eval_assistant.risk_module.steps.6"),
            ]}
            connections={[
              { module: "M04 Asset", relation: i18n.t("eval_assistant.risk_module.connections.assets") },
              { module: "M05 BIA", relation: i18n.t("eval_assistant.risk_module.connections.bia") },
              { module: "M00 Governance", relation: i18n.t("eval_assistant.risk_module.connections.governance") },
              { module: "M11 PDCA", relation: i18n.t("eval_assistant.risk_module.connections.pdca") },
              { module: "M08 Task", relation: i18n.t("eval_assistant.risk_module.connections.tasks") },
            ]}
            configNeeded={[
              i18n.t("eval_assistant.risk_module.config_needed.1"),
              i18n.t("eval_assistant.risk_module.config_needed.2"),
            ]}
          />
        </h2>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowWizard(true)}
            className="flex items-center gap-2 px-4 py-2 border border-primary-200 text-primary-700 rounded-lg hover:bg-primary-50 text-sm font-medium"
          >
            <span>🧭</span> {t("risk.wizard_title")}
          </button>
          <button
            onClick={() => setDrawerOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium"
          >
            <span>?</span> Guida alla valutazione
          </button>
          <button
            onClick={async () => {
              try {
                const resp = await riskApi.exportExcel({ plant: selectedPlant?.id, include_draft: false });
                const url = window.URL.createObjectURL(new Blob([resp.data]));
                const a = document.createElement("a");
                a.href = url;
                a.download = `risk_register${selectedPlant?.id ? `_${selectedPlant.code}` : ""}.xlsx`;
                a.click();
                window.URL.revokeObjectURL(url);
              } catch { /* ignore */ }
            }}
            className="flex items-center gap-2 px-4 py-2 border border-green-300 text-green-700 rounded-lg hover:bg-green-50 text-sm font-medium"
          >
            <span>⬇</span> {t("risk.export_excel")}
          </button>
          <button onClick={() => setShowNew(true)} className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700">
            + Nuovo scenario
          </button>
        </div>
      </div>

      <div className="mb-4 flex items-center gap-3">
        <div>
          <label className="text-xs text-gray-500 mr-1">Tipo:</label>
          <select value={typeFilter} onChange={e => setTypeFilter(e.target.value as "" | "IT" | "OT")}
            className="border rounded px-2 py-1.5 text-sm">
            <option value="">{t("risk.filter_all")}</option>
            <option value="IT">IT</option>
            <option value="OT">OT</option>
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-500 mr-1">Stato:</label>
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
            className="border rounded px-2 py-1.5 text-sm">
            <option value="">{t("risk.filter_all")}</option>
            <option value="bozza">{t("status.bozza")}</option>
            <option value="completato">{t("status.completato")}</option>
            <option value="archiviato">{t("risk.status_archiviato")}</option>
          </select>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">Caricamento...</div>
        ) : assessments.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-gray-400 mb-2">Nessuno scenario di rischio registrato</p>
            <button onClick={() => setShowNew(true)} className="text-sm text-primary-600 hover:underline">Crea il primo scenario →</button>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600 w-8"></th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Scenario</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Minaccia</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Owner</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Rischio Inerente (P×I)</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Rischio Residuo (P×I)</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Score</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Weighted (pesato)</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">ALE (da BIA)</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Stato</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("risk.plan_col_header")}</th>
                <th className="text-left px-4 py-3 font-medium text-blue-700 bg-blue-50">NIS2</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {assessments.map(a => (
                <>
                  <tr
                    key={a.id}
                    data-row-id={a.id}
                    onClick={() => setExpandedId(prev => prev === a.id ? null : a.id)}
                    className="hover:bg-gray-50 transition-colors cursor-pointer border-b border-gray-100"
                  >
                    <td className="px-4 py-3 text-gray-400 text-xs">{expandedId === a.id ? "▼" : "▶"}</td>
                    <td className="px-4 py-3">
                      <div className="font-medium text-gray-800">{a.name || <span className="text-gray-400 italic">—</span>}</div>
                      <div className="text-xs text-gray-400">{a.assessment_type}{a.critical_process_name && ` · ${a.critical_process_name}`}</div>
                    </td>
                    <td className="px-4 py-3 text-gray-600 text-xs">
                      {THREAT_CATEGORIES.find(c => c.value === a.threat_category)?.label ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-gray-600 text-xs">{a.owner_name ?? <span className="text-gray-300">—</span>}</td>
                    <td className="px-4 py-3 text-gray-600">
                      <div className="space-y-1">
                        <div>
                          {a.inherent_probability && a.inherent_impact
                            ? (
                              <span className={`text-xs font-mono font-bold px-1.5 py-0.5 rounded inline-block ${matrixColor(a.inherent_probability, a.inherent_impact)}`}>
                                {a.inherent_probability}×{a.inherent_impact}
                              </span>
                            )
                            : <span className="text-gray-400">—</span>}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      <div className="space-y-1">
                        <div>
                          {a.probability && a.impact
                            ? (
                              <span className={`text-xs font-mono font-bold px-1.5 py-0.5 rounded inline-block ${matrixColor(a.probability, a.impact)}`}>
                                {a.probability}×{a.impact}
                              </span>
                            )
                            : <span className="text-gray-400">—</span>}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="space-y-1">
                        <RiskLevelBadge score={a.score} />
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="space-y-1">
                        <RiskLevelBadge score={a.weighted_score} />
                        <div className="text-xs text-gray-500">Pesato sulla criticità BIA</div>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-600 text-xs">
                      <div className="space-y-1">
                        {a.ale_calcolato
                          ? <span className="text-blue-700 font-medium">{formatAle(a.ale_calcolato)}</span>
                          : <span>{formatAle(a.ale_annuo)}</span>}
                        <div className="text-xs text-gray-500">
                          {a.critical_process_name
                            ? (a.ale_calcolato ? "Calcolato da downtime_cost BIA" : "Stima (mancano dati BIA)")
                            : "BIA non collegata"}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <EffectiveStatusBadge assessment={a} />
                    </td>
                    <td className="px-4 py-3">
                      <TreatmentDeadlineBadge assessment={a} />
                    </td>
                    <td className="px-4 py-3 bg-blue-50/30" onClick={e => e.stopPropagation()}>
                      <div className="space-y-1">
                        {a.nis2_art21_category && (
                          <span className="block text-xs px-1.5 py-0.5 rounded bg-blue-100 text-blue-800 font-mono whitespace-nowrap">
                            {a.nis2_art21_category.replace("art21_", "Art.21(2)(").concat(")")}
                          </span>
                        )}
                        {a.nis2_relevance && (
                          <span className={`block text-xs px-1.5 py-0.5 rounded whitespace-nowrap ${
                            a.nis2_relevance === "significativo" ? "bg-red-100 text-red-700" :
                            a.nis2_relevance === "potenzialmente_significativo" ? "bg-orange-100 text-orange-700" :
                            "bg-gray-100 text-gray-600"
                          }`}>
                            {a.nis2_relevance === "significativo" ? "Significativo" :
                             a.nis2_relevance === "potenzialmente_significativo" ? "Pot. significativo" :
                             a.nis2_relevance === "non_significativo" ? "Non significativo" : "—"}
                          </span>
                        )}
                        {!a.nis2_art21_category && !a.nis2_relevance && <span className="text-xs text-gray-300">—</span>}
                      </div>
                    </td>
                    <td className="px-3 py-3 whitespace-nowrap" onClick={e => e.stopPropagation()}>
                      <div className="flex items-center gap-1">
                        {a.status === "bozza" && !!a.probability && !!a.impact && (
                          <button onClick={() => completeMutation.mutate(a.id)} disabled={completeMutation.isPending}
                            className="text-xs text-blue-700 border border-blue-300 rounded px-2 py-1 hover:bg-blue-50 disabled:opacity-50 font-medium">
                            Completa
                          </button>
                        )}
                        {a.status === "completato" && (
                          <button
                            onClick={() => {
                              if (window.confirm(t("risk.reopen_confirm"))) reopenMutation.mutate(a.id);
                            }}
                            disabled={reopenMutation.isPending}
                            title={t("risk.reopen_label")}
                            className="p-1.5 text-gray-400 hover:text-orange-600 hover:bg-orange-50 rounded transition-colors disabled:opacity-50"
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
                              <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
                            </svg>
                          </button>
                        )}
                        {a.status !== "archiviato" && (
                          <button
                            onClick={() => setEditAssessment(a)}
                            title="Modifica"
                            className="p-1.5 text-gray-500 hover:text-purple-700 hover:bg-purple-50 rounded transition-colors"
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
                              <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                            </svg>
                          </button>
                        )}
                        <button
                          onClick={() => {
                            if (window.confirm("Eliminare questo Risk Assessment?")) {
                              deleteMutation.mutate(a.id);
                            }
                          }}
                          disabled={deleteMutation.isPending}
                          title="Elimina"
                          className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors disabled:opacity-50"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
                            <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                          </svg>
                        </button>
                      </div>
                    </td>
                  </tr>
                  {expandedId === a.id && (
                    <tr key={`${a.id}-detail`}>
                      <td colSpan={13} className="p-0">
                        <RiskInherentResidualBadges assessment={a} />
                        <SuggestResidualPanel assessment={a} />
                        <FormalAcceptancePanel assessment={a} />
                        <MitigationPanel assessmentId={a.id} />
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showNew && plants && <NewAssessmentModal plants={plants} onClose={() => setShowNew(false)} />}
      <AssistenteValutazione open={drawerOpen} onClose={() => setDrawerOpen(false)} />
      {showWizard && <RiskContinuityWizard onClose={() => setShowWizard(false)} />}
      {editAssessment && (
        <EditAssessmentModal
          assessment={editAssessment}
          onClose={() => setEditAssessment(null)}
        />
      )}
    </div>
  );
}
