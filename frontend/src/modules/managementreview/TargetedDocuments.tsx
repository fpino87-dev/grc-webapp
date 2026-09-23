import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  managementReviewApi, reviewErrorMessage,
  type DocumentOutcome, type ManagementReview, type ReviewAgendaItem,
} from "../../api/endpoints/managementReview";
import { fmtDate } from "./shared";

// Riesame mirato: l'organo decide sui documenti in attesa. Si scelgono da un
// elenco calcolato sui dati correnti; ogni documento diventa un punto con la
// revisione esaminata fissata, e l'esito si applica all'approvazione del verbale.

const OUTCOMES: DocumentOutcome[] = ["approvato", "rinviato", "respinto"];
const OUTCOME_STYLE: Record<DocumentOutcome, string> = {
  approvato: "bg-green-600 text-white border-green-600",
  rinviato: "bg-amber-500 text-white border-amber-500",
  respinto: "bg-red-600 text-white border-red-600",
};

function invalidate(qc: ReturnType<typeof useQueryClient>) {
  return qc.invalidateQueries({ queryKey: ["management-review"] });
}

// ── Selezione dei documenti in attesa ────────────────────────────────────────

export function PendingDocumentsPicker({ review }: { review: ManagementReview }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState("");
  const [chosen, setChosen] = useState<Set<string>>(new Set());
  const [skipped, setSkipped] = useState<Array<{ id: string; title?: string; reason: string }>>([]);
  const [error, setError] = useState("");

  const { data: rows = [], isLoading } = useQuery({
    queryKey: ["management-review", review.id, "pending-documents"],
    queryFn: () => managementReviewApi.pendingDocuments(review.id),
    enabled: open,
    retry: false,
  });

  const add = useMutation({
    mutationFn: () => managementReviewApi.addDocumentItems(review.id, [...chosen]),
    onSuccess: data => {
      invalidate(qc);
      setSkipped(data.skipped);
      setChosen(new Set());
      setError("");
      if (data.skipped.length === 0) setOpen(false);
    },
    onError: e => setError(reviewErrorMessage(e, t("management_review.targeted.add_error"))),
  });

  const q = filter.trim().toLowerCase();
  const visible = rows.filter(r => !q || `${r.document_code} ${r.title}`.toLowerCase().includes(q));
  const toggle = (id: string) => setChosen(prev => {
    const next = new Set(prev);
    if (next.has(id)) next.delete(id); else next.add(id);
    return next;
  });

  if (!open) {
    return (
      <div className="space-y-1">
        <button onClick={() => { setOpen(true); setSkipped([]); }}
                className="px-3 py-1.5 border border-primary-300 text-primary-700 rounded text-xs hover:bg-primary-50">
          + {t("management_review.targeted.add_documents")}
        </button>
        {skipped.length > 0 && <SkippedList skipped={skipped} />}
      </div>
    );
  }

  return (
    <div className="border border-primary-200 bg-primary-50/30 rounded p-3 space-y-2">
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-medium text-gray-700">{t("management_review.targeted.pending_title")}</p>
        <input value={filter} onChange={e => setFilter(e.target.value)}
               placeholder={t("management_review.targeted.filter_ph")}
               className="border rounded px-2 py-1 text-xs w-48" />
      </div>
      <p className="text-xs text-gray-500">{t("management_review.targeted.pending_hint")}</p>
      {isLoading ? (
        <p className="text-xs text-gray-400">{t("management_review.list.loading")}</p>
      ) : visible.length === 0 ? (
        <p className="text-xs text-gray-400 italic">{t("management_review.targeted.no_pending")}</p>
      ) : (
        <div className="max-h-72 overflow-y-auto divide-y divide-gray-100 bg-white rounded border border-gray-200">
          {visible.map(r => {
            const disabled = r.selected || !r.has_version;
            return (
              <label key={r.id}
                     className={`flex items-start gap-2 px-3 py-2 text-sm ${disabled ? "opacity-60" : "cursor-pointer hover:bg-gray-50"}`}>
                <input type="checkbox" className="mt-1" disabled={disabled}
                       checked={r.selected || chosen.has(r.id)} onChange={() => toggle(r.id)} />
                <span className="flex-1 min-w-0">
                  <span className="text-gray-800">
                    {r.document_code && <span className="font-mono text-xs text-gray-500 mr-1">[{r.document_code}]</span>}
                    {r.title}
                  </span>
                  <span className="flex flex-wrap gap-1 mt-0.5">
                    <span className="text-xs text-gray-500">{t(`status.${r.status}`, r.status)}</span>
                    <span className="text-xs text-gray-500">· {r.version ?? t("management_review.targeted.no_file")}</span>
                    {r.plant_code && <span className="text-xs text-gray-400">· {r.plant_code}</span>}
                    {r.is_mandatory && <span className="text-xs px-1.5 rounded bg-blue-50 text-blue-700">{t("management_review.targeted.mandatory")}</span>}
                    {r.new_version && <span className="text-xs px-1.5 rounded bg-amber-50 text-amber-700">{t("management_review.targeted.new_version")}</span>}
                    {r.requires_body_resolution && <span className="text-xs px-1.5 rounded bg-indigo-50 text-indigo-700">{t("management_review.targeted.body_resolution")}</span>}
                    {r.selected && <span className="text-xs px-1.5 rounded bg-gray-100 text-gray-600">{t("management_review.targeted.already_selected")}</span>}
                  </span>
                </span>
              </label>
            );
          })}
        </div>
      )}
      {error && <p className="text-xs text-red-600">{error}</p>}
      {skipped.length > 0 && <SkippedList skipped={skipped} />}
      <div className="flex gap-2">
        <button onClick={() => add.mutate()} disabled={add.isPending || chosen.size === 0}
                className="px-3 py-1 bg-primary-600 text-white rounded text-xs hover:bg-primary-700 disabled:opacity-50">
          {t("management_review.targeted.add_selected", { count: chosen.size })}
        </button>
        <button onClick={() => { setOpen(false); setChosen(new Set()); }}
                className="px-3 py-1 border rounded text-xs text-gray-600 hover:bg-white">
          {t("management_review.actions.cancel")}
        </button>
      </div>
    </div>
  );
}

