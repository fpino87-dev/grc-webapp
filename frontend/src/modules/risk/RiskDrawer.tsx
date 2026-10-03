import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { apiError, riskApi, type CycleKind, type ResolvedPolicy, type Risk } from "../../api/endpoints/risk";
import {
  CurrentRiskStep, DecisionStep, ScenarioStep, initialEvaluation, scenarioSummary, stepStatus, useEvaluationModel,
  type EvaluationState,
} from "./EvaluationForm";
import { AcceptanceSection, LocalImpactSection, MeasuresSection, PlanSection } from "./RiskSections";
import { ClassTransition, ErrorBox, Section, Step, StepDot } from "./RiskUi";
import { AiDraftButton } from "./RiskAi";
import type { RegisterId } from "./RiskPage";
import { Link } from "react-router-dom";
import { TrackBadge } from "../objectives/objectiveBadges";
import type { ObjectiveTrack } from "../../api/endpoints/securityObjectives";
import { useUiStore } from "../../store/ui";

/** Scheda del rischio in un pannello laterale largo fino alla barra dei menu.
 * Passi nell'ordine del ragionamento: scenario → misure esistenti → rischio
 * attuale → decisione (accettare il residuo o trattare) → collegamenti. */
export function RiskDrawer({ riskId, registerId, evaluating, cycleKind, canWrite, orgScope, onClose }: {
  riskId: string;
  registerId: RegisterId;
  evaluating: boolean;
  cycleKind: CycleKind | null;
  canWrite: boolean;
  orgScope: boolean;
  onClose: () => void;
}) {
  const { t, i18n } = useTranslation();
  const qc = useQueryClient();
  const [form, setForm] = useState<EvaluationState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const { data: risk, isLoading } = useQuery({ queryKey: ["risk", riskId], queryFn: () => riskApi.get(riskId), retry: false });
  const { data: policy } = useQuery({
    queryKey: ["risk-policy", risk?.plant ?? null],
    queryFn: () => riskApi.resolvedPolicy(risk?.plant ?? null),
    enabled: !!risk,
    retry: false,
  });

  useEffect(() => { if (risk) setForm(initialEvaluation(risk)); }, [risk]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const sidebarCollapsed = useUiStore(s => s.sidebarCollapsed);
  const ownRegister = !!risk && (risk.plant ?? null) === registerId;
  const editable = !!risk && !risk.is_legacy && ownRegister && evaluating && canWrite;
  const canMonitor = !!risk && !risk.is_legacy && ownRegister && canWrite;

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["risk", riskId] });
    qc.invalidateQueries({ queryKey: ["risk-register"] });
    qc.invalidateQueries({ queryKey: ["risk-coverage", registerId] });
    qc.invalidateQueries({ queryKey: ["risk-matrix"] });
  };
  const onErr = (e: unknown) => setError(apiError(e, t("risk.errors.generic")));
  const save = useMutation({
    mutationFn: () => riskApi.update(riskId, form!),
    onSuccess: () => { setError(null); refresh(); },
    onError: onErr,
  });
  const complete = useMutation({
    mutationFn: async () => {
      await riskApi.update(riskId, form!);
      const check = await riskApi.completeness(riskId);
      setErrors(check.errors);
      if (check.errors.length) throw new Error("incomplete");
      return riskApi.complete(riskId);
    },
    onSuccess: () => { setError(null); setErrors([]); refresh(); },
    onError: e => { if ((e as Error).message !== "incomplete") onErr(e); refresh(); },
  });
  const confirm = useMutation({ mutationFn: () => riskApi.confirm(riskId), onSuccess: refresh, onError: onErr });
  const reopen = useMutation({ mutationFn: () => riskApi.reopen(riskId), onSuccess: refresh, onError: onErr });
  const remove = useMutation({
    mutationFn: () => riskApi.remove(riskId),
    onSuccess: () => { refresh(); onClose(); },
    onError: onErr,
  });
  // Rischio inserito per errore: esce dal registro e la coppia diventa non applicabile.
  const [naReason, setNaReason] = useState<string | null>(null);
  const convertNa = useMutation({
    mutationFn: () => riskApi.convertNotApplicable(riskId, naReason ?? ""),
    onSuccess: () => { refresh(); onClose(); },
    onError: onErr,
  });

  const dirty = !!risk && !!form && JSON.stringify(form) !== JSON.stringify(initialEvaluation(risk));
  const needsConfirm = !!risk && cycleKind === "periodico" && evaluating && risk.status === "completato"
    && risk.evaluated_in_cycle !== null && risk.applicable;

  return (
    <div className={`fixed inset-0 z-50 flex justify-end ${sidebarCollapsed ? "pl-14" : "pl-56"}`} role="dialog" aria-modal="true" aria-label={risk?.display_name ?? t("risk.drawer.title")}>
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />
      <aside className="relative h-full w-full bg-white shadow-2xl flex flex-col">
        <header className="px-6 pt-4 pb-3 border-b border-gray-100">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <p className="text-xs text-gray-500 font-mono">
                {risk?.threat_code} · {risk?.asset_type ? t(`risk.asset_types.${risk.asset_type}`) : ""}
                {risk?.plant_name ? ` · ${risk.plant_name}` : risk ? ` · ${t("risk.page.group_register")}` : ""}
              </p>
              <h2 className="text-lg font-semibold text-gray-900 truncate">{risk?.display_name ?? "…"}</h2>
              {risk && (
                <div className="flex flex-wrap items-center gap-2 mt-1">
                  <ClassTransition current={risk.current_class} expected={risk.treatment === "accettare" ? "" : risk.expected_class} />
                  <span className="text-[11px] px-2 py-0.5 rounded-full bg-gray-100 text-gray-600">
                    {t(risk.status === "completato" ? "risk.register.status_done" : "risk.register.status_draft")}
                  </span>
                  {risk.is_legacy && <span className="text-[11px] px-2 py-0.5 rounded-full bg-amber-100 text-amber-800">{t("risk.drawer.legacy_badge")}</span>}
                  {risk.is_inherited && <span className="text-[11px] px-2 py-0.5 rounded-full bg-blue-50 text-blue-700">{t("risk.drawer.inherited_badge")}</span>}
                  {dirty && <span className="text-[11px] text-amber-700">● {t("risk.drawer.unsaved")}</span>}
                </div>
              )}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {risk && editable && (
                <>
                  <button onClick={() => { if (window.confirm(t(risk.applicable ? "risk.drawer.delete_confirm" : "risk.drawer.delete_na_confirm"))) remove.mutate(); }}
                    className="px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 rounded">{t("common.delete")}</button>
                  {risk.applicable && (
                    <button onClick={() => setNaReason(naReason === null ? "" : null)} aria-expanded={naReason !== null}
                      className="px-3 py-1.5 border rounded text-sm">{t("risk.drawer.make_not_applicable")}</button>
                  )}
                  {risk.applicable && risk.status === "completato" && (
                    <button onClick={() => reopen.mutate()} className="px-3 py-1.5 border rounded text-sm">{t("risk.drawer.reopen")}</button>
                  )}
                  {risk.applicable && needsConfirm && !dirty && (
                    <button onClick={() => confirm.mutate()} className="px-3 py-1.5 border rounded text-sm">{t("risk.drawer.confirm")}</button>
                  )}
                  {risk.applicable && (
                    <>
                      <button onClick={() => save.mutate()} disabled={!dirty || save.isPending} className="px-3 py-1.5 border rounded text-sm disabled:opacity-50">
                        {t("common.save")}
                      </button>
                      <button onClick={() => complete.mutate()} disabled={complete.isPending}
                        className="px-3 py-1.5 bg-primary-600 text-white rounded text-sm disabled:opacity-50">
                        {t("risk.drawer.complete")}
                      </button>
                    </>
                  )}
                </>
              )}
              <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl leading-none px-1" aria-label={t("common.close")}>×</button>
            </div>
          </div>
          {risk && editable && naReason !== null && (
            <div className="mt-3 border border-amber-200 bg-amber-50 rounded p-3">
              <p className="text-xs text-amber-900 mb-2">{t("risk.drawer.make_not_applicable_hint")}</p>
              <textarea value={naReason} onChange={e => setNaReason(e.target.value)} rows={2} className="w-full border border-gray-300 rounded px-2.5 py-1.5 text-sm"
                placeholder={t("risk.drawer.not_applicable_reason")} aria-label={t("risk.drawer.not_applicable_reason")} />
              <div className="flex gap-2 mt-2">
                <button onClick={() => convertNa.mutate()} disabled={!naReason.trim() || convertNa.isPending}
                  className="px-3 py-1.5 bg-amber-600 text-white rounded text-sm disabled:opacity-50">{t("risk.drawer.make_not_applicable_confirm")}</button>
                <button onClick={() => setNaReason(null)} className="px-3 py-1.5 text-sm text-gray-600 hover:underline">{t("common.cancel")}</button>
              </div>
            </div>
          )}
          {risk && !editable && !risk.is_legacy && ownRegister && (
            <p className="text-[11px] text-gray-500 mt-2">{t(evaluating ? "risk.drawer.read_only_rights" : "risk.drawer.read_only_no_cycle")}</p>
          )}
          {errors.length > 0 && (
            <ul className="mt-2 text-sm text-red-700 bg-red-50 border border-red-200 rounded px-4 py-2 list-disc pl-6">
              {errors.map(e => <li key={e}>{e}</li>)}
            </ul>
          )}
          <ErrorBox message={error} />
        </header>

        <div className="flex-1 overflow-y-auto px-6 py-4">
          {isLoading || !risk || !form ? (
            <p className="text-sm text-gray-400">{t("common.loading")}</p>
          ) : risk.is_legacy ? (
            <LegacyView snapshot={risk.legacy_snapshot} lang={i18n.language} />
          ) : !risk.applicable ? (
            <Section title={t("risk.drawer.not_applicable_title")}>
              <p className="text-sm text-gray-700">{risk.not_applicable_reason}</p>
              {editable && <p className="text-xs text-gray-500 mt-2">{t("risk.drawer.not_applicable_undo_hint")}</p>}
            </Section>
          ) : (
            <RiskSheet risk={risk} form={form} setForm={setForm} editable={editable} canMonitor={canMonitor}
              policy={policy} registerId={registerId} orgScope={orgScope} />
          )}
        </div>
      </aside>
    </div>
  );
}

