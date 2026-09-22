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
  const [selected, setSelected] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [result, setResult] = useState<{ approved: number; skipped: Array<{ title?: string; reason: string }> } | null>(null);

  const pending = snap?.documenti?.elenco_non_approvati ?? [];
  const byResolution = review.approval_status === "approvato" && review.approval_mode === "delibera";

  const mutation = useMutation({
    mutationFn: () => managementReviewApi.approveDocuments(review.id, selected),
    onSuccess: (data) => {
      setResult({ approved: data.approved.length, skipped: data.skipped });
      setSelected([]);
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
  if (pending.length === 0) {
    return (
      <section className="border border-gray-200 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-gray-800">{t("management_review.deliberated.title")}</h3>
        <p className="text-xs text-gray-500 mt-1">{t("management_review.deliberated.empty")}</p>
      </section>
    );
  }

  const toggle = (id: string) =>
    setSelected(s => (s.includes(id) ? s.filter(x => x !== id) : [...s, id]));

  return (
    <section className="border border-gray-200 rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-800">{t("management_review.deliberated.title")}</h3>
      <p className="text-xs text-gray-500 mt-1">
        {byResolution
          ? t("management_review.deliberated.hint", {
              ref: review.approval_resolution_ref,
              date: fmtDate(review.approval_resolution_date),
            })
          : t("management_review.deliberated.needs_resolution")}
      </p>

      <div className="mt-3 space-y-1">
        {pending.map(d => (
          <label key={d.id} className="flex items-start gap-2 text-xs text-gray-700 py-1">
            <input
              type="checkbox"
              className="mt-0.5"
              disabled={!byResolution || mutation.isPending}
              checked={selected.includes(d.id)}
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
        disabled={!byResolution || selected.length === 0 || mutation.isPending}
        onClick={() => { setError(""); setResult(null); mutation.mutate(); }}
        className="mt-3 px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
      >
        {mutation.isPending
          ? t("common.saving")
          : t("management_review.deliberated.approve", { count: selected.length })}
      </button>
    </section>
  );
}
