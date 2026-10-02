import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { AiSuggestion } from "../../components/ui/AiSuggestion";
import {
  IMPACT_DIMENSIONS, apiError, riskApi, type AiDraftProposal, type AiMeasure, type RegisterReview, type Risk,
} from "../../api/endpoints/risk";
import type { EvaluationState } from "./EvaluationForm";
import { ErrorBox } from "./RiskUi";
import type { RegisterId } from "./RiskPage";

// Supporto IA al risk assessment (M20). Regola 9: ogni proposta resta una
// proposta finché l'utente non la accetta; l'esito (accettata/ignorata) va nel
// registro delle interazioni IA. La classe resta calcolata dalla matrice.

const AiBadge = () => {
  const { t } = useTranslation();
  return <span className="text-[10px] bg-amber-400 text-white px-1.5 py-0.5 rounded font-bold">{t("ai.ai_badge")}</span>;
};

function AiModal({ title, children, onClose, under = false }: {
  title: string; children: React.ReactNode; onClose: () => void; under?: boolean;
}) {
  // `under`: resta sotto la scheda del rischio (z-50) aperta da un suo link.
  return (
    <div className={`fixed inset-0 ${under ? "z-40" : "z-[60]"} flex items-center justify-center bg-black/30 p-4`} role="dialog" aria-modal="true" aria-label={title}>
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[85vh] flex flex-col text-gray-800">
        <div className="flex items-center justify-between px-5 pt-4 pb-2 border-b">
          <h3 className="text-base font-semibold flex items-center gap-2"><AiBadge /> {title}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">×</button>
        </div>
        <div className="overflow-y-auto px-5 py-3">{children}</div>
      </div>
    </div>
  );
}

const feedback = (id: string | null, action: "confirm" | "ignore", text = "") => {
  if (id) riskApi.aiFeedback(id, action, text).catch(() => undefined);
};

// ── 1. Bozza della valutazione ─────────────────────────────────────────────

type DraftKey = keyof AiDraftProposal;
const DRAFT_ORDER: DraftKey[] = [
  "vulnerability", "consequence", "probability_method", "probability", "probability_rationale",
  ...IMPACT_DIMENSIONS.map(d => `impact_${d}` as DraftKey), "impact_rationale",
  "treatment", "treatment_rationale", "expected_probability", "expected_impact",
];

export function AiDraftButton({ risk, form, onApply }: {
  risk: Risk; form: EvaluationState; onApply: (next: EvaluationState) => void;
}) {
  const { t } = useTranslation();
  const [proposal, setProposal] = useState<AiDraftProposal | null>(null);
  const [interaction, setInteraction] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<DraftKey>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const ask = useMutation({
    mutationFn: () => riskApi.aiDraft(risk.id),
    onSuccess: res => {
      setProposal(res.proposal); setInteraction(res.interaction_id); setError(null);
      setSelected(new Set(DRAFT_ORDER.filter(k => res.proposal[k] !== undefined)));
    },
    onError: e => setError(apiError(e, t("risk.ai.error"))),
  });

  const label = (k: DraftKey) => k.startsWith("impact_") && k !== "impact_rationale"
    ? `${t("risk.drawer.impact_dimensions")} · ${t(`risk.dimensions.${k.slice(7)}`)}` : t(`risk.drawer.${k}`);
  const show = (k: DraftKey, v: unknown) => {
    if (v === null || v === undefined || v === "") return "—";
    if (k === "probability_method") return t(v === "fer" ? "risk.drawer.method_fer" : "risk.drawer.method_frequency");
    if (k === "treatment") return t(`risk.treatment_${v}`);
    return String(v);
  };
  const keys = proposal ? DRAFT_ORDER.filter(k => proposal[k] !== undefined) : [];
  const apply = () => {
    const chosen = keys.filter(k => selected.has(k));
    onApply({ ...form, ...Object.fromEntries(chosen.map(k => [k, proposal![k]])) });
    feedback(interaction, "confirm", chosen.join(", "));
    setProposal(null);
  };
  const ignore = () => { feedback(interaction, "ignore"); setProposal(null); };

  return (
    <div className="mb-3">
      <button onClick={() => ask.mutate()} disabled={ask.isPending}
        className="text-xs px-2.5 py-1 rounded border border-amber-300 bg-amber-50 text-amber-800 hover:bg-amber-100 disabled:opacity-50">
        ✨ {t(ask.isPending ? "risk.ai.working" : "risk.ai.draft")}
      </button>
      <ErrorBox message={error} />
      {proposal && (
        <AiModal title={t("risk.ai.draft_title")} onClose={ignore}>
          <p className="text-xs text-gray-500 mb-2">{t("risk.ai.draft_hint")}</p>
          {keys.length === 0 ? <p className="text-sm text-gray-500">{t("risk.ai.nothing")}</p> : (
            <ul className="divide-y text-sm">
              {keys.map(k => (
                <li key={k} className="py-1.5 flex gap-2">
                  <input type="checkbox" className="mt-1" checked={selected.has(k)}
                    onChange={e => setSelected(s => { const n = new Set(s); if (e.target.checked) n.add(k); else n.delete(k); return n; })} />
                  <div className="min-w-0">
                    <p className="text-xs text-gray-500">{label(k)}
                      <span className="ml-2 text-gray-400">{t("risk.ai.current")}: {show(k, form[k as keyof EvaluationState])}</span>
                    </p>
                    <p className="whitespace-pre-wrap">{show(k, proposal[k])}</p>
                  </div>
                </li>
              ))}
            </ul>
          )}
          <p className="text-[11px] text-gray-500 mt-2">{t("ai.generated_label")} {t("risk.ai.class_note")}</p>
          <div className="flex gap-2 justify-end mt-3">
            <button onClick={ignore} className="px-3 py-1.5 border rounded text-sm">{t("ai.ignore")}</button>
            <button onClick={apply} disabled={!selected.size} className="px-3 py-1.5 bg-green-600 text-white rounded text-sm disabled:opacity-50">
              {t("risk.ai.apply_selected")}
            </button>
          </div>
        </AiModal>
      )}
    </div>
  );
}

