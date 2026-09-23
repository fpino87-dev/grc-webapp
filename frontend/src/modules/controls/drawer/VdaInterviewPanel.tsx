import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  controlsApi,
  type VdaCoverage,
  type VdaInterview,
  type VdaInterviewDraft,
  type VdaInterviewRequirement,
  type VdaRequirementLevel,
} from "../../../api/endpoints/controls";

const LEVEL_STYLE: Record<VdaRequirementLevel, string> = {
  must: "bg-red-100 text-red-800",
  high: "bg-orange-100 text-orange-800",
  very_high: "bg-purple-100 text-purple-800",
  should: "bg-gray-100 text-gray-700",
};

const COVERAGE_STYLE: Record<VdaCoverage, string> = {
  covered: "bg-green-100 text-green-800",
  partial: "bg-amber-100 text-amber-800",
  missing: "bg-red-100 text-red-800",
};

const MANDATORY: VdaRequirementLevel[] = ["must", "high", "very_high"];
const K = "controls.drawer.evaluation.interview";

function errorMessage(e: unknown, fallback: string): string {
  return (e as { response?: { data?: { error?: string } } })?.response?.data?.error ?? fallback;
}

function RequirementLine({ r, coverage }: { r: VdaInterviewRequirement; coverage?: VdaCoverage }) {
  const { t } = useTranslation();
  return (
    <li className="text-xs text-gray-600 space-x-1">
      <span className={`inline-block text-[10px] font-semibold px-1.5 rounded ${LEVEL_STYLE[r.level]}`}>
        {t(`${K}.levels.${r.level}`)}{r.source ? ` · ${r.source}` : ""}
      </span>
      {coverage && (
        <span className={`inline-block text-[10px] font-semibold px-1.5 rounded ${COVERAGE_STYLE[coverage]}`}>
          {t(`${K}.coverage.${coverage}`)}
        </span>
      )}
      <span className="italic">{r.text_en}</span>
    </li>
  );
}

/**
 * Intervista guidata VDA ISA "da auditor": poche domande per tema con
 * contesto ed esempio, verifica dell'auditor (max 2 giri) con domande di
 * approfondimento, bozza in inglese dall'intera conversazione.
 * La bozza non viene salvata qui: `onUseDraft` la copia nel campo
 * descrizione, dove l'utente la rivede e la salva (human-in-the-loop).
 */
