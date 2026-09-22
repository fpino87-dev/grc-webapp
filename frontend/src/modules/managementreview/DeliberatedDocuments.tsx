import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { managementReviewApi, type ManagementReview } from "../../api/endpoints/managementReview";
import { fmtDate } from "./shared";

type PendingDoc = {
  id: string; title: string; document_code: string; document_type: string;
  status: string; owner: string; created_at: string | null;
};

/**
 * Documenti obbligatori deliberati nella seduta.
 *
 * L'elenco è quello congelato nello snapshot e stampato nel verbale: dopo che
 * l'organo ha deliberato (e il riesame è stato approvato come delibera), qui si
 * registrano in blocco le approvazioni, che ereditano numero e data della
 * delibera. Il verbale firmato resta l'evidenza.
 */
export function DeliberatedDocuments({ review, snap, isGovernance }: {
  review: ManagementReview;
  snap: { documenti?: { elenco_non_approvati?: PendingDoc[] } } | null;
  isGovernance: boolean;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [selected, setSelected] = useState<string[] | null>(null);
  const [error, setError] = useState("");
  const [result, setResult] = useState<{ approved: number; skipped: Array<{ title?: string; reason: string }> } | null>(null);

  const all = snap?.documenti?.elenco_non_approvati ?? [];
  // Quelli già mandati in vigore con questo riesame restano visibili come
  // esito della seduta, ma non sono più da approvare.
  const approvedHere = new Set((review.approved_documents ?? []).map(d => d.id));
  const pending = all.filter(d => !approvedHere.has(d.id));
  // Basta che il riesame sia approvato: se l'organo ha deliberato fuori dalla
  // piattaforma i documenti ne ereditano gli estremi, altrimenti il
  // riferimento è la seduta stessa.
  const approved = review.approval_status === "approvato";
  const hasResolution = !!review.approval_resolution_ref && !!review.approval_resolution_date;

  // null = nessuna scelta esplicita: valgono tutti i documenti dell'elenco
  const chosen = selected ?? pending.map(d => d.id);

  const mutation = useMutation({
    mutationFn: () => managementReviewApi.approveDocuments(review.id, chosen),
    onSuccess: (data) => {
      setResult({ approved: data.approved.length, skipped: data.skipped });
      setSelected(null);
      qc.invalidateQueries({ queryKey: ["management-reviews"] });
      qc.invalidateQueries({ queryKey: ["documents"] });
    },
    onError: (e: unknown) => {
      // @ts-expect-error forma dell'errore axios
      setError(e?.response?.data?.detail || t("common.save_error"));
    },
  });

  // Il pannello resta visibile anche senza documenti in attesa: dice che non
  // ce ne sono, invece di sparire e lasciar credere che manchi la funzione.
  if (!isGovernance || !snap) return null;

  const approvedList = all.filter(d => approvedHere.has(d.id));
  const approvedRows = approvedList.length > 0 && (
    <div className="mt-3 space-y-1">
      {approvedList.map(d => (
        <p key={d.id} className="text-xs text-green-700">
          ✓ {d.document_code ? `[${d.document_code}] ` : ""}{d.title} — {t("management_review.deliberated.approved_here")}
        </p>
      ))}
    </div>
  );

  if (pending.length === 0) {
    return (
      <section className="border border-gray-200 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-gray-800">{t("management_review.deliberated.title")}</h3>
        {approvedRows || <p className="text-xs text-gray-500 mt-1">{t("management_review.deliberated.empty")}</p>}
      </section>
    );
  }

  const toggle = (id: string) =>
    setSelected(s => {
      const current = s ?? pending.map(d => d.id);
      return current.includes(id) ? current.filter(x => x !== id) : [...current, id];
    });

  return (
    <section className="border border-gray-200 rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-800">{t("management_review.deliberated.title")}</h3>
      <p className="text-xs text-gray-500 mt-1">
        {!approved
          ? t("management_review.deliberated.needs_approval")
          : hasResolution
            ? t("management_review.deliberated.hint", {
                ref: review.approval_resolution_ref,
                date: fmtDate(review.approval_resolution_date),
              })
            : t("management_review.deliberated.hint_meeting", { date: fmtDate(review.review_date) })}
      </p>

      {approvedRows}

      <div className="mt-3 space-y-1">
        {pending.map(d => (
          <label key={d.id} className="flex items-start gap-2 text-xs text-gray-700 py-1">
            <input
              type="checkbox"
              className="mt-0.5"
              disabled={!approved || mutation.isPending}
              checked={chosen.includes(d.id)}
              onChange={() => toggle(d.id)}
            />
            <span>
              <span className="font-medium">{d.document_code ? `[${d.document_code}] ` : ""}{d.title}</span>
              <span className="text-gray-400"> · {fmtDate(d.created_at)}</span>
            </span>
          </label>
        ))}
      </div>

      {error && <p className="text-xs text-red-600 mt-2">{error}</p>}
      {result && (
        <div className="text-xs mt-2 space-y-1">
          <p className="text-green-700">{t("management_review.deliberated.done", { count: result.approved })}</p>
          {result.skipped.map((s, i) => (
            <p key={i} className="text-amber-600">{s.title ? `${s.title}: ` : ""}{s.reason}</p>
          ))}
        </div>
      )}

      <button
        type="button"
        disabled={!approved || chosen.length === 0 || mutation.isPending}
        onClick={() => { setError(""); setResult(null); mutation.mutate(); }}
        className="mt-3 px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
      >
        {mutation.isPending
          ? t("common.saving")
          : t("management_review.deliberated.approve", { count: chosen.length })}
      </button>
    </section>
  );
}