const STEP_IDS = ["risk-step-1", "risk-step-2", "risk-step-3", "risk-step-4", "risk-step-5"];

function RiskSheet({ risk, form, setForm, editable, canMonitor, policy, registerId, orgScope }: {
  risk: Risk; form: EvaluationState; setForm: (f: EvaluationState) => void; editable: boolean; canMonitor: boolean;
  policy?: ResolvedPolicy; registerId: RegisterId; orgScope: boolean;
}) {
  const { t, i18n } = useTranslation();
  const model = useEvaluationModel(risk, form);
  const status = stepStatus(form, model);
  const { data: measures = [] } = useQuery({
    queryKey: ["risk-measures", risk.id], queryFn: () => riskApi.measures(risk.id), retry: false,
  });
  // Lo scenario già compilato parte chiuso: si lavora sui passi che mancano.
  const [open, setOpen] = useState<boolean[]>(() => [!status.scenario, true, true, true, false]);
  const toggle = (i: number) => setOpen(o => o.map((v, j) => (j === i ? !v : v)));
  const goTo = (i: number) => {
    setOpen(o => o.map((v, j) => (j === i ? true : v)));
    setTimeout(() => document.getElementById(STEP_IDS[i])?.scrollIntoView?.({ behavior: "smooth", block: "start" }), 0);
  };
  const steps: { title: string; done: boolean | null }[] = [
    { title: t("risk.drawer.step_scenario"), done: status.scenario },
    { title: t("risk.drawer.step_measures"), done: measures.length ? true : null },
    { title: t("risk.drawer.step_current"), done: status.current },
    { title: t("risk.drawer.step_decision"), done: status.decision },
    { title: t("risk.drawer.step_links"), done: null },
  ];
  const missing = steps.filter(s => s.done === false).map(s => s.title);
  const acceptance = <AcceptanceSection risk={risk} canMonitor={canMonitor} />;

  return (
    <div className="flex gap-6 items-start">
      <nav aria-label={t("risk.drawer.steps")} className="w-52 shrink-0 sticky top-0 space-y-1">
        {steps.map((s, i) => (
          <button key={STEP_IDS[i]} type="button" onClick={() => goTo(i)}
            className="w-full flex items-center gap-2 px-2 py-2 rounded text-left text-sm hover:bg-gray-50">
            <StepDot n={i + 1} done={s.done} />
            <span className={s.done === false ? "text-gray-900" : "text-gray-700"}>{i + 1} · {s.title}</span>
          </button>
        ))}
        <p className="px-2 pt-2 text-[11px] text-gray-500">
          {missing.length ? t("risk.drawer.steps_missing", { steps: missing.join(", ") }) : t("risk.drawer.steps_ready")}
        </p>
      </nav>

      <div className="flex-1 min-w-0 max-w-5xl space-y-3">
        <Step id={STEP_IDS[0]} n={1} title={steps[0].title} done={steps[0].done} open={open[0]} onToggle={() => toggle(0)}
          summary={scenarioSummary(risk, form, model, t)}>
          <ScenarioStep risk={risk} value={form} onChange={setForm} editable={editable} model={model} />
        </Step>

        <Step id={STEP_IDS[1]} n={2} title={steps[1].title} done={steps[1].done} open={open[1]} onToggle={() => toggle(1)}
          summary={t("risk.drawer.measures_count", { count: measures.length })}>
          <MeasuresSection risk={risk} editable={editable} />
        </Step>

        <Step id={STEP_IDS[2]} n={3} title={steps[2].title} done={steps[2].done} open={open[2]} onToggle={() => toggle(2)}
          summary={model.current ? `P ${form.probability ?? "—"} × I ${model.impact ?? "—"} = ${t(`risk.classes.${model.current}`)}` : undefined}
          right={editable ? <AiDraftButton risk={risk} form={form} onApply={setForm} /> : undefined}>
          <CurrentRiskStep risk={risk} value={form} onChange={setForm} editable={editable} model={model} policy={policy} />
        </Step>

        <Step id={STEP_IDS[3]} n={4} title={steps[3].title} done={steps[3].done} open={open[3]} onToggle={() => toggle(3)}
          summary={form.treatment ? t(`risk.treatment_${form.treatment}`) : undefined}>
          <DecisionStep risk={risk} value={form} onChange={setForm} editable={editable} model={model}
            plan={<PlanSection risk={risk} canMonitor={canMonitor} />} acceptance={acceptance} />
        </Step>

        <Step id={STEP_IDS[4]} n={5} title={steps[4].title} done={steps[4].done} open={open[4]} onToggle={() => toggle(4)}
          summary={t("risk.drawer.assessed", {
            who: risk.assessed_by_name ?? "—",
            when: risk.assessed_at ? new Date(risk.assessed_at).toLocaleDateString(i18n.language) : "—",
          })}>
          {risk.plant === null && <LocalImpactSection risk={risk} registerId={registerId} orgScope={orgScope} />}
          <Section title={t("risk.drawer.security_objectives")}>
            {(risk.security_objectives_summary ?? []).length === 0 ? (
              <p className="text-xs text-gray-500">{t("risk.drawer.no_security_objectives")}</p>
            ) : (
              <ul className="space-y-1 text-sm">
                {(risk.security_objectives_summary ?? []).map(o => (
                  <li key={o.id} className="flex flex-wrap items-center gap-2">
                    <TrackBadge track={o.track as ObjectiveTrack} />
                    <Link to="/objectives" className="text-primary-600 hover:underline">{o.code} — {o.title}</Link>
                    <span className="text-xs text-gray-500">{new Date(o.target_date).toLocaleDateString(i18n.language)}</span>
                  </li>
                ))}
              </ul>
            )}
          </Section>
          <Section title={t("risk.drawer.history")}>
            <p className="text-xs text-gray-500">
              {t("risk.drawer.assessed", {
                who: risk.assessed_by_name ?? "—",
                when: risk.assessed_at ? new Date(risk.assessed_at).toLocaleDateString(i18n.language) : "—",
              })}
            </p>
          </Section>
        </Step>
      </div>
    </div>
  );
}