export function VdaInterviewPanel({
  instanceId,
  onUseDraft,
}: {
  instanceId: string;
  onUseDraft: (text: string, interactionId: string | null) => void;
}) {
  const { t, i18n } = useTranslation();
  const qc = useQueryClient();
  const uiLang = (i18n.language || "it").slice(0, 2);
  const queryKey = ["vda-interview", instanceId, uiLang];
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [fuAnswers, setFuAnswers] = useState<Record<string, string>>({});
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const [draft, setDraft] = useState<VdaInterviewDraft | null>(null);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");
  const [used, setUsed] = useState(false);
  const [confirmReset, setConfirmReset] = useState(false);

  // staleTime Infinity: un refetch non deve sovrascrivere ciò che si sta scrivendo.
  const { data, isLoading, isError } = useQuery({
    queryKey,
    queryFn: () => controlsApi.getVdaInterview(instanceId, uiLang),
    staleTime: Infinity,
  });

  useEffect(() => {
    if (data) {
      setAnswers(data.answers);
      setFuAnswers(data.followup_answers);
    }
  }, [data]);

  const payload = (extra: { reset_reviews?: boolean } = {}) => ({
    answers, followup_answers: fuAnswers, lang: data?.lang ?? uiLang, ...extra,
  });
  const onInterview = (d: VdaInterview) => {
    qc.setQueryData(queryKey, d);
    setError("");
  };
  const onFail = (e: unknown) => setError(errorMessage(e, t("common.error")));

  const saveMutation = useMutation({
    mutationFn: (reset: boolean) => controlsApi.saveVdaInterview(instanceId, payload({ reset_reviews: reset })),
    onSuccess: (d) => {
      onInterview(d);
      setConfirmReset(false);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    },
    onError: onFail,
  });

  const reviewMutation = useMutation({
    mutationFn: () => controlsApi.reviewVdaInterview(instanceId, payload()),
    onSuccess: onInterview,
    onError: onFail,
  });

  const draftMutation = useMutation({
    mutationFn: () => controlsApi.draftVdaInterview(instanceId, payload()),
    onSuccess: (d) => {
      setError("");
      setDraft(d);
      setUsed(false);
    },
    onError: onFail,
  });

  const reqById = useMemo(
    () => Object.fromEntries((data?.requirements ?? []).map(r => [r.id, r])),
    [data],
  );

  if (isLoading) {
    return <p className="text-xs text-gray-500 italic">{t(`${K}.loading`)}</p>;
  }
  if (isError || !data) {
    return <p className="text-xs text-red-600">{t("common.error")}</p>;
  }

  const toggle = (key: string) => setOpen(o => ({ ...o, [key]: !o[key] }));
  const latest = data.reviews[data.reviews.length - 1];
  const coverage = latest?.coverage ?? {};
  const answered = data.topics.filter(tp => (answers[tp.id] ?? "").trim()).length;
  const roundsLeft = data.max_rounds - data.rounds_used;
  const busy = saveMutation.isPending || reviewMutation.isPending || draftMutation.isPending;
  const gapsCount = (draft?.gaps ?? []).filter(id => MANDATORY.includes(reqById[id]?.level)).length;

  if (data.topics.length === 0) {
    return (
      <div className="space-y-2 border-t border-purple-200 pt-3">
        <p className="text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded px-2 py-1">
          {t(`${K}.ai_${data.ai_error || "unavailable"}`)}
        </p>
        <p className="text-xs font-semibold text-gray-600">{t(`${K}.requirements_all`)}</p>
        <ul className="space-y-1">
          {data.requirements.map(r => <RequirementLine key={r.id} r={r} />)}
        </ul>
      </div>
    );
  }

  const counts = { covered: 0, partial: 0, missing: 0 } as Record<VdaCoverage, number>;
  Object.values(coverage).forEach(v => { counts[v] += 1; });
  const openReqs = data.requirements.filter(r => coverage[r.id] && coverage[r.id] !== "covered");
  const supported = latest?.maturity.supported_level;

  return (
    <div className="space-y-3 border-t border-purple-200 pt-3">
      <p className="text-xs text-gray-600">{t(`${K}.intro`)}</p>
      {data.lang !== uiLang && (
        <p className="text-xs text-gray-500 italic">{t(`${K}.lang_locked`, { lang: data.lang.toUpperCase() })}</p>
      )}
      <p className="text-xs font-medium text-gray-600">
        {t(`${K}.answered_count`, { answered, total: data.topics.length })}
      </p>

      {/* Domande per tema */}
      <ol className="space-y-3">
        {data.topics.map((tp, idx) => (
          <li key={tp.id} className="border border-gray-200 rounded p-2 space-y-1.5 bg-white">
            <p className="text-[11px] font-semibold text-purple-700 uppercase">{t(`${K}.topic_label`, { n: idx + 1 })}</p>
            <p className="text-sm font-medium text-gray-900">{tp.question}</p>
            {tp.auditor_intent && (
              <p className="text-xs text-gray-600">
                <span className="font-semibold">{t(`${K}.auditor_intent`)}:</span> {tp.auditor_intent}
              </p>
            )}
            {tp.what_to_mention.length > 0 && (
              <div className="text-xs text-gray-600">
                <span className="font-semibold">{t(`${K}.what_to_mention`)}:</span>
                <ul className="list-disc pl-5">
                  {tp.what_to_mention.map((m, i) => <li key={i}>{m}</li>)}
                </ul>
              </div>
            )}
            <div className="flex flex-wrap gap-x-3">
              {tp.example && (
                <button type="button" onClick={() => toggle(`ex-${tp.id}`)} className="text-[11px] text-purple-700 hover:underline">
                  {open[`ex-${tp.id}`] ? "▾" : "▸"} {t(`${K}.example_toggle`)}
                </button>
              )}
              <button type="button" onClick={() => toggle(`req-${tp.id}`)} className="text-[11px] text-purple-700 hover:underline">
                {open[`req-${tp.id}`] ? "▾" : "▸"} {t(`${K}.requirements_toggle`, { count: tp.req_ids.length })}
              </button>
            </div>
            {tp.example && open[`ex-${tp.id}`] && (
              <div className="text-xs bg-gray-50 border border-dashed border-gray-300 rounded px-2 py-1 space-y-0.5">
                <p className="text-[11px] text-gray-500">{t(`${K}.example_note`)}</p>
                <p className="italic text-gray-600">{tp.example}</p>
              </div>
            )}
            {open[`req-${tp.id}`] && (
              <ul className="space-y-1">
                {tp.req_ids.map(id => reqById[id] && <RequirementLine key={id} r={reqById[id]} coverage={coverage[id]} />)}
              </ul>
            )}
            <textarea
              value={answers[tp.id] ?? ""}
              onChange={e => { setAnswers(a => ({ ...a, [tp.id]: e.target.value })); setSaved(false); }}
              placeholder={t(`${K}.answer_placeholder`)}
              maxLength={2000}
              className="w-full border rounded px-2 py-1.5 text-sm"
              rows={4}
            />
          </li>
        ))}
      </ol>

      {/* Verifica dell'auditor (ultimo giro) */}
      {latest && (
        <div className="border border-indigo-200 bg-indigo-50/40 rounded p-2 space-y-2">
          <p className="text-xs font-semibold text-indigo-800">
            {t(`${K}.review_title`, { round: latest.round, max: data.max_rounds })}
          </p>
          <p className="text-[11px] text-gray-500">{t("ai.generated_label")}</p>
          {latest.summary && <p className="text-sm text-gray-800">{latest.summary}</p>}
          <p className="text-xs space-x-2">
            <span className="text-green-700">✓ {t(`${K}.coverage_covered`, { count: counts.covered })}</span>
            <span className="text-amber-700">◐ {t(`${K}.coverage_partial`, { count: counts.partial })}</span>
            <span className="text-red-700">✗ {t(`${K}.coverage_missing`, { count: counts.missing })}</span>
          </p>
          {openReqs.length > 0 && (
            <>
              <button type="button" onClick={() => toggle("open-reqs")} className="text-[11px] text-indigo-700 hover:underline">
                {open["open-reqs"] ? "▾" : "▸"} {t(`${K}.coverage_details`)}
              </button>
              {open["open-reqs"] && (
                <ul className="space-y-1">
                  {openReqs.map(r => <RequirementLine key={r.id} r={r} coverage={coverage[r.id]} />)}
                </ul>
              )}
            </>
          )}
          {supported !== null && supported !== undefined && (
            <div className={`text-xs rounded px-2 py-1 ${supported < data.declared_maturity ? "bg-red-50 border border-red-200 text-red-800" : "bg-white border border-gray-200 text-gray-700"}`}>
              <p className="font-semibold">
                {t(`${K}.maturity_supported`, { supported, declared: data.declared_maturity })}
              </p>
              {latest.maturity.comment && <p>{latest.maturity.comment}</p>}
              {supported < data.declared_maturity && <p className="font-medium">⚠ {t(`${K}.maturity_gap`)}</p>}
            </div>
          )}
          {latest.evidence.length > 0 && (
            <div className="text-xs">
              <p className="font-semibold text-gray-700">{t(`${K}.evidence_title`)}</p>
              <ul className="space-y-0.5">
                {latest.evidence.map((ev, i) => (
                  <li key={i}>
                    {ev.linked
                      ? <span className="text-green-700">✓ </span>
                      : <span className="text-amber-700">○ </span>}
                    {ev.item}{" "}
                    <span className="text-gray-500">
                      ({ev.linked ? t(`${K}.evidence_linked`, { name: ev.linked }) : t(`${K}.evidence_missing`)})
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Domande di approfondimento di tutti i giri */}
      {data.followups.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-semibold text-indigo-800">{t(`${K}.followups_title`)}</p>
          {data.followups.map(f => (
            <div key={f.id} className="space-y-1">
              <p className="text-sm text-gray-800">
                <span className="text-[10px] font-semibold text-indigo-700 mr-1">{t(`${K}.followup_round`, { round: f.round })}</span>
                {f.question}
              </p>
              <textarea
                value={fuAnswers[f.id] ?? ""}
                onChange={e => { setFuAnswers(a => ({ ...a, [f.id]: e.target.value })); setSaved(false); }}
                placeholder={t(`${K}.followup_placeholder`)}
                maxLength={2000}
                className="w-full border rounded px-2 py-1.5 text-sm"
                rows={2}
              />
            </div>
          ))}
        </div>
      )}

      {error && <p className="text-xs text-red-600 whitespace-pre-line">{error}</p>}

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => saveMutation.mutate(false)}
          disabled={busy}
          className="flex-1 py-1.5 border border-purple-300 text-purple-700 rounded text-xs hover:bg-purple-50 disabled:opacity-50"
        >
          {saveMutation.isPending ? t("common.saving") : saved ? "✓ " + t(`${K}.answers_saved`) : t(`${K}.save_answers`)}
        </button>
        <button
          type="button"
          onClick={() => reviewMutation.mutate()}
          disabled={busy || answered === 0 || roundsLeft <= 0}
          className="flex-1 py-1.5 bg-indigo-600 text-white rounded text-xs hover:bg-indigo-700 disabled:opacity-50"
        >
          {reviewMutation.isPending ? t(`${K}.reviewing`) : t(`${K}.review`, { used: data.rounds_used, max: data.max_rounds })}
        </button>
        <button
          type="button"
          onClick={() => draftMutation.mutate()}
          disabled={busy || answered === 0}
          className="flex-1 py-1.5 bg-purple-600 text-white rounded text-xs hover:bg-purple-700 disabled:opacity-50"
        >
          {draftMutation.isPending ? t(`${K}.generating`) : t(`${K}.generate`)}
        </button>
      </div>
      {data.rounds_used === 0 && answered > 0 && (
        <p className="text-[11px] text-gray-500">{t(`${K}.no_review_hint`)}</p>
      )}
      {roundsLeft <= 0 && (
        <div className="text-[11px] text-gray-600 space-y-1">
          <p>{t(`${K}.rounds_exhausted`, { max: data.max_rounds })}</p>
          {!confirmReset ? (
            <button type="button" onClick={() => setConfirmReset(true)} className="text-indigo-700 hover:underline">
              {t(`${K}.reset`)}
            </button>
          ) : (
            <button type="button" onClick={() => saveMutation.mutate(true)} disabled={busy} className="text-red-700 font-medium hover:underline">
              {t(`${K}.reset_confirm`)}
            </button>
          )}
        </div>
      )}

      {draft && (
        <div className="space-y-2 border border-purple-200 rounded p-2 bg-white">
          <p className="text-[11px] text-gray-500">
            {t("ai.generated_label")}{draft.model ? ` — ${draft.provider}/${draft.model}` : ""}
          </p>
          {gapsCount > 0 && (
            <p className="text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded px-2 py-1">
              ⚠ {t(`${K}.gaps_warning`, { count: gapsCount })}
            </p>
          )}
          <p className="text-xs font-semibold text-gray-600">{t(`${K}.draft_title`)}</p>
          <p className="text-sm text-gray-800 whitespace-pre-wrap">{draft.draft_en}</p>
          {draft.draft_local && data.lang !== "en" && (
            <>
              <p className="text-xs font-semibold text-gray-600">{t(`${K}.draft_local_title`)}</p>
              <p className="text-xs text-gray-600 whitespace-pre-wrap">{draft.draft_local}</p>
            </>
          )}
          <button
            type="button"
            onClick={() => { onUseDraft(draft.draft_en, draft.interaction_id); setUsed(true); }}
            disabled={!draft.draft_en}
            className="w-full py-1.5 bg-purple-600 text-white rounded text-xs hover:bg-purple-700 disabled:opacity-50"
          >
            {t(`${K}.use_draft`)}
          </button>
          {used && <p className="text-xs text-green-700">{t(`${K}.draft_used`)}</p>}
        </div>
      )}
    </div>
  );
}
