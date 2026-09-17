import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { managementReviewApi, reviewErrorMessage, type ManagementReview } from "../../api/endpoints/managementReview";
import type { GrcUser } from "../../api/endpoints/users";
import { StatusBadge } from "../../components/ui/StatusBadge";
import i18n from "../../i18n";
import { AgendaSection } from "./AgendaSection";
import { ExecutiveSummarySection } from "./ExecutiveSummarySection";
import { SitesBlock } from "./SnapshotBlocks";
import { ParticipantsFields, SnapSection, fmtDate, type Snap } from "./shared";

const APPROVAL_COLORS: Record<string, string> = {
  bozza:     "bg-gray-100 text-gray-600",
  in_review: "bg-blue-100 text-blue-700",
  approvato: "bg-green-100 text-green-700",
  rifiutato: "bg-red-100 text-red-700",
};

type Plant = { id: string; code: string; name: string };

// ── Presidente e partecipanti ────────────────────────────────────────────────

function ParticipantsSection({ review, users, locked }: { review: ManagementReview; users: GrcUser[]; locked: boolean }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<{ chair: number | null; attendees: number[] }>({ chair: null, attendees: [] });
  const [error, setError] = useState("");

  const saveMutation = useMutation({
    mutationFn: () => managementReviewApi.update(review.id, draft),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["management-review"] }); setEditing(false); setError(""); },
    onError: e => setError(reviewErrorMessage(e, t("management_review.participants.save_error"))),
  });

  async function startEdit() {
    let chair = review.chair ?? null;
    if (chair === null) {
      chair = (await managementReviewApi.suggestedChair(review.plant).catch(() => ({ id: null }))).id;
    }
    setDraft({ chair, attendees: review.attendees ?? [] });
    setEditing(true);
  }

  return (
    <section>
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-semibold text-gray-700">{t("management_review.participants.heading")}</h4>
        {!editing && !locked && (
          <button onClick={startEdit} className="text-xs px-2 py-1 border border-gray-300 rounded hover:bg-gray-50 text-gray-600">
            {t("management_review.participants.edit")}
          </button>
        )}
      </div>
      {editing ? (
        <div className="border border-blue-200 rounded p-3 bg-blue-50 space-y-2">
          <ParticipantsFields users={users} chair={draft.chair} attendees={draft.attendees} onChange={setDraft} />
          {error && <p className="text-xs text-red-600">{error}</p>}
          <div className="flex gap-2">
            <button onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending} className="px-3 py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700 disabled:opacity-50">
              {saveMutation.isPending ? t("management_review.participants.saving") : t("management_review.participants.save")}
            </button>
            <button onClick={() => { setEditing(false); setError(""); }} className="px-3 py-1 border rounded text-xs text-gray-600 hover:bg-white">
              {t("management_review.participants.cancel")}
            </button>
          </div>
        </div>
      ) : (
        <dl className="text-sm space-y-1">
          <div className="flex gap-2">
            <dt className="text-gray-500 shrink-0">{t("management_review.participants.chair")}:</dt>
            <dd className={review.chair_name ? "text-gray-800 font-medium" : "text-amber-600"}>
              {review.chair_name ?? t("management_review.participants.chair_missing")}
            </dd>
          </div>
          <div className="flex gap-2">
            <dt className="text-gray-500 shrink-0">{t("management_review.participants.attendees")}:</dt>
            <dd className="text-gray-800">
              {review.attendees_detail?.length ? review.attendees_detail.map(a => a.name).join(", ") : <span className="text-gray-400">—</span>}
            </dd>
          </div>
        </dl>
      )}
    </section>
  );
}

// ── Stato riunione e prossimo riesame ────────────────────────────────────────

