import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { managementReviewApi, reviewErrorMessage, type ManagementReview } from "../../api/endpoints/managementReview";
import i18n from "../../i18n";

function aiErrorMessage(e: unknown, t: (k: string) => string) {
  const resp = (e as { response?: { status?: number; data?: { code?: string } } })?.response;
  if (resp?.status === 503) return t("management_review.summary.ai_unavailable");
  if (resp?.data?.code === "ai_not_configured") return t("management_review.summary.ai_not_configured");
  return reviewErrorMessage(e, t("management_review.summary.ai_error"));
}

/**
 * Sintesi executive del verbale. L'IA produce solo una BOZZA, marcata come
 * contenuto generato da IA: entra nel verbale soltanto quando un utente la
 * accetta (eventualmente modificandola). Dopo l'approvazione è in sola lettura.
 */
export function ExecutiveSummarySection({ review, locked }: { review: ManagementReview; locked: boolean }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const draft = review.executive_summary_draft;
  const draftMeta = review.executive_summary_draft_meta ?? {};
  const meta = review.executive_summary_meta ?? {};
  // null = nessuna modifica in corso: si mostra la bozza IA o il testo salvato
  const [edited, setText] = useState<string | null>(null);
  const text = edited ?? (draft || review.executive_summary);
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState("");

  const refresh = () => qc.invalidateQueries({ queryKey: ["management-review"] });
  const generate = useMutation({
    mutationFn: () => managementReviewApi.draftSummary(review.id, (i18n.language || "it").slice(0, 2)),
    onSuccess: () => { refresh(); setError(""); setText(null); },
    onError: e => setError(aiErrorMessage(e, t)),
  });
  const accept = useMutation({
    mutationFn: () => managementReviewApi.saveSummary(review.id, text),
    onSuccess: () => { refresh(); setEditing(false); setError(""); setText(null); },
    onError: e => setError(reviewErrorMessage(e, t("management_review.summary.save_error"))),
  });
  const discard = useMutation({
    mutationFn: () => managementReviewApi.discardSummaryDraft(review.id),
    onSuccess: () => { refresh(); setError(""); setText(null); },
    onError: e => setError(reviewErrorMessage(e, t("management_review.summary.save_error"))),
  });

  const hasSnapshot = !!review.snapshot_generated_at;
  const staleDraft = !!draft && !!draftMeta.snapshot_generated_at && !!review.snapshot_generated_at
    && new Date(draftMeta.snapshot_generated_at).getTime() !== new Date(review.snapshot_generated_at).getTime();
  const dt = (iso?: string) => (iso ? new Date(iso).toLocaleString(i18n.language || "it") : "—");

  const provenance = review.executive_summary && (
    <p className="text-xs text-gray-500 mt-1">
      {meta.ai_assisted
        ? t(meta.edited ? "management_review.summary.meta_ai_edited" : "management_review.summary.meta_ai", {
            model: `${meta.provider}/${meta.model}`, name: meta.accepted_by_name ?? "—", date: dt(meta.accepted_at),
          })
        : t("management_review.summary.meta_manual", { name: meta.accepted_by_name ?? "—", date: dt(meta.accepted_at) })}
    </p>
  );

  return (
    <section>
      <h4 className="text-sm font-semibold text-gray-700 mb-1">{t("management_review.summary.heading")}</h4>
      <p className="text-xs text-gray-400 mb-2">{t("management_review.summary.intro")}</p>

      {draft && !locked ? (
        <div className="border border-amber-300 bg-amber-50 rounded p-3 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs bg-amber-400 text-white px-2 py-0.5 rounded font-bold">{t("ai.ai_badge")}</span>
            <span className="text-xs text-amber-800">🤖 {t("ai.generated_label")}</span>
          </div>
          <p className="text-xs text-amber-700">
            {t("management_review.summary.draft_meta", { model: `${draftMeta.provider}/${draftMeta.model}`, date: dt(draftMeta.generated_at) })}
          </p>
          {staleDraft && <p className="text-xs text-red-600">{t("management_review.summary.stale_draft")}</p>}
          <textarea rows={10} value={text} onChange={e => setText(e.target.value)} className="w-full border rounded p-2 text-sm bg-white" />
          <div className="flex flex-wrap gap-2">
            <button onClick={() => accept.mutate()} disabled={accept.isPending || !text.trim()} className="px-3 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700 disabled:opacity-50">
              {accept.isPending ? t("management_review.summary.saving") : t("management_review.summary.accept")}
            </button>
            <button onClick={() => discard.mutate()} disabled={discard.isPending} className="px-3 py-1 bg-gray-200 text-gray-700 text-xs rounded hover:bg-gray-300">
              {t("management_review.summary.discard")}
            </button>
          </div>
        </div>
      ) : editing && !locked ? (
        <div className="space-y-2">
          <textarea rows={10} value={text} onChange={e => setText(e.target.value)} className="w-full border rounded p-2 text-sm" />
          <div className="flex gap-2">
            <button onClick={() => accept.mutate()} disabled={accept.isPending} className="px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 disabled:opacity-50">
              {accept.isPending ? t("management_review.summary.saving") : t("management_review.summary.save")}
            </button>
            <button onClick={() => { setEditing(false); setText(null); }} className="px-3 py-1 border rounded text-xs text-gray-600">
              {t("management_review.summary.cancel")}
            </button>
          </div>
        </div>
      ) : review.executive_summary ? (
        <div className="border border-gray-200 rounded p-3 bg-gray-50">
          <p className="text-sm text-gray-800 whitespace-pre-line">{review.executive_summary}</p>
          {provenance}
        </div>
      ) : (
        <p className="text-xs text-gray-400 italic">{t("management_review.summary.none")}</p>
      )}

      {!locked && !draft && !editing && (
        <div className="flex flex-wrap items-center gap-2 mt-2">
          <button
            onClick={() => generate.mutate()}
            disabled={generate.isPending || !hasSnapshot}
            title={!hasSnapshot ? t("management_review.detail.need_snapshot_tip") : undefined}
            className="px-3 py-1.5 bg-indigo-600 text-white text-xs rounded hover:bg-indigo-700 disabled:opacity-50"
          >
            {generate.isPending ? t("management_review.summary.generating") : `✨ ${t(review.executive_summary ? "management_review.summary.regenerate_ai" : "management_review.summary.generate_ai")}`}
          </button>
          <button onClick={() => setEditing(true)} className="px-3 py-1.5 border border-gray-300 text-xs rounded text-gray-600 hover:bg-gray-50">
            {t(review.executive_summary ? "management_review.summary.edit" : "management_review.summary.write")}
          </button>
        </div>
      )}
      {!locked && !draft && <p className="text-xs text-gray-400 mt-1">{t("management_review.summary.privacy")}</p>}
      {error && <p className="text-xs text-red-600 mt-1">{error}</p>}
    </section>
  );
}
