import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { documentsApi } from "../../api/endpoints/documents";
import { managementReviewApi, reviewErrorMessage, type ManagementReview } from "../../api/endpoints/managementReview";
import i18n from "../../i18n";
import { todayISO } from "../../utils/dates";
import { fmtDate } from "./shared";

const APPROVAL_COLORS: Record<string, string> = {
  bozza:     "bg-gray-100 text-gray-600",
  in_review: "bg-blue-100 text-blue-700",
  approvato: "bg-green-100 text-green-700",
  rifiutato: "bg-red-100 text-red-700",
};

// Due forme di approvazione (§9.3): in app — da un componente in carica
// dell'organo con account, o da governance — oppure registrando la delibera
// dell'organo (numero, data ed eventuale documento come evidenza).

export function ApprovalSection({ review, isGovernance, onMissing }: {
  review: ManagementReview; isGovernance: boolean; onMissing?: (codes: string[]) => void;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [mode, setMode] = useState<"in_app" | "delibera">("in_app");
  const [note, setNote] = useState("");
  const [resolution, setResolution] = useState({ ref: "", date: "", document_id: "" });
  const [docQuery, setDocQuery] = useState("");
  const [error, setError] = useState("");

  const isApproved = review.approval_status === "approvato";
  const hasSnapshot = !!review.snapshot_generated_at;
  const isCompleted = review.status === "completato";

  const { data: docs } = useQuery({
    queryKey: ["documents-evidence", docQuery],
    queryFn: () => documentsApi.list(docQuery ? { search: docQuery } : {}),
    enabled: mode === "delibera" && isGovernance && !isApproved,
    retry: false,
  });

  // La chiusura della riunione è il controllo di copertura dei punti
  // obbligatori (§9.3.2): resta un passaggio a sé, ma si fa da qui — in seduta
  // si chiude e si approva nello stesso momento, senza risalire la pagina.
  const complete = useMutation({
    mutationFn: () => managementReviewApi.complete(review.id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["management-review"] }); setError(""); onMissing?.([]); },
    onError: (e: any) => {
      const data = e?.response?.data;
      if (data?.code === "agenda_incomplete") {
        onMissing?.(data.missing ?? []);
        setError(t("management_review.detail.agenda_incomplete", { count: (data.missing ?? []).length }));
      } else {
        setError(reviewErrorMessage(e, t("management_review.detail.status_error")));
      }
    },
  });

  const approve = useMutation({
    mutationFn: () => managementReviewApi.approve(review.id, mode === "delibera"
      ? { note, mode, resolution_ref: resolution.ref, resolution_date: resolution.date,
          document_id: resolution.document_id || null }
      : { note, mode }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["management-review"] }); setError(""); },
    onError: e => setError(reviewErrorMessage(e, t("management_review.detail.approve_error"))),
  });

  const canSubmit = hasSnapshot && isCompleted && (mode === "in_app" || (!!resolution.ref.trim() && !!resolution.date));

  return (
    <section>
      <h4 className="text-sm font-semibold text-gray-700 mb-3">{t("management_review.detail.approval")}</h4>
      <div className="flex flex-wrap items-center gap-3 mb-3">
        <span className={`text-xs px-2 py-1 rounded font-medium ${APPROVAL_COLORS[review.approval_status] ?? "bg-gray-100 text-gray-600"}`}>
          {t(`management_review.approval.${review.approval_status}`, review.approval_status)}
        </span>
        {isApproved && review.approved_at && (
          <span className="text-xs text-gray-600">
            {review.approval_mode === "delibera" ? (
              t("management_review.approval_form.approved_resolution", {
                body: review.governing_body_name ?? "—",
                ref: review.approval_resolution_ref,
                date: fmtDate(review.approval_resolution_date),
                by: review.approved_by_name ?? "—",
              })
            ) : (
              <>
                {t("management_review.detail.approved_on", { date: new Date(review.approved_at).toLocaleString(i18n.language || "it") })}
                {` — ${review.approved_member_name ?? review.approved_by_name ?? "—"}`}
              </>
            )}
            {review.approval_note && ` — ${review.approval_note}`}
          </span>
        )}
      </div>

      {!isApproved && !review.viewer_can_approve && (
        <p className="text-xs text-gray-500">{t("management_review.approval_form.not_allowed")}</p>
      )}

      {!isApproved && review.viewer_can_approve && (
        <div className="space-y-2">
          {isGovernance && (
            <div className="flex flex-wrap gap-4 text-sm">
              {(["in_app", "delibera"] as const).map(m => (
                <label key={m} className="flex items-center gap-1.5 cursor-pointer">
                  <input type="radio" name="approval-mode" checked={mode === m} onChange={() => setMode(m)} />
                  {t(`management_review.approval_form.mode_${m}`)}
                </label>
              ))}
            </div>
          )}
          <p className="text-xs text-gray-500">
            {mode === "delibera" ? t("management_review.approval_form.hint_resolution")
              : isGovernance ? t("management_review.approval_form.hint_in_app_governance")
              : t("management_review.approval_form.hint_in_app_member")}
          </p>

          {mode === "delibera" && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <input className="border rounded px-3 py-2 text-sm" value={resolution.ref}
                     placeholder={t("management_review.approval_form.resolution_ref_ph")}
                     onChange={e => setResolution(r => ({ ...r, ref: e.target.value }))} />
              <input type="date" className="border rounded px-3 py-2 text-sm" value={resolution.date}
                     min={review.review_date} max={todayISO()}
                     onChange={e => setResolution(r => ({ ...r, date: e.target.value }))} />
              <div>
                <input className="border rounded px-3 py-1.5 text-xs w-full mb-1" value={docQuery}
                       placeholder={t("management_review.approval_form.document_search_ph")}
                       onChange={e => setDocQuery(e.target.value)} />
                <select className="border rounded px-2 py-1.5 text-xs w-full" value={resolution.document_id}
                        onChange={e => setResolution(r => ({ ...r, document_id: e.target.value }))}>
                  <option value="">{t("management_review.approval_form.no_document")}</option>
                  {(docs?.results ?? []).map(d => (
                    <option key={d.id} value={d.id}>{d.document_code ? `${d.document_code} — ` : ""}{d.title}</option>
                  ))}
                </select>
              </div>
            </div>
          )}

          <textarea value={note} onChange={e => setNote(e.target.value)} rows={2}
                    placeholder={t("management_review.detail.note_ph")}
                    className="w-full border rounded px-3 py-2 text-sm" />
          {error && <p className="text-xs text-red-600">{error}</p>}
          <button onClick={() => approve.mutate()} disabled={approve.isPending || !canSubmit}
                  className="px-4 py-2 bg-green-600 text-white rounded text-sm hover:bg-green-700 disabled:opacity-50">
            {approve.isPending ? t("management_review.detail.approving")
              : mode === "delibera" ? t("management_review.approval_form.register_resolution")
              : t("management_review.detail.approve")}
          </button>
          {!hasSnapshot && <p className="text-xs text-amber-600">{t("management_review.detail.need_snapshot")}</p>}
          {hasSnapshot && !isCompleted && (
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-xs text-amber-600">{t("management_review.detail.need_completed_why")}</p>
              <button onClick={() => complete.mutate()} disabled={complete.isPending}
                      className="px-3 py-1 bg-green-600 text-white rounded text-xs hover:bg-green-700 disabled:opacity-50">
                ✓ {complete.isPending ? t("management_review.detail.approving") : t("management_review.detail.mark_completed")}
              </button>
            </div>
          )}
          {!review.executive_summary && <p className="text-xs text-gray-400">{t("management_review.detail.summary_recommended")}</p>}
        </div>
      )}
    </section>
  );
}