// ── 2. Misure del piano di trattamento ─────────────────────────────────────

export function AiMeasuresButton({ risk }: { risk: Risk }) {
  const { t, i18n } = useTranslation();
  const qc = useQueryClient();
  const [measures, setMeasures] = useState<AiMeasure[] | null>(null);
  const [added, setAdded] = useState<number[]>([]);
  const [interaction, setInteraction] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const ask = useMutation({
    mutationFn: () => riskApi.aiMeasures(risk.id),
    onSuccess: res => { setMeasures(res.measures); setInteraction(res.interaction_id); setAdded([]); setError(null); },
    onError: e => setError(apiError(e, t("risk.ai.error"))),
  });
  const add = useMutation({
    mutationFn: (i: number) => riskApi.createPlan({
      assessment: risk.id, action: measures![i].action, due_date: measures![i].due_date,
      expected_effect: measures![i].expected_effect, control_instance: measures![i].control_instance,
      owner: risk.treatment_owner, owner_external: risk.treatment_owner_external,
    }),
    onSuccess: (_r, i) => {
      setAdded(a => [...a, i]);
      qc.invalidateQueries({ queryKey: ["risk-plans", risk.id] });
      qc.invalidateQueries({ queryKey: ["risk-register"] });
    },
    onError: e => setError(apiError(e, t("risk.errors.generic"))),
  });
  const close = () => {
    feedback(interaction, added.length ? "confirm" : "ignore",
      added.map(i => measures![i].action).join("\n"));
    setMeasures(null);
  };

  return (
    <div className="mt-2">
      <button onClick={() => ask.mutate()} disabled={ask.isPending}
        className="text-xs px-2.5 py-1 rounded border border-amber-300 bg-amber-50 text-amber-800 hover:bg-amber-100 disabled:opacity-50">
        ✨ {t(ask.isPending ? "risk.ai.working" : "risk.ai.measures")}
      </button>
      {!measures && <ErrorBox message={error} />}
      {measures && (
        <AiModal title={t("risk.ai.measures_title")} onClose={close}>
          <p className="text-xs text-gray-500 mb-2">{t("risk.ai.measures_hint")}</p>
          {measures.length === 0 && <p className="text-sm text-gray-500">{t("risk.ai.nothing")}</p>}
          <ul className="space-y-2">
            {measures.map((m, i) => (
              <li key={i} className="border rounded p-2 text-sm">
                <p className="font-medium">{m.action}</p>
                <p className="text-xs text-gray-500">
                  {t("risk.drawer.due")}: {new Date(m.due_date).toLocaleDateString(i18n.language)}
                  {m.expected_effect && ` · ${t(`risk.effect.${m.expected_effect}`)}`}
                  {m.control_label && ` · ${m.control_label}`}
                </p>
                {m.rationale && <p className="text-xs text-gray-600 mt-0.5">{m.rationale}</p>}
                <button onClick={() => add.mutate(i)} disabled={added.includes(i) || add.isPending}
                  className="mt-1 text-xs px-2 py-0.5 rounded bg-green-600 text-white disabled:opacity-50">
                  {t(added.includes(i) ? "risk.ai.added" : "risk.ai.add_to_plan")}
                </button>
              </li>
            ))}
          </ul>
          <ErrorBox message={error} />
          <p className="text-[11px] text-gray-500 mt-2">{t("ai.generated_label")}</p>
          <div className="flex justify-end mt-3">
            <button onClick={close} className="px-3 py-1.5 border rounded text-sm">{t("common.close")}</button>
          </div>
        </AiModal>
      )}
    </div>
  );
}

// ── 3. Revisione di coerenza ───────────────────────────────────────────────

