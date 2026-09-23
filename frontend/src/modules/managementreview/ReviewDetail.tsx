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
import { useAuthStore } from "../../store/auth";
import { ApprovalSection } from "./ApprovalSection";
import { DeliberatedDocuments } from "./DeliberatedDocuments";
import { ParticipantsSection } from "./ParticipantsSection";
import { ReportLogoPicker } from "./ReportLogoPicker";
import { SnapSection, fmtDate, type Snap } from "./shared";
import { OutcomeSummary } from "./TargetedDocuments";

// Scrittura sul riesame: governance. Un componente dell'organo con account
// (es. un consigliere) lo legge e lo approva, senza modificarlo.
const WRITE_ROLES = ["super_admin", "compliance_officer"];

type Plant = { id: string; code: string; name: string };

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
      } else if (data?.code === "document_outcome_missing") {
        onMissing(data.missing ?? []);
        setError(t("management_review.targeted.outcomes_missing", { count: (data.missing ?? []).length }));
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
          {!locked && review.status === "pianificato" && (
            <button onClick={() => start.mutate()} disabled={start.isPending} className="px-3 py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700 disabled:opacity-50">
              ▶ {t("management_review.detail.start_meeting")}
            </button>
          )}
          {!locked && review.status === "in_corso" && (
            <button onClick={() => complete.mutate()} disabled={complete.isPending} className="px-3 py-1 bg-green-600 text-white rounded text-xs hover:bg-green-700 disabled:opacity-50">
              ✓ {t("management_review.detail.mark_completed")}
            </button>
          )}
        </div>
        {error && <p className="text-xs text-red-600 mt-1">{error}</p>}
      </div>
      {review.kind === "mirato" ? (
        <p className="text-xs text-gray-500 self-center">{t("management_review.targeted.no_next_review")}</p>
      ) : <div>
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
      </div>}
    </section>
  );
}

// ── Dettaglio ────────────────────────────────────────────────────────────────

export function ReviewDetail({ review, users, plants, onClose }: { review: ManagementReview; users: GrcUser[]; plants: Plant[]; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [snapshotError, setSnapshotError] = useState("");
  const role = useAuthStore(s => s.user?.role) ?? "";
  const isGovernance = WRITE_ROLES.includes(role);
  const [downloading, setDownloading] = useState<"" | "html" | "pdf">("");
  const [missing, setMissing] = useState<string[]>([]);

  const snapshotMutation = useMutation({
    mutationFn: () => managementReviewApi.generateSnapshot(review.id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["management-review"] }); setSnapshotError(""); },
    onError: e => setSnapshotError(reviewErrorMessage(e, t("management_review.detail.snapshot_error"))),
  });

  async function handleDownload(fmt: "html" | "pdf") {
    setDownloading(fmt);
    try {
      const date = review.review_date?.replace(/-/g, "") ?? "";
      const prefix = review.kind === "mirato" ? "riesame_mirato" : "riesame";
      await managementReviewApi.downloadReport(review.id, `${prefix}_${review.id}_${date}.${fmt}`, fmt);
    } finally {
      setDownloading("");
    }
  }

  const snap = (review.snapshot_generated_at ? review.snapshot_data : null) as Snap | null;
  const isApproved = review.approval_status === "approvato";
  const locked = isApproved || !isGovernance;
  const hasSnapshot = !!review.snapshot_generated_at;
  const isTargeted = review.kind === "mirato";
  // Snapshot generati prima dei dettagli: solo contatori.
  const legacySnapshot = !!snap && (
    !("azioni_precedenti" in snap)
    // snapshot congelati prima dei documenti obbligatori non approvati
    || !("elenco_non_approvati" in ((snap.documenti as Record<string, unknown>) ?? {}))
  );

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl flex flex-col max-h-[92vh]">
        {/* Header */}
        <div className="flex items-start justify-between gap-3 px-6 py-4 border-b border-gray-100 shrink-0">
          <div className="min-w-0">
            <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              {review.title}
              {isTargeted && (
                <span className="text-xs font-medium px-2 py-0.5 rounded bg-purple-100 text-purple-700">
                  {t("management_review.targeted.badge")}
                </span>
              )}
            </h3>
            {isTargeted && <p className="text-xs text-purple-700 mt-0.5">{t("management_review.targeted.not_periodic")}</p>}
            <p className="text-xs text-gray-400 mt-0.5">
              {t("management_review.detail.meeting_date")} {fmtDate(review.review_date)}
              <span className="ml-2">· {review.plant_name ?? t("management_review.list.org_wide")}</span>
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {(hasSnapshot || isTargeted) && (["pdf", "html"] as const).map(fmt => (
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
          <div>
            <MeetingSection review={review} locked={locked} onMissing={setMissing} />
            <ReportLogoPicker review={review} canWrite={isGovernance} />
          </div>

          <ParticipantsSection review={review} users={users} locked={isApproved} canWrite={isGovernance} />

          {/* ── Dati riesame (snapshot): solo nel riesame completo §9.3 ── */}
          {!isTargeted && <section>
            <h4 className="text-sm font-semibold text-gray-700 mb-2">{t("management_review.detail.review_data")}</h4>
            {!hasSnapshot ? (
              <div className="border border-dashed border-gray-300 rounded p-4 text-center">
                <p className="text-sm text-gray-500 mb-3">{t("management_review.detail.no_snapshot")}</p>
                {snapshotError && <p className="text-xs text-red-600 mb-2">{snapshotError}</p>}
                {isGovernance && <button
                  onClick={() => snapshotMutation.mutate()}
                  disabled={snapshotMutation.isPending}
                  className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
                >
                  {snapshotMutation.isPending ? t("management_review.detail.generating") : t("management_review.detail.generate_snapshot")}
                </button>}
              </div>
            ) : (
              <div className="space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-xs text-green-700">
                    {t("management_review.detail.snapshot_generated", { date: new Date(review.snapshot_generated_at!).toLocaleString(i18n.language || "it") })}
                  </p>
                  <button
                    onClick={() => snapshotMutation.mutate()}
                    disabled={snapshotMutation.isPending || locked}
                    title={isApproved ? t("management_review.detail.regen_locked") : t("management_review.detail.regen_tip")}
                    className="text-xs px-2 py-1 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-40 shrink-0"
                  >
                    {snapshotMutation.isPending ? "..." : t("management_review.detail.regen")}
                  </button>
                </div>
                {snapshotError && <p className="text-xs text-red-600">{snapshotError}</p>}
                {legacySnapshot && !locked && (
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
          </section>}

          <AgendaSection review={review} users={users} plants={plants} snap={snap} locked={locked} missing={missing} />

          {!isTargeted && <ExecutiveSummarySection review={review} locked={locked} />}

          <ApprovalSection review={review} isGovernance={isGovernance} onMissing={setMissing} />

          {isTargeted
            ? <OutcomeSummary review={review} isGovernance={isGovernance} />
            : <DeliberatedDocuments review={review} snap={snap} isGovernance={isGovernance} />}
        </div>
      </div>
    </div>
  );
}
