import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { apiError, riskApi, type CycleKind } from "../../api/endpoints/risk";
import { EvaluationForm, initialEvaluation, type EvaluationState } from "./EvaluationForm";
import { AcceptanceSection, LocalImpactSection, MeasuresSection, PlanSection } from "./RiskSections";
import { ClassTransition, ErrorBox, Section } from "./RiskUi";
import { AiDraftButton } from "./RiskAi";
import type { RegisterId } from "./RiskPage";
import { Link } from "react-router-dom";
import { TrackBadge } from "../objectives/objectiveBadges";
import type { ObjectiveTrack } from "../../api/endpoints/securityObjectives";
import { useUiStore } from "../../store/ui";

/** Scheda del rischio in un pannello laterale (pattern UserDrawer), largo
 * fino alla barra dei menu: la scheda ha molti campi affiancati. */
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

  const dirty = !!risk && !!form && JSON.stringify(form) !== JSON.stringify(initialEvaluation(risk));
  const needsConfirm = !!risk && cycleKind === "periodico" && evaluating && risk.status === "completato"
    && risk.evaluated_in_cycle !== null && risk.applicable;

  return (
    <div className={`fixed inset-0 z-50 flex justify-end ${sidebarCollapsed ? "pl-14" : "pl-56"}`} role="dialog" aria-modal="true" aria-label={risk?.display_name ?? t("risk.drawer.title")}>
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />
      <aside className="relative h-full w-full bg-white shadow-2xl flex flex-col">
        <header className="px-6 pt-5 pb-3 border-b border-gray-100">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-xs text-gray-500 font-mono">
                {risk?.threat_code} · {risk?.asset_type ? t(`risk.asset_types.${risk.asset_type}`) : ""}
                {risk?.plant_name ? ` · ${risk.plant_name}` : risk ? ` · ${t("risk.page.group_register")}` : ""}
              </p>
              <h2 className="text-lg font-semibold text-gray-900 truncate">{risk?.display_name ?? "…"}</h2>
              {risk && (
                <div className="flex flex-wrap items-center gap-2 mt-1">
                  <ClassTransition current={risk.current_class} expected={risk.expected_class} />
                  <span className="text-[11px] px-2 py-0.5 rounded-full bg-gray-100 text-gray-600">
                    {t(risk.status === "completato" ? "risk.register.status_done" : "risk.register.status_draft")}
                  </span>
                  {risk.is_legacy && <span className="text-[11px] px-2 py-0.5 rounded-full bg-amber-100 text-amber-800">{t("risk.drawer.legacy_badge")}</span>}
                  {risk.is_inherited && <span className="text-[11px] px-2 py-0.5 rounded-full bg-blue-50 text-blue-700">{t("risk.drawer.inherited_badge")}</span>}
                </div>
              )}
            </div>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl leading-none" aria-label={t("common.close")}>×</button>
          </div>
          {risk && !editable && !risk.is_legacy && ownRegister && (
            <p className="text-[11px] text-gray-500 mt-2">{t(evaluating ? "risk.drawer.read_only_rights" : "risk.drawer.read_only_no_cycle")}</p>
          )}
        </header>

        <div className="flex-1 overflow-y-auto px-6 py-4">
          {isLoading || !risk || !form ? (
            <p className="text-sm text-gray-400">{t("common.loading")}</p>
          ) : risk.is_legacy ? (
            <LegacyView snapshot={risk.legacy_snapshot} lang={i18n.language} />
          ) : !risk.applicable ? (
            <Section title={t("risk.drawer.not_applicable_title")}>
              <p className="text-sm text-gray-700">{risk.not_applicable_reason}</p>
            </Section>
          ) : (
            <>
              {editable && <AiDraftButton risk={risk} form={form} onApply={setForm} />}
              <EvaluationForm risk={risk} value={form} onChange={setForm} editable={editable} policy={policy} />
              <MeasuresSection risk={risk} editable={editable} />
              <PlanSection risk={risk} canMonitor={canMonitor} />
              <AcceptanceSection risk={risk} canMonitor={canMonitor} />
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
            </>
          )}
          {errors.length > 0 && (
            <ul className="mt-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded px-4 py-2 list-disc ml-0 pl-6">
              {errors.map(e => <li key={e}>{e}</li>)}
            </ul>
          )}
          <ErrorBox message={error} />
        </div>

        {risk && editable && (
          <footer className="px-6 py-3 border-t border-gray-100 flex flex-wrap gap-2 justify-end">
            <button onClick={() => { if (window.confirm(t("risk.drawer.delete_confirm"))) remove.mutate(); }}
              className="mr-auto px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 rounded">{t("common.delete")}</button>
            {risk.status === "completato" && (
              <button onClick={() => reopen.mutate()} className="px-3 py-1.5 border rounded text-sm">{t("risk.drawer.reopen")}</button>
            )}
            {needsConfirm && !dirty && (
              <button onClick={() => confirm.mutate()} className="px-3 py-1.5 border rounded text-sm">{t("risk.drawer.confirm")}</button>
            )}
            <button onClick={() => save.mutate()} disabled={!dirty || save.isPending} className="px-3 py-1.5 border rounded text-sm disabled:opacity-50">
              {t("common.save")}
            </button>
            <button onClick={() => complete.mutate()} disabled={complete.isPending}
              className="px-3 py-1.5 bg-primary-600 text-white rounded text-sm disabled:opacity-50">
              {t("risk.drawer.complete")}
            </button>
          </footer>
        )}
      </aside>
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