/** Valutazione precedente (metodo superato): valori congelati, sola lettura. */
function LegacyView({ snapshot, lang }: { snapshot: Record<string, unknown>; lang: string }) {
  const { t } = useTranslation();
  const rows: [string, unknown][] = [
    [t("risk.legacy.score"), snapshot.score],
    [t("risk.legacy.inherent_score"), snapshot.inherent_score],
    [t("risk.legacy.probability_impact"), `${snapshot.probability ?? "—"} × ${snapshot.impact ?? "—"}`],
    [t("risk.legacy.treatment"), snapshot.treatment],
    [t("risk.legacy.cause"), snapshot.cause],
    [t("risk.legacy.consequence"), snapshot.consequence],
    [t("risk.legacy.accepted"), snapshot.risk_accepted_formally ? t("common.yes") : t("common.no")],
    [t("risk.legacy.acceptance_note"), snapshot.risk_acceptance_note],
    [t("risk.legacy.assessed_at"), snapshot.assessed_at ? new Date(String(snapshot.assessed_at)).toLocaleDateString(lang) : null],
  ];
  return (
    <Section title={t("risk.legacy.title")}>
      <p className="text-xs text-gray-500 mb-2">{t("risk.legacy.hint")}</p>
      <dl className="grid grid-cols-3 gap-x-3 gap-y-1 text-sm">
        {rows.map(([k, v]) => (
          <div key={k} className="contents">
            <dt className="text-gray-500 text-xs">{k}</dt>
            <dd className="col-span-2">{v === null || v === undefined || v === "" ? "—" : String(v)}</dd>
          </div>
        ))}
      </dl>
    </Section>
  );
}
