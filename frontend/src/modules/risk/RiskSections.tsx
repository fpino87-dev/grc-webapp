import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { AiMeasuresButton } from "./RiskAi";
import { apiError, riskApi, type Acceptance, type ExistingMeasure, type MitigationPlan, type Risk } from "../../api/endpoints/risk";
import { controlsApi } from "../../api/endpoints/controls";
import { plantsApi } from "../../api/endpoints/plants";
import { usersApi } from "../../api/endpoints/users";
import { governanceApi } from "../../api/endpoints/governance";
import { useAuthStore } from "../../store/auth";
import { MixedOwnerField } from "./MixedOwnerField";
import { ClassBadge, ErrorBox, Field, Section, inputCls } from "./RiskUi";

// Controlli collegabili a una misura: quelli del sito del registro; per un
// rischio di gruppo quelli di tutti i siti visibili, col codice del sito
// davanti (il backend lo ammette, il gruppo vale per ogni sito).
function useControls(plantId: string | null) {
  const { data: controls } = useQuery({
    queryKey: ["control-instances", plantId],
    queryFn: () => controlsApi.instances(plantId ? { plant: plantId } : {}),
    retry: false,
  });
  const { data: plants = [] } = useQuery({
    queryKey: ["plants"], queryFn: () => plantsApi.list(), enabled: !plantId, retry: false,
  });
  const codes = new Map(plants.map(p => [p.id, p.code]));
  return (controls?.results ?? []).map(c => ({
    id: c.id,
    label: `${plantId ? "" : `[${codes.get(c.plant) ?? "?"}] `}${c.control_external_id} ${c.control_title}`,
  }));
}

const fmt = (d: string | null | undefined, lang: string) => (d ? new Date(d).toLocaleDateString(lang) : "—");

// ── Misure esistenti ─────────────────────────────────────────────────────────

