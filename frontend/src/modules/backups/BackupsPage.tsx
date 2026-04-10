import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  listBackupsApi,
  createBackupApi,
  restoreBackupApi,
  deleteBackupApi,
  backupDownloadUrl,
  type BackupRecord,
} from "../../api/endpoints/backups";
import { useAuthStore } from "../../store/auth";

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatBytes(bytes: number | null): string {
  if (bytes == null) return "—";
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("it-IT", {
    day: "2-digit", month: "2-digit", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

// ── Status badge ──────────────────────────────────────────────────────────────

const STATUS_STYLES: Record<string, string> = {
  completed: "bg-green-100 text-green-800 border-green-200",
  running:   "bg-blue-100  text-blue-800  border-blue-200",
  pending:   "bg-yellow-100 text-yellow-800 border-yellow-200",
  failed:    "bg-red-100   text-red-800   border-red-200",
  restored:  "bg-purple-100 text-purple-800 border-purple-200",
};

const STATUS_DOT: Record<string, string> = {
  completed: "bg-green-500",
  running:   "bg-blue-500 animate-pulse",
  pending:   "bg-yellow-500 animate-pulse",
  failed:    "bg-red-500",
  restored:  "bg-purple-500",
};

function StatusBadge({ status }: { status: BackupRecord["status"] }) {
  const { t } = useTranslation();
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${STATUS_STYLES[status] ?? "bg-gray-100 text-gray-700 border-gray-200"}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${STATUS_DOT[status] ?? "bg-gray-400"}`} />
      {t(`backups.status.${status}`)}
    </span>
  );
}

// ── Confirm modal ─────────────────────────────────────────────────────────────

function ConfirmModal({
  title, message, confirmLabel, danger, onConfirm, onCancel,
}: {
  title: string; message: string; confirmLabel: string;
  danger?: boolean; onConfirm: () => void; onCancel: () => void;
}) {
  const { t } = useTranslation();
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 px-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
        <p className="text-sm text-gray-600 mb-6 leading-relaxed">{message}</p>
        <div className="flex justify-end gap-3">
          <button onClick={onCancel}
            className="px-4 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50 text-gray-700">
            {t("actions.cancel")}
          </button>
          <button onClick={onConfirm}
            className={`px-4 py-2 text-sm rounded-md text-white font-medium ${danger ? "bg-red-600 hover:bg-red-700" : "bg-primary-600 hover:bg-primary-700"}`}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Backup card ───────────────────────────────────────────────────────────────

function BackupCard({
  backup,
  onRestore,
  onDelete,
  onDownload,
  isBusy,
}: {
  backup: BackupRecord;
  onRestore: () => void;
  onDelete: () => void;
  onDownload: () => void;
  isBusy: boolean;
}) {
  const { t } = useTranslation();
  const isCompleted = backup.status === "completed";
  const isRunning   = backup.status === "running" || backup.status === "pending";

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 hover:shadow-sm transition-shadow">
      {/* Row 1 — status + data + tipo */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 flex-wrap">
          <StatusBadge status={backup.status} />
          <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
            backup.backup_type === "auto" ? "bg-gray-100 text-gray-600" : "bg-indigo-100 text-indigo-700"
          }`}>
            {t(`backups.type.${backup.backup_type}`)}
          </span>
        </div>
        <span className="text-xs text-gray-400 whitespace-nowrap">{formatDate(backup.created_at)}</span>
      </div>

      {/* Row 2 — filename */}
      <p className="font-mono text-xs text-gray-600 bg-gray-50 rounded px-2 py-1.5 mb-3 break-all">
        {backup.filename || "—"}
      </p>

      {/* Row 3 — dimensione + utente */}
      <div className="flex items-center gap-4 text-xs text-gray-500 mb-3">
        <span>
          <span className="font-medium text-gray-700">{t("backups.col.size")}:</span>{" "}
          {formatBytes(backup.size_bytes)}
        </span>
        {backup.created_by_email && (
          <span>
            <span className="font-medium text-gray-700">{t("backups.col.created_by")}:</span>{" "}
            {backup.created_by_email}
          </span>
        )}
        {backup.completed_at && (
          <span>
            <span className="font-medium text-gray-700">{t("backups.col.completed")}:</span>{" "}
            {formatDate(backup.completed_at)}
          </span>
        )}
      </div>

      {/* Errore (se failed) */}
      {backup.status === "failed" && backup.error_message && (
        <div className="mb-3 px-3 py-2 bg-red-50 border border-red-100 rounded text-xs text-red-700 break-all">
          {backup.error_message}
        </div>
      )}

      {/* Row 4 — azioni */}
      <div className="flex items-center gap-2 flex-wrap pt-1 border-t border-gray-100">
        {isCompleted && (
          <>
            <button
              onClick={onDownload}
              disabled={isBusy}
              className="flex items-center gap-1 text-xs px-3 py-1.5 rounded-md border border-gray-300 hover:bg-gray-50 text-gray-700 disabled:opacity-50"
            >
              ⬇ {t("backups.action.download")}
            </button>
            <button
              onClick={onRestore}
              disabled={isBusy}
              className="flex items-center gap-1 text-xs px-3 py-1.5 rounded-md border border-amber-400 hover:bg-amber-50 text-amber-700 font-medium disabled:opacity-50"
            >
              ↩ {t("backups.action.restore")}
            </button>
          </>
        )}
        {isRunning && (
          <span className="text-xs text-blue-600 italic">{t("backups.creating")}</span>
        )}
        <div className="ml-auto">
          <button
            onClick={onDelete}
            disabled={isBusy || isRunning}
            className="flex items-center gap-1 text-xs px-3 py-1.5 rounded-md border border-red-300 hover:bg-red-50 text-red-600 font-medium disabled:opacity-50"
          >
            🗑 {t("backups.action.delete")}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function BackupsPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const token = useAuthStore(s => s.token);

  const [confirmRestore, setConfirmRestore] = useState<BackupRecord | null>(null);
  const [confirmDelete,  setConfirmDelete]  = useState<BackupRecord | null>(null);
  const [feedback, setFeedback] = useState<{ type: "ok" | "err"; msg: string } | null>(null);

  const { data: backups = [], isLoading } = useQuery({
    queryKey: ["backups"],
    queryFn: listBackupsApi,
    refetchInterval: (q) => {
      const data = q.state.data as BackupRecord[] | undefined;
      return data?.some(b => b.status === "running" || b.status === "pending") ? 3000 : false;
    },
  });

  const showFeedback = (type: "ok" | "err", msg: string) => {
    setFeedback({ type, msg });
    setTimeout(() => setFeedback(null), 5000);
  };

  const createMut = useMutation({
    mutationFn: createBackupApi,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["backups"] }); showFeedback("ok", t("backups.feedback.created")); },
    onError:   () => showFeedback("err", t("backups.feedback.create_error")),
  });

  const restoreMut = useMutation({
    mutationFn: (id: string) => restoreBackupApi(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["backups"] }); showFeedback("ok", t("backups.feedback.restored")); },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      showFeedback("err", msg ?? t("backups.feedback.restore_error"));
    },
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteBackupApi(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["backups"] }); showFeedback("ok", t("backups.feedback.deleted")); },
    onError:   () => showFeedback("err", t("backups.feedback.delete_error")),
  });

  const handleDownload = (backup: BackupRecord) => {
    fetch(backupDownloadUrl(backup.id), { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.blob())
      .then(blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = backup.filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      });
  };

  const isBusy = createMut.isPending || restoreMut.isPending || deleteMut.isPending;

  // Ordine: running/pending in cima, poi per data desc
  const sorted = [...backups].sort((a, b) => {
    const priority = (s: string) => (s === "running" || s === "pending") ? 0 : 1;
    if (priority(a.status) !== priority(b.status)) return priority(a.status) - priority(b.status);
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });

  return (
    <div className="p-6 max-w-3xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between mb-6 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t("backups.title")}</h1>
          <p className="text-sm text-gray-500 mt-1">{t("backups.subtitle")}</p>
        </div>
        <button
          onClick={() => createMut.mutate()}
          disabled={isBusy}
          className="shrink-0 flex items-center gap-2 bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors disabled:opacity-50"
        >
          {createMut.isPending ? t("backups.creating") : `💾 ${t("backups.create")}`}
        </button>
      </div>

      {/* Feedback */}
      {feedback && (
        <div className={`mb-4 px-4 py-3 rounded-md text-sm font-medium ${
          feedback.type === "ok"
            ? "bg-green-50 text-green-800 border border-green-200"
            : "bg-red-50 text-red-800 border border-red-200"
        }`}>
          {feedback.msg}
        </div>
      )}

      {/* Info retention */}
      <div className="mb-6 bg-blue-50 border border-blue-200 rounded-md px-4 py-3 text-sm text-blue-800">
        ℹ {t("backups.retention_info")}
      </div>

      {/* Conteggio */}
      {!isLoading && backups.length > 0 && (
        <p className="text-xs text-gray-400 mb-3">{backups.length} backup</p>
      )}

      {/* Lista card */}
      {isLoading ? (
        <p className="text-sm text-gray-500">{t("common.loading")}</p>
      ) : sorted.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <p className="text-5xl mb-3">💾</p>
          <p className="text-sm">{t("backups.empty")}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {sorted.map(b => (
            <BackupCard
              key={b.id}
              backup={b}
              isBusy={isBusy}
              onDownload={() => handleDownload(b)}
              onRestore={() => setConfirmRestore(b)}
              onDelete={() => setConfirmDelete(b)}
            />
          ))}
        </div>
      )}

      {/* Modale restore */}
      {confirmRestore && (
        <ConfirmModal
          title={t("backups.confirm_restore.title")}
          message={t("backups.confirm_restore.message", { filename: confirmRestore.filename })}
          confirmLabel={t("backups.action.restore")}
          danger
          onConfirm={() => { restoreMut.mutate(confirmRestore.id); setConfirmRestore(null); }}
          onCancel={() => setConfirmRestore(null)}
        />
      )}

      {/* Modale elimina */}
      {confirmDelete && (
        <ConfirmModal
          title={t("backups.confirm_delete.title")}
          message={t("backups.confirm_delete.message", { filename: confirmDelete.filename })}
          confirmLabel={t("backups.action.delete")}
          danger
          onConfirm={() => { deleteMut.mutate(confirmDelete.id); setConfirmDelete(null); }}
          onCancel={() => setConfirmDelete(null)}
        />
      )}
    </div>
  );
}