export function ReviewDialog({ registerId, onOpen, onClose }: {
  registerId: RegisterId; onOpen: (id: string) => void; onClose: () => void;
}) {
  const { t } = useTranslation();
  const [withAi, setWithAi] = useState(false);
  const [review, setReview] = useState<RegisterReview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const run = useMutation({
    mutationFn: () => riskApi.review(registerId, withAi),
    onSuccess: res => { setReview(res); setError(null); },
    onError: e => setError(apiError(e, t("risk.ai.error"))),
  });
  const close = () => {
    if (review?.ai) feedback(review.ai.interaction_id, "confirm", `${review.ai.findings.length}`);
    onClose();
  };
  const open = (id: string) => { onOpen(id); };

  return (
    <AiModal title={t("risk.ai.review_title")} onClose={close} under>
      <p className="text-xs text-gray-500 mb-2">{t("risk.ai.review_hint")}</p>
      <label className="flex items-center gap-2 text-sm mb-2">
        <input type="checkbox" checked={withAi} onChange={e => setWithAi(e.target.checked)} /> {t("risk.ai.review_with_ai")}
      </label>
      <button onClick={() => run.mutate()} disabled={run.isPending} className="px-3 py-1.5 bg-primary-600 text-white rounded text-sm disabled:opacity-50">
        {t(run.isPending ? "risk.ai.working" : "risk.ai.review_run")}
      </button>
      <ErrorBox message={error} />
      {review && (
        <div className="mt-3 space-y-3">
          <div>
            <h4 className="text-sm font-semibold mb-1">{t("risk.ai.review_rules")} · {review.checks.length}</h4>
            {review.checks.length === 0 ? <p className="text-sm text-green-700">{t("risk.ai.review_ok")}</p> : (
              <ul className="divide-y text-sm">
                {review.checks.map((f, i) => (
                  <li key={i} className="py-1.5">
                    <span className={`text-[10px] px-1.5 py-0.5 rounded mr-2 ${f.severity === "error" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-800"}`}>
                      {t(`risk.ai.severity.${f.severity}`)}
                    </span>
                    <button onClick={() => open(f.risk_id)} className="font-medium hover:underline">{f.risk_name}</button>
                    <span className="block text-xs text-gray-600">
                      {t(`risk.ai.checks.${f.code}`, {
                        ...f.params, field: f.params.field ? t(`risk.drawer.${f.params.field}`) : "",
                      })}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
          {review.ai && (
            <div>
              <h4 className="text-sm font-semibold mb-1 flex items-center gap-2"><AiBadge /> {t("risk.ai.review_ai")} · {review.ai.findings.length}</h4>
              {review.ai.findings.length === 0 ? <p className="text-sm text-green-700">{t("risk.ai.review_ok")}</p> : (
                <ul className="divide-y text-sm">
                  {review.ai.findings.map((f, i) => (
                    <li key={i} className="py-1.5">
                      <button onClick={() => open(f.risk_id)} className="font-medium hover:underline">{f.risk_name}</button>
                      <span className="block text-xs text-gray-700">{f.issue}</span>
                      {f.suggestion && <span className="block text-xs text-gray-500">→ {f.suggestion}</span>}
                    </li>
                  ))}
                </ul>
              )}
              <p className="text-[11px] text-gray-500 mt-1">{t("ai.generated_label")}</p>
            </div>
          )}
        </div>
      )}
    </AiModal>
  );
}

// ── 4. Sintesi per l'organo ────────────────────────────────────────────────

export function SummaryDialog({ registerId, onClose }: { registerId: RegisterId; onClose: () => void }) {
  const { t } = useTranslation();
  const [result, setResult] = useState<{ summary: string; interaction_id: string | null } | null>(null);
  const [final, setFinal] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const run = useMutation({
    mutationFn: () => riskApi.aiSummary(registerId),
    onSuccess: res => { setResult(res); setError(null); },
    onError: e => setError(apiError(e, t("risk.ai.error"))),
  });
  const close = () => {
    if (result && final === null) feedback(result.interaction_id, "ignore");
    onClose();
  };

  return (
    <AiModal title={t("risk.ai.summary_title")} onClose={close}>
      <p className="text-xs text-gray-500 mb-2">{t("risk.ai.summary_hint")}</p>
      {!result && (
        <button onClick={() => run.mutate()} disabled={run.isPending} className="px-3 py-1.5 bg-primary-600 text-white rounded text-sm disabled:opacity-50">
          {t(run.isPending ? "risk.ai.working" : "risk.ai.summary_run")}
        </button>
      )}
      <ErrorBox message={error} />
      {result && final === null && (
        <AiSuggestion suggestionId={result.interaction_id ?? ""} output={result.summary}
          onAccept={text => { setFinal(text); feedback(result.interaction_id, "confirm", text); }}
          onIgnore={() => { feedback(result.interaction_id, "ignore"); onClose(); }} />
      )}
      {final !== null && (
        <div>
          <textarea readOnly value={final} rows={12} className="w-full border rounded p-2 text-sm" />
          <div className="flex justify-end gap-2 mt-2">
            <button onClick={() => navigator.clipboard?.writeText(final)} className="px-3 py-1.5 border rounded text-sm">{t("risk.ai.copy")}</button>
            <button onClick={onClose} className="px-3 py-1.5 bg-primary-600 text-white rounded text-sm">{t("common.close")}</button>
          </div>
        </div>
      )}
    </AiModal>
  );
}