export function MeasuresSection({ risk, editable }: { risk: Risk; editable: boolean }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const emptyForm = { control_instance: "", description: "", effectiveness: "media" };
  const [form, setForm] = useState(emptyForm);
  // Misura in modifica: il modulo sotto l'elenco passa da "aggiungi" a "salva".
  const [editingId, setEditingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { data: measures = [] } = useQuery({
    queryKey: ["risk-measures", risk.id], queryFn: () => riskApi.measures(risk.id), retry: false,
  });
  const controls = useControls(risk.plant);
  const refresh = () => qc.invalidateQueries({ queryKey: ["risk-measures", risk.id] });
  const save = useMutation({
    mutationFn: () => {
      const payload = {
        control_instance: form.control_instance || null, description: form.description,
        effectiveness: form.effectiveness as ExistingMeasure["effectiveness"],
      };
      return editingId ? riskApi.updateMeasure(editingId, payload) : riskApi.createMeasure({ risk: risk.id, ...payload });
    },
    onSuccess: () => { setForm(emptyForm); setEditingId(null); setError(null); refresh(); },
    onError: e => setError(apiError(e, t("risk.errors.generic"))),
  });
  const remove = useMutation({ mutationFn: (id: string) => riskApi.deleteMeasure(id), onSuccess: refresh });
  const startEdit = (m: ExistingMeasure) => {
    setEditingId(m.id); setError(null);
    setForm({ control_instance: m.control_instance ?? "", description: m.description, effectiveness: m.effectiveness });
  };
  const effectivenessCls = { alta: "bg-green-100 text-green-800", media: "bg-yellow-100 text-yellow-900", bassa: "bg-gray-100 text-gray-700" };

  return (
    <div>
      <p className="text-xs text-gray-600 mb-2">{t("risk.drawer.existing_measures_hint")}</p>
      {measures.length === 0 && <p className="text-xs text-gray-400 mb-2">{t("risk.drawer.no_measures")}</p>}
      <ul className="space-y-1 mb-2">
        {measures.map(m => (
          <li key={m.id} className={`flex items-center justify-between gap-2 text-sm border rounded px-2 py-1.5 ${editingId === m.id ? "border-primary-400 ring-1 ring-primary-200" : ""}`}>
            <span className="flex-1">
              {m.control_title && <span className="font-mono text-xs text-gray-500 mr-1">{m.control_title}</span>}
              {m.description}
            </span>
            <span className={`text-[11px] px-2 py-0.5 rounded-full whitespace-nowrap ${effectivenessCls[m.effectiveness]}`}>
              {t("risk.drawer.effectiveness")}: {t(`risk.effectiveness.${m.effectiveness}`)}
            </span>
            {editable && (
              <span className="flex gap-2 text-xs">
                <button onClick={() => startEdit(m)} className="text-gray-700 hover:underline">{t("common.edit")}</button>
                <button onClick={() => remove.mutate(m.id)} className="text-red-600 hover:underline">{t("common.delete")}</button>
              </span>
            )}
          </li>
        ))}
      </ul>
      {editable && (
        <div className={`border rounded p-2 ${editingId ? "bg-primary-50 border-primary-300" : "bg-gray-50"}`}>
          <div className="grid grid-cols-6 gap-2 items-start">
            <select value={form.control_instance} onChange={e => setForm({ ...form, control_instance: e.target.value })}
              className={`${inputCls} col-span-2`} aria-label={t("risk.drawer.no_control")}>
              <option value="">{t("risk.drawer.no_control")}</option>
              {controls.map(c => <option key={c.id} value={c.id}>{c.label}</option>)}
            </select>
            <input value={form.description} onChange={e => setForm({ ...form, description: e.target.value })}
              className={`${inputCls} col-span-3`} placeholder={t("risk.drawer.measure_description")} />
            <select value={form.effectiveness} onChange={e => setForm({ ...form, effectiveness: e.target.value })} className={inputCls}
              aria-label={t("risk.drawer.effectiveness")}>
              {["alta", "media", "bassa"].map(x => <option key={x} value={x}>{t(`risk.effectiveness.${x}`)}</option>)}
            </select>
          </div>
          <div className="flex flex-wrap items-center gap-2 mt-2">
            <button onClick={() => save.mutate()} disabled={(!form.description && !form.control_instance) || save.isPending}
              className="px-3 py-1.5 border rounded text-sm bg-white hover:bg-gray-50 disabled:opacity-50">
              {editingId ? t("common.save") : `+ ${t("common.add")}`}
            </button>
            {editingId && (
              <button onClick={() => { setEditingId(null); setForm(emptyForm); }} className="px-3 py-1.5 text-sm text-gray-600 hover:underline">
                {t("common.cancel")}
              </button>
            )}
            <span className="text-[11px] text-gray-500 ml-auto">{t("risk.drawer.effectiveness_guide")}</span>
          </div>
        </div>
      )}
      <ErrorBox message={error} />
    </div>
  );
}

// ── Piano di trattamento ─────────────────────────────────────────────────────

export function PlanSection({ risk, canMonitor }: { risk: Risk; canMonitor: boolean }) {
  const { t, i18n } = useTranslation();
  const qc = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const emptyForm = { action: "", due_date: "", expected_effect: "", control_instance: "", owner: "", owner_external: "" };
  const [form, setForm] = useState(emptyForm);
  // Misura in modifica: il modulo sotto l'elenco passa da "aggiungi" a "salva".
  const [editingId, setEditingId] = useState<string | null>(null);
  const formRef = useRef<HTMLDivElement>(null);
  const [verifying, setVerifying] = useState<MitigationPlan | null>(null);
  const [note, setNote] = useState("");
  const { data: plans = [] } = useQuery({
    queryKey: ["risk-plans", risk.id], queryFn: () => riskApi.plans({ assessment: risk.id }), retry: false,
  });
  const { data: users = [] } = useQuery({ queryKey: ["users"], queryFn: () => usersApi.list(), retry: false });
  const controls = useControls(risk.plant);
  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["risk-plans", risk.id] });
    qc.invalidateQueries({ queryKey: ["risk", risk.id] });
    qc.invalidateQueries({ queryKey: ["risk-register"] });
  };
  const onErr = (e: unknown) => setError(apiError(e, t("risk.errors.generic")));
  const add = useMutation({
    mutationFn: () => {
      const payload = {
        action: form.action, due_date: form.due_date,
        expected_effect: form.expected_effect as MitigationPlan["expected_effect"],
        control_instance: form.control_instance || null,
        owner: form.owner ? Number(form.owner) : null, owner_external: form.owner_external,
      };
      return editingId ? riskApi.updatePlan(editingId, payload) : riskApi.createPlan({ assessment: risk.id, ...payload });
    },
    onSuccess: () => { setForm(emptyForm); setEditingId(null); setError(null); refresh(); },
    onError: onErr,
  });
  const startEdit = (p: MitigationPlan) => {
    setEditingId(p.id); setError(null);
    setForm({
      action: p.action, due_date: p.due_date, expected_effect: p.expected_effect,
      control_instance: p.control_instance ?? "", owner: p.owner ? String(p.owner) : "", owner_external: p.owner_external,
    });
    formRef.current?.scrollIntoView?.({ block: "nearest", behavior: "smooth" });
  };
  const cancelEdit = () => { setEditingId(null); setForm(emptyForm); };
  const complete = useMutation({
    mutationFn: (p: MitigationPlan) => p.completed_at ? riskApi.uncompletePlan(p.id) : riskApi.updatePlan(p.id, { completed_at: new Date().toISOString() }),
    onSuccess: refresh, onError: onErr,
  });
  const verify = useMutation({
    mutationFn: () => riskApi.verifyPlan(verifying!.id, note),
    onSuccess: () => { setVerifying(null); setNote(""); refresh(); }, onError: onErr,
  });
  const remove = useMutation({ mutationFn: (id: string) => riskApi.deletePlan(id), onSuccess: refresh, onError: onErr });
  const applyExpected = useMutation({
    mutationFn: () => riskApi.applyExpected(risk.id, ""), onSuccess: refresh, onError: onErr,
  });
  const today = new Date().toISOString().slice(0, 10);

  return (
    <Section
      title={t("risk.drawer.treatment_plan")}
      right={risk.can_apply_expected && canMonitor ? (
        <button onClick={() => applyExpected.mutate()} className="text-xs px-2 py-1 bg-green-600 text-white rounded hover:bg-green-700">
          {t("risk.drawer.apply_expected")}
        </button>
      ) : undefined}
    >
      <p className="text-[11px] text-gray-500 mb-2">{t("risk.drawer.plan_hint")}</p>
      {canMonitor && risk.treatment !== "accettare" && (
        risk.current_class && risk.treatment
          ? <div className="mb-2"><AiMeasuresButton risk={risk} /></div>
          : <p className="text-[11px] text-amber-700 mb-2">{t("risk.ai.measures_needs_treatment")}</p>
      )}
      {plans.length === 0 && <p className="text-xs text-gray-400 mb-2">{t("risk.drawer.no_plans")}</p>}
      <ul className="space-y-1 mb-2">
        {plans.map(p => {
          const overdue = !p.completed_at && p.due_date < today;
          return (
            <li key={p.id} className={`border rounded px-2 py-1.5 text-sm ${editingId === p.id ? "border-primary-400 ring-1 ring-primary-200" : overdue ? "border-red-200 bg-red-50" : ""}`}>
              <div className="flex items-start justify-between gap-2">
                <span className="flex-1">
                  {p.action}
                  <span className="block text-[11px] text-gray-500">
                    {[p.owner_name, `${t("risk.drawer.due")} ${fmt(p.due_date, i18n.language)}`, p.control_title,
                      p.expected_effect ? t(`risk.effect.${p.expected_effect}`) : null].filter(Boolean).join(" · ")}
                  </span>
                </span>
                <span className="text-[11px] whitespace-nowrap">
                  {p.verified_at ? <span className="text-green-700">✓ {t("risk.drawer.verified")}</span>
                    : p.completed_at ? <span className="text-blue-700">{t("risk.drawer.completed")}</span>
                    : overdue ? <span className="text-red-700">{t("risk.drawer.overdue")}</span>
                    : <span className="text-gray-500">{t("risk.drawer.open")}</span>}
                </span>
              </div>
              {canMonitor && (
                <div className="flex gap-3 mt-1 text-[11px]">
                  <button onClick={() => complete.mutate(p)} className="text-primary-600 hover:underline">
                    {t(p.completed_at ? "risk.drawer.reopen_measure" : "risk.drawer.mark_completed")}
                  </button>
                  {p.completed_at && !p.verified_at && (
                    <button onClick={() => setVerifying(p)} className="text-green-700 hover:underline">{t("risk.drawer.verify")}</button>
                  )}
                  {!p.verified_at && (
                    <button onClick={() => startEdit(p)} className="text-gray-700 hover:underline">{t("common.edit")}</button>
                  )}
                  <button onClick={() => remove.mutate(p.id)} className="text-red-600 hover:underline">{t("common.delete")}</button>
                </div>
              )}
              {verifying?.id === p.id && (
                <div className="flex gap-2 mt-1">
                  <input value={note} onChange={e => setNote(e.target.value)} className={inputCls} placeholder={t("risk.drawer.verification_note")} />
                  <button onClick={() => verify.mutate()} className="px-2 border rounded text-xs">{t("common.confirm")}</button>
                </div>
              )}
            </li>
          );
        })}
      </ul>
      {canMonitor && (
        <div ref={formRef} className={`border rounded p-2 ${editingId ? "bg-primary-50 border-primary-300" : "bg-gray-50"}`}>
          {editingId && <p className="text-xs font-medium text-primary-700 mb-1">{t("risk.drawer.editing_measure")}</p>}
          <div className="grid grid-cols-2 gap-2">
            <textarea value={form.action} onChange={e => setForm({ ...form, action: e.target.value })} rows={editingId ? 3 : 1}
              className={`${inputCls} col-span-2`} placeholder={t("risk.drawer.measure_action")} />
            <input type="date" value={form.due_date} onChange={e => setForm({ ...form, due_date: e.target.value })} className={inputCls} />
            <select value={form.expected_effect} onChange={e => setForm({ ...form, expected_effect: e.target.value })} className={inputCls}>
              <option value="">{t("risk.drawer.expected_effect")}</option>
              {["probabilita", "impatto", "entrambi"].map(x => <option key={x} value={x}>{t(`risk.effect.${x}`)}</option>)}
            </select>
            <select value={form.control_instance} onChange={e => setForm({ ...form, control_instance: e.target.value })}
              className={inputCls}>
              <option value="">{t("risk.drawer.no_control")}</option>
              {controls.map(c => <option key={c.id} value={c.id}>{c.label}</option>)}
            </select>
            <MixedOwnerField users={users} userId={form.owner || null} external={form.owner_external} small
              noneLabel={t("risk.drawer.measure_owner")}
              onChange={(uid, ext) => setForm({ ...form, owner: uid ?? "", owner_external: ext })} />
          </div>
          <div className="flex gap-2 mt-2">
            <button onClick={() => add.mutate()} disabled={!form.action || !form.due_date || add.isPending}
              className="px-3 py-1.5 border rounded text-sm bg-white hover:bg-gray-50 disabled:opacity-50">
              {editingId ? t("common.save") : `+ ${t("risk.drawer.add_measure")}`}
            </button>
            {editingId && (
              <button onClick={cancelEdit} className="px-3 py-1.5 text-sm text-gray-600 hover:underline">{t("common.cancel")}</button>
            )}
          </div>
        </div>
      )}
      <ErrorBox message={error} />
    </Section>
  );
}

