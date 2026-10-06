import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  managementReviewApi, reviewErrorMessage,
  type DocumentOutcome, type ManagementReview, type ReviewAgendaItem,
} from "../../api/endpoints/managementReview";
import { ClassBadge } from "../risk/RiskUi";
import { fmtDate } from "./shared";

// Riesame completo o mirato: l'organo delibera le accettazioni del rischio che
// la policy gli riserva, comprese quelle dei rischi che il Risk Owner ha
// valutato e tratta da solo (procedura di risk management §10). Ogni
// accettazione diventa un punto con il suo esito, che si applica
// all'approvazione del verbale.

const OUTCOMES: DocumentOutcome[] = ["approvato", "rinviato", "respinto"];
const OUTCOME_STYLE: Record<DocumentOutcome, string> = {
  approvato: "bg-green-600 text-white border-green-600",
  rinviato: "bg-amber-500 text-white border-amber-500",
  respinto: "bg-red-600 text-white border-red-600",
};
function invalidate(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: ["management-review"] });
  qc.invalidateQueries({ queryKey: ["risk-acceptances"] });
}

// ── Selezione delle accettazioni in attesa ───────────────────────────────────

export function PendingAcceptancesPicker({ review }: { review: ManagementReview }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [chosen, setChosen] = useState<Set<string>>(new Set());
  const [skipped, setSkipped] = useState<Array<{ id: string; reason: string }>>([]);
  const [error, setError] = useState("");

  const { data: rows = [], isLoading } = useQuery({
    queryKey: ["management-review", review.id, "pending-acceptances"],
    queryFn: () => managementReviewApi.pendingAcceptances(review.id),
    retry: false,
  });
  const waiting = rows.filter(r => !r.selected).length;

  const add = useMutation({
    mutationFn: () => managementReviewApi.addAcceptanceItems(review.id, [...chosen]),
    onSuccess: data => {
      invalidate(qc);
      setSkipped(data.skipped);
      setChosen(new Set());
      setError("");
      if (data.skipped.length === 0) setOpen(false);
    },
    onError: e => setError(reviewErrorMessage(e, t("management_review.risk_acceptances.add_error"))),
  });

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
          + {t("management_review.risk_acceptances.add")}
          {waiting > 0 && <span className="ml-1 px-1.5 rounded-full bg-amber-100 text-amber-800">{waiting}</span>}
        </button>
        {skipped.length > 0 && <Skipped skipped={skipped} />}
      </div>
    );
  }

  return (
    <div className="border border-primary-200 bg-primary-50/30 rounded p-3 space-y-2">
      <p className="text-xs font-medium text-gray-700">{t("management_review.risk_acceptances.pending_title")}</p>
      <p className="text-xs text-gray-500">{t("management_review.risk_acceptances.pending_hint")}</p>
      {isLoading ? (
        <p className="text-xs text-gray-400">{t("management_review.list.loading")}</p>
      ) : rows.length === 0 ? (
        <p className="text-xs text-gray-400 italic">{t("management_review.risk_acceptances.no_pending")}</p>
      ) : (
        <div className="max-h-72 overflow-y-auto divide-y divide-gray-100 bg-white rounded border border-gray-200">
          {rows.map(r => (
            <label key={r.id}
                   className={`flex items-start gap-2 px-3 py-2 text-sm ${r.selected ? "opacity-60" : "cursor-pointer hover:bg-gray-50"}`}>
              <input type="checkbox" className="mt-1" disabled={r.selected}
                     checked={r.selected || chosen.has(r.id)} onChange={() => toggle(r.id)} />
              <span className="flex-1 min-w-0">
                <span className="text-gray-800">{r.risk_name}</span>
                <span className="flex flex-wrap items-center gap-1 mt-0.5">
                  <ClassBadge size="xs" cls={r.risk_class} />
                  <span className="text-xs text-gray-500">· {r.plant_code ?? t("management_review.risk_acceptances.group")}</span>
                  <span className="text-xs text-gray-500">· {t("management_review.risk_acceptances.valid_until", { date: fmtDate(r.expires_on) })}</span>
                  {r.upper_opinion === "pending" && (
                    <span className="text-xs px-1.5 rounded bg-indigo-50 text-indigo-700">{t("management_review.risk_acceptances.opinion_pending")}</span>
                  )}
                  {r.selected && <span className="text-xs px-1.5 rounded bg-gray-100 text-gray-600">{t("management_review.targeted.already_selected")}</span>}
                </span>
                <span className="block text-xs text-gray-500 mt-0.5 truncate" title={r.rationale}>{r.rationale}</span>
              </span>
            </label>
          ))}
        </div>
      )}
      {error && <p className="text-xs text-red-600">{error}</p>}
      {skipped.length > 0 && <Skipped skipped={skipped} />}
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

function Skipped({ skipped }: { skipped: Array<{ id: string; reason: string }> }) {
  const { t } = useTranslation();
  return (
    <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2">
      <p className="font-medium">{t("management_review.targeted.skipped")}</p>
      <ul className="list-disc ml-4">{skipped.map(s => <li key={s.id}>{s.reason}</li>)}</ul>
    </div>
  );
}

// ── Esito del punto accettazione ─────────────────────────────────────────────

export function AcceptanceOutcomeControls({ item, locked }: { item: ReviewAgendaItem; locked: boolean }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [error, setError] = useState("");
  const info = item.risk_acceptance_info;

  const setOutcome = useMutation({
    mutationFn: (outcome: DocumentOutcome | "") => managementReviewApi.updateAgendaItem(item.id, { document_outcome: outcome }),
    onSuccess: () => { invalidate(qc); setError(""); },
    onError: e => setError(reviewErrorMessage(e, t("management_review.agenda.save_error"))),
  });

  if (!info) return null;
  const outcome = item.document_outcome || "";
  const stillPending = info.status === "pending";

  return (
    <div className="bg-gray-50/60 rounded p-2 space-y-2">
      <div className="flex flex-wrap items-center gap-1 text-xs text-gray-600">
        <ClassBadge size="xs" cls={info.risk_class} />
        <span>· {info.plant_code ?? t("management_review.risk_acceptances.group")}</span>
        <span>· {t("management_review.risk_acceptances.valid_until", { date: fmtDate(info.expires_on) })}</span>
        {info.upper_opinion === "pending" && (
          <span className="px-1.5 rounded bg-indigo-50 text-indigo-700">{t("management_review.risk_acceptances.opinion_pending")}</span>
        )}
      </div>
      <p className="text-xs text-gray-700">
        <span className="font-medium">{t("management_review.risk_acceptances.rationale")}:</span> {info.rationale}
      </p>
      {!stillPending && !item.document_outcome_applied_at && (
        <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1">
          {t("management_review.risk_acceptances.no_longer_pending", { status: t(`risk.acceptance.status.${info.status}`, info.status) })}
        </p>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-gray-600">{t("management_review.targeted.outcome")}</span>
        {OUTCOMES.map(o => (
          <button key={o}
                  onClick={() => setOutcome.mutate(outcome === o ? "" : o)}
                  disabled={locked || setOutcome.isPending || (!stillPending && !outcome)}
                  className={`px-2 py-0.5 rounded border text-xs disabled:cursor-not-allowed ${
                    outcome === o ? OUTCOME_STYLE[o] : "border-gray-300 text-gray-600 hover:bg-white disabled:opacity-50"}`}>
            {t(`management_review.targeted.outcomes.${o}`)}
          </button>
        ))}
        {!outcome && <span className="text-xs text-red-600">{t("management_review.targeted.outcome_missing")}</span>}
      </div>
      {item.document_outcome_applied_at ? (
        <p className="text-xs text-green-700">✓ {t("management_review.risk_acceptances.applied_on", { date: fmtDate(item.document_outcome_applied_at) })}</p>
      ) : item.document_outcome_error ? (
        <p className="text-xs text-red-600">{t("management_review.targeted.not_applied", { reason: item.document_outcome_error })}</p>
      ) : outcome ? (
        <p className="text-xs text-gray-400">{t("management_review.risk_acceptances.applies_on_approval")}</p>
      ) : null}
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}