function MeetingSection({ review, locked, onMissing }: { review: ManagementReview; locked: boolean; onMissing: (codes: string[]) => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [error, setError] = useState("");
  // null = nessuna modifica in corso: si mostra il valore salvato
  const [editedNext, setEditedNext] = useState<string | null>(null);
  const nextDate = editedNext ?? review.next_review_date ?? "";

  const refresh = () => qc.invalidateQueries({ queryKey: ["management-review"] });
  const start = useMutation({
    mutationFn: () => managementReviewApi.start(review.id),
    onSuccess: () => { refresh(); setError(""); },
    onError: e => setError(reviewErrorMessage(e, t("management_review.detail.status_error"))),
  });
  const complete = useMutation({
    mutationFn: () => managementReviewApi.complete(review.id),
    onSuccess: () => { refresh(); setError(""); onMissing([]); },
    onError: (e: any) => {
      const data = e?.response?.data;
      if (data?.code === "agenda_incomplete") {
        onMissing(data.missing ?? []);
        setError(t("management_review.detail.agenda_incomplete", { count: (data.missing ?? []).length }));
      } else {
        setError(reviewErrorMessage(e, t("management_review.detail.status_error")));
      }
    },
  });
  const saveNext = useMutation({
    mutationFn: () => managementReviewApi.update(review.id, { next_review_date: nextDate || null }),
    onSuccess: () => { refresh(); setError(""); setEditedNext(null); },
    onError: e => setError(reviewErrorMessage(e, t("management_review.detail.status_error"))),
  });

  return (
    <section className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <div>
        <h4 className="text-sm font-semibold text-gray-700 mb-2">{t("management_review.detail.meeting_status")}</h4>
        <div className="flex flex-wrap items-center gap-3">
          <StatusBadge status={review.status} />
          {review.status === "pianificato" && (
            <button onClick={() => start.mutate()} disabled={start.isPending} className="px-3 py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700 disabled:opacity-50">
              ▶ {t("management_review.detail.start_meeting")}
            </button>
          )}
          {review.status === "in_corso" && (
            <button onClick={() => complete.mutate()} disabled={complete.isPending} className="px-3 py-1 bg-green-600 text-white rounded text-xs hover:bg-green-700 disabled:opacity-50">
              ✓ {t("management_review.detail.mark_completed")}
            </button>
          )}
        </div>
        {error && <p className="text-xs text-red-600 mt-1">{error}</p>}
      </div>
      <div>
        <h4 className="text-sm font-semibold text-gray-700 mb-2">{t("management_review.detail.next_review")}</h4>
        {locked ? (
          <p className="text-sm text-gray-800">{fmtDate(review.next_review_date)}</p>
        ) : (
          <div className="flex items-center gap-2">
            <input type="date" value={nextDate} onChange={e => setEditedNext(e.target.value)} className="border rounded px-2 py-1 text-sm" />
            {nextDate !== (review.next_review_date ?? "") && (
              <button onClick={() => saveNext.mutate()} disabled={saveNext.isPending} className="px-2 py-1 bg-blue-600 text-white rounded text-xs disabled:opacity-50">
                {t("management_review.participants.save")}
              </button>
            )}
          </div>
        )}
        <p className="text-xs text-gray-400 mt-1">{t("management_review.detail.next_review_hint")}</p>
      </div>
    </section>
  );
}

// ── Dettaglio ────────────────────────────────────────────────────────────────

export function ReviewDetail({ review, users, plants, onClose }: { review: ManagementReview; users: GrcUser[]; plants: Plant[]; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [note, setNote] = useState("");
  const [snapshotError, setSnapshotError] = useState("");
  const [approveError, setApproveError] = useState("");
  const [downloading, setDownloading] = useState<"" | "html" | "pdf">("");
  const [missing, setMissing] = useState<string[]>([]);

  const snapshotMutation = useMutation({
    mutationFn: () => managementReviewApi.generateSnapshot(review.id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["management-review"] }); setSnapshotError(""); },
    onError: e => setSnapshotError(reviewErrorMessage(e, t("management_review.detail.snapshot_error"))),
  });

  const approveMutation = useMutation({
    mutationFn: () => managementReviewApi.approve(review.id, note),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["management-review"] }); setApproveError(""); },
    onError: e => setApproveError(reviewErrorMessage(e, t("management_review.detail.approve_error"))),
  });

  async function handleDownload(fmt: "html" | "pdf") {
    setDownloading(fmt);
    try {
      const date = review.review_date?.replace(/-/g, "") ?? "";
      await managementReviewApi.downloadReport(review.id, `riesame_${review.id}_${date}.${fmt}`, fmt);
    } finally {
      setDownloading("");
    }
  }

  const snap = (review.snapshot_generated_at ? review.snapshot_data : null) as Snap | null;
  const isApproved = review.approval_status === "approvato";
  const hasSnapshot = !!review.snapshot_generated_at;
  const isCompleted = review.status === "completato";
  // Snapshot generati prima dei dettagli: solo contatori.
  const legacySnapshot = !!snap && !("azioni_precedenti" in snap);

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl flex flex-col max-h-[92vh]">
        {/* Header */}
        <div className="flex items-start justify-between gap-3 px-6 py-4 border-b border-gray-100 shrink-0">
          <div className="min-w-0">
            <h3 className="text-lg font-semibold text-gray-900">{review.title}</h3>
            <p className="text-xs text-gray-400 mt-0.5">
              {t("management_review.detail.meeting_date")} {fmtDate(review.review_date)}
              <span className="ml-2">· {review.plant_name ?? t("management_review.list.org_wide")}</span>
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {hasSnapshot && (["pdf", "html"] as const).map(fmt => (
              <button
                key={fmt}
                onClick={() => handleDownload(fmt)}
                disabled={!!downloading}
                className={`px-3 py-1.5 rounded text-xs disabled:opacity-50 ${fmt === "pdf" ? "bg-indigo-600 text-white hover:bg-indigo-700" : "border border-indigo-300 text-indigo-700 hover:bg-indigo-50"}`}
              >
                {downloading === fmt ? t("management_review.detail.downloading") : t(`management_review.detail.download_${fmt}`)}
              </button>
            ))}
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl w-8 h-8 flex items-center justify-center rounded hover:bg-gray-100">×</button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
          <MeetingSection review={review} locked={isApproved} onMissing={setMissing} />

          <ParticipantsSection review={review} users={users} locked={isApproved} />

          {/* ── Dati riesame (snapshot) ── */}
          <section>
            <h4 className="text-sm font-semibold text-gray-700 mb-2">{t("management_review.detail.review_data")}</h4>
            {!hasSnapshot ? (
              <div className="border border-dashed border-gray-300 rounded p-4 text-center">
                <p className="text-sm text-gray-500 mb-3">{t("management_review.detail.no_snapshot")}</p>
                {snapshotError && <p className="text-xs text-red-600 mb-2">{snapshotError}</p>}
                <button
                  onClick={() => snapshotMutation.mutate()}
                  disabled={snapshotMutation.isPending}
                  className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
                >
                  {snapshotMutation.isPending ? t("management_review.detail.generating") : t("management_review.detail.generate_snapshot")}
                </button>
              </div>
            ) : (
              <div className="space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-xs text-green-700">
                    {t("management_review.detail.snapshot_generated", { date: new Date(review.snapshot_generated_at!).toLocaleString(i18n.language || "it") })}
                  </p>
                  <button
                    onClick={() => snapshotMutation.mutate()}
                    disabled={snapshotMutation.isPending || isApproved}
                    title={isApproved ? t("management_review.detail.regen_locked") : t("management_review.detail.regen_tip")}
                    className="text-xs px-2 py-1 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-40 shrink-0"
                  >
                    {snapshotMutation.isPending ? "..." : t("management_review.detail.regen")}
                  </button>
                </div>
                {snapshotError && <p className="text-xs text-red-600">{snapshotError}</p>}
                {legacySnapshot && !isApproved && (
                  <p className="text-xs text-amber-600">{t("management_review.detail.regen_for_details")}</p>
                )}
                <p className="text-xs text-gray-400">{t("management_review.detail.data_in_agenda")}</p>
                {snap && Array.isArray(snap.siti) && snap.siti.length > 0 && (
                  <SnapSection title={t("management_review.snap.sites_overview")}>
                    <SitesBlock snap={snap} />
                  </SnapSection>
                )}
              </div>
            )}
          </section>

          <AgendaSection review={review} users={users} plants={plants} snap={snap} locked={isApproved} missing={missing} />

          <ExecutiveSummarySection review={review} locked={isApproved} />

          {/* ── Approvazione ── */}
          <section>
            <h4 className="text-sm font-semibold text-gray-700 mb-3">{t("management_review.detail.approval")}</h4>
            <div className="flex flex-wrap items-center gap-3 mb-3">
              <span className={`text-xs px-2 py-1 rounded font-medium ${APPROVAL_COLORS[review.approval_status] ?? "bg-gray-100 text-gray-600"}`}>
                {t(`management_review.approval.${review.approval_status}`, review.approval_status)}
              </span>
              {isApproved && review.approved_at && (
                <span className="text-xs text-gray-500">
                  {t("management_review.detail.approved_on", { date: new Date(review.approved_at).toLocaleString(i18n.language || "it") })}
                  {review.approved_by_name && ` — ${review.approved_by_name}`}
                  {review.approval_note && ` — ${review.approval_note}`}
                </span>
              )}
            </div>
            {!isApproved && (
              <div className="space-y-2">
                <textarea
                  value={note}
                  onChange={e => setNote(e.target.value)}
                  placeholder={t("management_review.detail.note_ph")}
                  rows={2}
                  className="w-full border rounded px-3 py-2 text-sm"
                />
                {approveError && <p className="text-xs text-red-600">{approveError}</p>}
                <button
                  onClick={() => approveMutation.mutate()}
                  disabled={approveMutation.isPending || !hasSnapshot || !isCompleted}
                  className="px-4 py-2 bg-green-600 text-white rounded text-sm hover:bg-green-700 disabled:opacity-50"
                >
                  {approveMutation.isPending ? t("management_review.detail.approving") : t("management_review.detail.approve")}
                </button>
                {!hasSnapshot && <p className="text-xs text-amber-600">{t("management_review.detail.need_snapshot")}</p>}
                {hasSnapshot && !isCompleted && <p className="text-xs text-amber-600">{t("management_review.detail.need_completed")}</p>}
                {!review.executive_summary && <p className="text-xs text-gray-400">{t("management_review.detail.summary_recommended")}</p>}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