function SkippedList({ skipped }: { skipped: Array<{ id: string; title?: string; reason: string }> }) {
  const { t } = useTranslation();
  return (
    <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2">
      <p className="font-medium">{t("management_review.targeted.skipped")}</p>
      <ul className="list-disc ml-4">
        {skipped.map(s => <li key={s.id}>{s.title ? `${s.title}: ` : ""}{s.reason}</li>)}
      </ul>
    </div>
  );
}

// ── Esito del punto documento ────────────────────────────────────────────────

export function DocumentOutcomeControls({ item, locked }: { item: ReviewAgendaItem; locked: boolean }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [error, setError] = useState("");
  const info = item.document_info;

  const setOutcome = useMutation({
    mutationFn: (outcome: DocumentOutcome | "") => managementReviewApi.updateAgendaItem(item.id, { document_outcome: outcome }),
    onSuccess: () => { invalidate(qc); setError(""); },
    onError: e => setError(reviewErrorMessage(e, t("management_review.agenda.save_error"))),
  });
  const realign = useMutation({
    mutationFn: () => managementReviewApi.refreshItemVersion(item.id),
    onSuccess: () => { invalidate(qc); setError(""); },
    onError: e => setError(reviewErrorMessage(e, t("management_review.agenda.save_error"))),
  });

  if (!info) return null;
  const outcome = item.document_outcome || "";

  return (
    <div className="bg-gray-50/60 rounded p-2 space-y-2">
      <p className="text-xs text-gray-600">
        {t("management_review.targeted.examined_version", { version: info.examined_version ?? "—" })}
        {" · "}{t(`status.${info.status}`, info.status)}
        {info.is_mandatory && <span className="ml-1 text-blue-700">· {t("management_review.targeted.mandatory")}</span>}
      </p>
      {info.version_changed && (
        <div className="flex flex-wrap items-center gap-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1">
          <span>{t("management_review.targeted.version_changed", { version: info.latest_version ?? "—" })}</span>
          {!locked && (
            <button onClick={() => realign.mutate()} disabled={realign.isPending}
                    className="px-2 py-0.5 border border-amber-400 rounded hover:bg-amber-100 disabled:opacity-50">
              {t("management_review.targeted.realign")}
            </button>
          )}
        </div>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-gray-600">{t("management_review.targeted.outcome")}</span>
        {OUTCOMES.map(o => (
          <button key={o}
                  onClick={() => setOutcome.mutate(outcome === o ? "" : o)}
                  disabled={locked || setOutcome.isPending || info.version_changed}
                  className={`px-2 py-0.5 rounded border text-xs disabled:cursor-not-allowed ${
                    outcome === o ? OUTCOME_STYLE[o] : "border-gray-300 text-gray-600 hover:bg-white disabled:opacity-50"}`}>
            {t(`management_review.targeted.outcomes.${o}`)}
          </button>
        ))}
        {!outcome && <span className="text-xs text-red-600">{t("management_review.targeted.outcome_missing")}</span>}
      </div>
      <OutcomeState item={item} />
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}

function OutcomeState({ item }: { item: ReviewAgendaItem }) {
  const { t } = useTranslation();
  if (item.document_outcome_applied_at) {
    return <p className="text-xs text-green-700">✓ {t("management_review.targeted.applied_on", { date: fmtDate(item.document_outcome_applied_at) })}</p>;
  }
  if (item.document_outcome_error) {
    return <p className="text-xs text-red-600">{t("management_review.targeted.not_applied", { reason: item.document_outcome_error })}</p>;
  }
  return item.document_outcome
    ? <p className="text-xs text-gray-400">{t("management_review.targeted.applies_on_approval")}</p>
    : null;
}

// ── Dopo l'approvazione: esiti applicati ai documenti ────────────────────────

export function OutcomeSummary({ review, isGovernance }: { review: ManagementReview; isGovernance: boolean }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [error, setError] = useState("");
  const items = (review.agenda_items ?? []).filter(i => i.document);
  const failed = items.filter(i => i.document_outcome_error);

  const retry = useMutation({
    mutationFn: () => managementReviewApi.applyOutcomes(review.id),
    onSuccess: () => { invalidate(qc); setError(""); },
    onError: e => setError(reviewErrorMessage(e, t("management_review.targeted.retry_error"))),
  });

  if (review.approval_status !== "approvato" || items.length === 0) return null;
  return (
    <div className="border border-gray-200 rounded p-3 space-y-1">
      <p className="text-xs font-medium text-gray-700">{t("management_review.targeted.outcomes_title")}</p>
      {items.map(i => (
        <p key={i.id} className="text-xs text-gray-700">
          <span className="font-medium">{i.title}</span>{" — "}
          {t(`management_review.targeted.outcomes.${i.document_outcome || "rinviato"}`)}{" · "}
          {i.document_outcome_applied_at
            ? <span className="text-green-700">{t("management_review.targeted.applied_on", { date: fmtDate(i.document_outcome_applied_at) })}</span>
            : <span className="text-red-600">{t("management_review.targeted.not_applied", { reason: i.document_outcome_error || "—" })}</span>}
        </p>
      ))}
      {failed.length > 0 && isGovernance && (
        <button onClick={() => retry.mutate()} disabled={retry.isPending}
                className="mt-1 px-3 py-1 border border-gray-300 rounded text-xs text-gray-700 hover:bg-gray-50 disabled:opacity-50">
          {t("management_review.targeted.retry")}
        </button>
      )}
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}
