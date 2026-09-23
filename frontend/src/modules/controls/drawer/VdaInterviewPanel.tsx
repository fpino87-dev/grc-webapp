import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  controlsApi,
  type VdaInterview,
  type VdaInterviewDraft,
  type VdaRequirementLevel,
} from "../../../api/endpoints/controls";

const LEVEL_STYLE: Record<VdaRequirementLevel, string> = {
  must: "bg-red-100 text-red-800",
  high: "bg-orange-100 text-orange-800",
  very_high: "bg-purple-100 text-purple-800",
  should: "bg-gray-100 text-gray-700",
};

// Livelli per cui una risposta mancante lascia un [TO BE COMPLETED] nella bozza.
const MANDATORY: VdaRequirementLevel[] = ["must", "high", "very_high"];

function errorMessage(e: unknown, fallback: string): string {
  return (e as { response?: { data?: { error?: string } } })?.response?.data?.error ?? fallback;
}

/**
 * Intervista guidata VDA ISA: una domanda per requisito nella lingua
 * dell'utente, bozza in inglese generata dall'IA solo dalle risposte.
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
  const lang = (i18n.language || "it").slice(0, 2);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [openOriginal, setOpenOriginal] = useState<Record<string, boolean>>({});
  const [draft, setDraft] = useState<VdaInterviewDraft | null>(null);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");
  const [used, setUsed] = useState(false);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["vda-interview", instanceId, lang],
    queryFn: () => controlsApi.getVdaInterview(instanceId, lang),
    staleTime: Infinity,
  });

  useEffect(() => {
    if (data) setAnswers(data.answers);
  }, [data]);

  // Le risposte salvate (anche dalla generazione bozza) restano nella cache
  // della query: riaprendo il pannello non si ripresentano quelle vecchie.
  // staleTime Infinity evita che un refetch sovrascriva ciò che si sta scrivendo.
  const rememberAnswers = () =>
    qc.setQueryData<VdaInterview>(["vda-interview", instanceId, lang], old =>
      old ? { ...old, answers: { ...answers } } : old,
    );

  const saveMutation = useMutation({
    mutationFn: () => controlsApi.saveVdaInterview(instanceId, answers, lang),
    onSuccess: () => {
      rememberAnswers();
      setError("");
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    },
    onError: (e) => setError(errorMessage(e, t("common.error"))),
  });

  const draftMutation = useMutation({
    mutationFn: () => controlsApi.draftVdaInterview(instanceId, answers, lang),
    onSuccess: (d) => {
      rememberAnswers();
      setError("");
      setDraft(d);
      setUsed(false);
    },
    onError: (e) => setError(errorMessage(e, t("common.error"))),
  });

  const requirements = data?.requirements ?? [];
  const levelById = useMemo(
    () => Object.fromEntries(requirements.map(r => [r.id, r.level])),
    [requirements],
  );
  const answered = requirements.filter(r => (answers[r.id] ?? "").trim()).length;
  const unansweredMandatory = (draft?.unanswered ?? []).filter(id => MANDATORY.includes(levelById[id])).length;

  if (isLoading) {
    return <p className="text-xs text-gray-500 italic">{t("controls.drawer.evaluation.interview.loading")}</p>;
  }
  if (isError || !data) {
    return <p className="text-xs text-red-600">{t("common.error")}</p>;
  }

  return (
    <div className="space-y-3 border-t border-purple-200 pt-3">
      <p className="text-xs text-gray-600">{t("controls.drawer.evaluation.interview.intro")}</p>
      {data.ai_error && (
        <p className="text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded px-2 py-1">
          {t(`controls.drawer.evaluation.interview.ai_${data.ai_error}`)}
        </p>
      )}

      <p className="text-xs font-medium text-gray-600">
        {t("controls.drawer.evaluation.interview.answered_count", { answered, total: requirements.length })}
      </p>

      <ol className="space-y-3">
        {requirements.map((r, idx) => (
          <li key={r.id} className="space-y-1">
            <div className="flex items-start gap-2">
              <span className="text-xs text-gray-400 w-5 shrink-0 text-right">{idx + 1}.</span>
              <div className="flex-1 space-y-1">
                <span className={`inline-block text-[10px] font-semibold px-1.5 rounded ${LEVEL_STYLE[r.level]}`}>
                  {t(`controls.drawer.evaluation.interview.levels.${r.level}`)}
                  {r.source ? ` · ${r.source}` : ""}
                </span>
                <p className="text-sm text-gray-800">{r.question || r.text_en}</p>
                {r.question && (
                  <button
                    type="button"
                    onClick={() => setOpenOriginal(o => ({ ...o, [r.id]: !o[r.id] }))}
                    className="text-[11px] text-purple-700 hover:underline"
                  >
                    {openOriginal[r.id] ? "▾" : "▸"} {t("controls.drawer.evaluation.interview.original")}
                  </button>
                )}
                {r.question && openOriginal[r.id] && (
                  <p className="text-xs text-gray-500 italic bg-gray-50 rounded px-2 py-1">{r.text_en}</p>
                )}
                <textarea
                  value={answers[r.id] ?? ""}
                  onChange={e => { setAnswers(a => ({ ...a, [r.id]: e.target.value })); setSaved(false); }}
                  placeholder={t("controls.drawer.evaluation.interview.answer_placeholder")}
                  maxLength={2000}
                  className="w-full border rounded px-2 py-1.5 text-sm"
                  rows={2}
                />
              </div>
            </div>
          </li>
        ))}
      </ol>

      {error && <p className="text-xs text-red-600 whitespace-pre-line">{error}</p>}

      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => saveMutation.mutate()}
          disabled={saveMutation.isPending}
          className="flex-1 py-1.5 border border-purple-300 text-purple-700 rounded text-xs hover:bg-purple-50 disabled:opacity-50"
        >
          {saveMutation.isPending ? t("common.saving") : saved ? "✓ " + t("controls.drawer.evaluation.interview.answers_saved") : t("controls.drawer.evaluation.interview.save_answers")}
        </button>
        <button
          type="button"
          onClick={() => draftMutation.mutate()}
          disabled={draftMutation.isPending || answered === 0 || data.ai_error === "not_configured"}
          className="flex-1 py-1.5 bg-purple-600 text-white rounded text-xs hover:bg-purple-700 disabled:opacity-50"
        >
          {draftMutation.isPending ? t("controls.drawer.evaluation.interview.generating") : t("controls.drawer.evaluation.interview.generate")}
        </button>
      </div>

      {draft && (
        <div className="space-y-2 border border-purple-200 rounded p-2 bg-white">
          <p className="text-[11px] text-gray-500">
            {t("ai.generated_label")}{draft.model ? ` — ${draft.provider}/${draft.model}` : ""}
          </p>
          {unansweredMandatory > 0 && (
            <p className="text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded px-2 py-1">
              ⚠ {t("controls.drawer.evaluation.interview.unanswered_warning", { count: unansweredMandatory })}
            </p>
          )}
          {draft.not_implemented.length > 0 && (
            <p className="text-xs text-red-800 bg-red-50 border border-red-200 rounded px-2 py-1">
              ⚠ {t("controls.drawer.evaluation.interview.not_implemented_warning", { count: draft.not_implemented.length })}
            </p>
          )}
          <p className="text-xs font-semibold text-gray-600">{t("controls.drawer.evaluation.interview.draft_title")}</p>
          <p className="text-sm text-gray-800 whitespace-pre-wrap">{draft.draft_en}</p>
          {draft.draft_local && lang !== "en" && (
            <>
              <p className="text-xs font-semibold text-gray-600">{t("controls.drawer.evaluation.interview.draft_local_title")}</p>
              <p className="text-xs text-gray-600 whitespace-pre-wrap">{draft.draft_local}</p>
            </>
          )}
          <button
            type="button"
            onClick={() => { onUseDraft(draft.draft_en, draft.interaction_id); setUsed(true); }}
            disabled={!draft.draft_en}
            className="w-full py-1.5 bg-purple-600 text-white rounded text-xs hover:bg-purple-700 disabled:opacity-50"
          >
            {t("controls.drawer.evaluation.interview.use_draft")}
          </button>
          {used && <p className="text-xs text-green-700">{t("controls.drawer.evaluation.interview.draft_used")}</p>}
        </div>
      )}
    </div>
  );
}