// ── Accettazione ─────────────────────────────────────────────────────────────

export function AcceptanceSection({ risk, canMonitor }: { risk: Risk; canMonitor: boolean }) {
  const { t, i18n } = useTranslation();
  const qc = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  // Rischio da accettare: la motivazione del trattamento è già la motivazione
  // dell'accettazione, si riprende e si può correggere.
  const [form, setForm] = useState({
    rationale: risk.treatment === "accettare" ? risk.treatment_rationale : "", expires_on: "", body: "", ref: "",
  });
  const [opinionNote, setOpinionNote] = useState("");
  const [revokeReason, setRevokeReason] = useState("");
  const { data: req } = useQuery({
    queryKey: ["risk-acceptance-req", risk.id, risk.current_class],
    queryFn: () => riskApi.acceptanceRequirements(risk.id),
    enabled: risk.status === "completato" && risk.applicable && !!risk.current_class,
    retry: false,
  });
  const { data: history = [] } = useQuery({
    queryKey: ["risk-acceptances", risk.id], queryFn: () => riskApi.acceptances({ risk: risk.id }), retry: false,
  });
  const { data: bodies = [] } = useQuery({ queryKey: ["committees"], queryFn: () => governanceApi.committees(), retry: false });
  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["risk-acceptances"] });
    qc.invalidateQueries({ queryKey: ["risk", risk.id] });
    qc.invalidateQueries({ queryKey: ["risk-register"] });
  };
  const onErr = (e: unknown) => setError(apiError(e, t("risk.errors.generic")));
  const open = history.find(a => a.status === "pending" || a.status === "active");
  const act = useMutation({
    mutationFn: (fn: () => Promise<Acceptance>) => fn(),
    onSuccess: () => { setError(null); refresh(); }, onError: onErr,
  });

  if (!risk.applicable || risk.status !== "completato") {
    return (
      <Section title={t("risk.drawer.acceptance")}>
        <p className="text-xs text-gray-400">{t("risk.drawer.acceptance_needs_completion")}</p>
      </Section>
    );
  }

  return (
    <Section title={t("risk.drawer.acceptance")}>
      {req && (
        <div className="text-xs bg-gray-50 rounded px-3 py-2 mb-2 space-y-0.5">
          {req.not_acceptable ? (
            <p className="text-red-700 font-medium">{t("risk.drawer.not_acceptable_notice")}</p>
          ) : (
            <>
              <p>{t("risk.drawer.who_accepts", {
                cls: t(`risk.classes.${req.class}`),
                roles: req.roles.map(r => t(`risk.acceptance_roles.${r}`, r)).join(" + ") || t("risk.drawer.governing_body"),
              })}</p>
              {req.added_for_self_management && <p className="text-amber-800">{t("risk.drawer.self_management_note")}</p>}
              {req.upper_opinion !== "none" && <p>{t(`risk.drawer.opinion_${req.upper_opinion}`)}</p>}
              {req.requires_body && <p>{t("risk.drawer.body_required")}</p>}
              <p>{t("risk.drawer.max_validity", { months: req.max_months })}</p>
            </>
          )}
        </div>
      )}

      {open ? (
        <div className="border rounded px-3 py-2 text-sm space-y-1">
          <div className="flex items-center gap-2">
            <ClassBadge cls={open.risk_class} />
            <span className="font-medium">{t(`risk.acceptance.status.${open.status}`)}</span>
            <span className="text-xs text-gray-500">{t("risk.drawer.expires", { date: fmt(open.expires_on, i18n.language) })}</span>
          </div>
          <p className="text-xs text-gray-600">{open.rationale}</p>
          <p className="text-[11px] text-gray-500">
            {t("risk.drawer.signatures")}: {open.signatures_display.map(s => `${t(`risk.acceptance_roles.${s.role}`, s.role)} (${s.user ?? "—"})`).join(", ") || "—"}
            {" · "}{t("risk.drawer.required")}: {open.required_roles.map(r => t(`risk.acceptance_roles.${r}`, r)).join(", ") || "—"}
          </p>
          {open.upper_opinion !== "not_required" && (
            <p className="text-[11px] text-gray-500">{t("risk.drawer.ciso_opinion")}: {t(`risk.acceptance.opinion.${open.upper_opinion}`)}
              {open.opinion_by_name ? ` (${open.opinion_by_name})` : ""}</p>
          )}
          {open.requires_body && (
            <p className="text-[11px] text-gray-500">{t("risk.drawer.body")}: {open.body_name ?? "—"} {open.body_resolution_ref}</p>
          )}
          {open.status === "pending" && (
            <div className="flex flex-wrap gap-2 pt-1">
              {open.can_sign && (
                <button onClick={() => act.mutate(() => riskApi.signAcceptance(open.id))} className="px-2 py-1 border rounded text-xs">
                  {t("risk.drawer.sign")}
                </button>
              )}
              {open.can_give_opinion && (
                <>
                  <input value={opinionNote} onChange={e => setOpinionNote(e.target.value)} className={`${inputCls} w-48`}
                    placeholder={t("risk.drawer.opinion_note")} />
                  <button onClick={() => act.mutate(() => riskApi.giveOpinion(open.id, true, opinionNote))}
                    className="px-2 py-1 border border-green-300 text-green-700 rounded text-xs">{t("risk.drawer.favorable")}</button>
                  <button onClick={() => act.mutate(() => riskApi.giveOpinion(open.id, false, opinionNote))}
                    className="px-2 py-1 border border-red-300 text-red-700 rounded text-xs">{t("risk.drawer.unfavorable")}</button>
                </>
              )}
              {open.requires_body && !open.body_resolution_ref && canMonitor && (
                <>
                  <select value={form.body} onChange={e => setForm({ ...form, body: e.target.value })} className={`${inputCls} w-40`}>
                    <option value="">{t("risk.cycle.choose_body")}</option>
                    {bodies.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
                  </select>
                  <input value={form.ref} onChange={e => setForm({ ...form, ref: e.target.value })} className={`${inputCls} w-40`}
                    placeholder={t("risk.drawer.resolution_ref")} />
                  <button onClick={() => act.mutate(() => riskApi.bodyDecision(open.id, form.body, form.ref))}
                    className="px-2 py-1 border rounded text-xs">{t("risk.drawer.record_decision")}</button>
                </>
              )}
            </div>
          )}
          {canMonitor && (
            <div className="flex gap-2 pt-1">
              <input value={revokeReason} onChange={e => setRevokeReason(e.target.value)} className={`${inputCls} w-56`}
                placeholder={t("risk.drawer.revoke_reason")} />
              <button onClick={() => act.mutate(() => riskApi.revokeAcceptance(open.id, revokeReason))} disabled={!revokeReason.trim()}
                className="px-2 py-1 border border-red-300 text-red-700 rounded text-xs disabled:opacity-50">{t("risk.drawer.revoke")}</button>
            </div>
          )}
        </div>
      ) : canMonitor && req && !req.not_acceptable ? (
        <div className="border rounded p-2 bg-gray-50">
          <Field label={t("risk.drawer.acceptance_rationale")}>
            <p className="text-[11px] text-gray-500 mb-1">
              {t(risk.treatment === "accettare" ? "risk.drawer.acceptance_rationale_from_treatment" : "risk.drawer.acceptance_rationale_while_treating")}
            </p>
            <textarea value={form.rationale} onChange={e => setForm({ ...form, rationale: e.target.value })} rows={3} className={inputCls} />
          </Field>
          <div className="grid grid-cols-2 gap-2">
            <Field label={t("risk.drawer.acceptance_expiry")}>
              <input type="date" value={form.expires_on} onChange={e => setForm({ ...form, expires_on: e.target.value })} className={inputCls} />
            </Field>
            {req.requires_body && (
              <Field label={t("risk.drawer.body")}>
                <select value={form.body} onChange={e => setForm({ ...form, body: e.target.value })} className={inputCls}>
                  <option value="">{t("risk.cycle.choose_body")}</option>
                  {bodies.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
                </select>
              </Field>
            )}
          </div>
          <button
            onClick={() => act.mutate(() => riskApi.requestAcceptance({
              risk: risk.id, rationale: form.rationale, expires_on: form.expires_on || undefined,
              body: form.body || undefined, body_resolution_ref: form.ref || undefined,
            }))}
            disabled={!form.rationale.trim()}
            className="px-3 py-1.5 bg-primary-600 text-white rounded text-sm disabled:opacity-50"
          >
            {t("risk.drawer.request_acceptance")}
          </button>
        </div>
      ) : null}

      {history.filter(a => a !== open).length > 0 && (
        <details className="mt-2 text-xs">
          <summary className="cursor-pointer text-gray-500">{t("risk.drawer.acceptance_history")}</summary>
          <ul className="mt-1 space-y-0.5">
            {history.filter(a => a !== open).map(a => (
              <li key={a.id} className="text-gray-600">
                {fmt(a.created_at, i18n.language)} · {t(`risk.classes.${a.risk_class}`)} · {t(`risk.acceptance.status.${a.status}`)}
                {a.close_reason ? ` — ${a.close_reason}` : ""}
              </li>
            ))}
          </ul>
        </details>
      )}
      <ErrorBox message={error} />
    </Section>
  );
}

// ── Rischi di gruppo: impatto locale ─────────────────────────────────────────

export function LocalImpactSection({ risk, registerId, orgScope }: { risk: Risk; registerId: string | null; orgScope: boolean }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const selectedPlant = useAuthStore(s => s.selectedPlant);
  const [impact, setImpact] = useState(4);
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const { data: reports = [] } = useQuery({
    queryKey: ["risk-local-impact", risk.id], queryFn: () => riskApi.localImpactReports({ risk: risk.id }), retry: false,
  });
  const refresh = () => qc.invalidateQueries({ queryKey: ["risk-local-impact", risk.id] });
  const site = registerId ?? selectedPlant?.id ?? null;
  const report = useMutation({
    mutationFn: () => riskApi.reportLocalImpact({ risk: risk.id, plant: site!, local_impact: impact, note }),
    onSuccess: () => { setNote(""); setError(null); refresh(); },
    onError: e => setError(apiError(e, t("risk.errors.generic"))),
  });
  const ack = useMutation({ mutationFn: (id: string) => riskApi.acknowledgeLocalImpact(id), onSuccess: refresh });

  return (
    <Section title={t("risk.drawer.local_impact")}>
      <ul className="space-y-1 mb-2 text-sm">
        {reports.map(r => (
          <li key={r.id} className="border rounded px-2 py-1">
            <span className="font-medium">{r.plant_name}</span> · {t("risk.drawer.local_impact_value", { value: r.local_impact })}
            <span className="block text-xs text-gray-600">{r.note}</span>
            <span className="text-[11px] text-gray-500">{t(`risk.drawer.local_status.${r.status}`)}</span>
            {orgScope && r.status === "aperta" && (
              <button onClick={() => ack.mutate(r.id)} className="ml-2 text-[11px] text-primary-600 hover:underline">{t("risk.drawer.acknowledge")}</button>
            )}
          </li>
        ))}
      </ul>
      {risk.is_inherited && site && (
        <div className="flex gap-2 items-start">
          <select value={impact} onChange={e => setImpact(Number(e.target.value))} className={`${inputCls} w-20`}>
            {[1, 2, 3, 4, 5].map(n => <option key={n} value={n}>{n}</option>)}
          </select>
          <input value={note} onChange={e => setNote(e.target.value)} className={inputCls} placeholder={t("risk.drawer.local_impact_note")} />
          <button onClick={() => report.mutate()} disabled={!note.trim()} className="px-2 py-1.5 border rounded text-sm disabled:opacity-50">
            {t("risk.drawer.report")}
          </button>
        </div>
      )}
      <ErrorBox message={error} />
    </Section>
  );
}
