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

// ── Helpers ──────────────────────────────────────────────────────────────────

function formatBytes(bytes: number | null): string {
  if (bytes == null) return "—";
  if (bytes < 1024) return `${bytes} B`;
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
  completed: "bg-green-100 text-green-800",
  running:   "bg-blue-100 text-blue-800",
  pending:   "bg-yellow-100 text-yellow-800",
  failed:    "bg-red-100 text-red-800",
  restored:  "bg-purple-100 text-purple-800",
};

function StatusBadge({ status }: { status: BackupRecord["status"] }) {
  const { t } = useTranslation();
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${STATUS_STYLES[status] ?? "bg-gray-100 text-gray-700"}`}>
      {t(`backups.status.${status}`)}
    </span>
  );
}

// ── Confirm modal ─────────────────────────────────────────────────────────────

function ConfirmModal({
  title,
  message,
  confirmLabel,
  danger,
  onConfirm,
  onCancel,
}: {
  title: string;
  message: string;
  confirmLabel: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
        <p className="text-sm text-gray-600 mb-6">{message}</p>
        <div className="flex justify-end gap-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
          >
            Annulla
          </button>
          <button
            onClick={onConfirm}
            className={`px-4 py-2 text-sm rounded-md text-white font-medium ${
              danger ? "bg-red-600 hover:bg-red-700" : "bg-primary-600 hover:bg-primary-700"
            }`}
          >
            {confirmLabel}
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
      const hasRunning = data?.some(b => b.status === "running" || b.status === "pending");
      return hasRunning ? 3000 : false;
    },
  });

  const showFeedback = (type: "ok" | "err", msg: string) => {
    setFeedback({ type, msg });
    setTimeout(() => setFeedback(null), 5000);
  };

  const createMut = useMutation({
    mutationFn: createBackupApi,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["backups"] });
      showFeedback("ok", t("backups.feedback.created"));
    },
    onError: () => showFeedback("err", t("backups.feedback.create_error")),
  });

  const restoreMut = useMutation({
    mutationFn: (id: string) => restoreBackupApi(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["backups"] });
      showFeedback("ok", t("backups.feedback.restored"));
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      showFeedback("err", msg ?? t("backups.feedback.restore_error"));
    },
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteBackupApi(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["backups"] });
      showFeedback("ok", t("backups.feedback.deleted"));
    },
    onError: () => showFeedback("err", t("backups.feedback.delete_error")),
  });

  const handleDownload = (backup: BackupRecord) => {
    const a = document.createElement("a");
    a.href = backupDownloadUrl(backup.id);
    if (token) a.setAttribute("data-token", token); // handled by apiClient interceptor via direct link
    a.download = backup.filename;
    // Il download usa il token JWT come Authorization header; per link diretti
    // usiamo fetch + blob per rispettare l'autenticazione
    fetch(backupDownloadUrl(backup.id), {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.blob())
      .then(blob => {
        const url = URL.createObjectURL(blob);
        a.href = url;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      });
  };

  const isBusy = createMut.isPending || restoreMut.isPending || deleteMut.isPending;

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t("backups.title")}</h1>
          <p className="text-sm text-gray-500 mt-1">{t("backups.subtitle")}</p>
        </div>
        <button
          onClick={() => createMut.mutate()}
          disabled={isBusy}
          className="flex items-center gap-2 bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors disabled:opacity-50"
        >
          {createMut.isPending ? t("backups.creating") : t("backups.create")}
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
      <div className="mb-4 bg-blue-50 border border-blue-200 rounded-md px-4 py-3 text-sm text-blue-800">
        {t("backups.retention_info")}
      </div>

      {/* Tabella */}
      {isLoading ? (
        <p className="text-sm text-gray-500">{t("common.loading")}</p>
      ) : backups.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <p className="text-4xl mb-3">💾</p>
          <p className="text-sm">{t("backups.empty")}</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-500">{t("backups.col.date")}</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">{t("backups.col.filename")}</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">{t("backups.col.size")}</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">{t("backups.col.type")}</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">{t("backups.col.status")}</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">{t("backups.col.created_by")}</th>
                <th className="px-4 py-3 text-right font-medium text-gray-500">{t("backups.col.actions")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {backups.map(b => (
                <tr key={b.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-700 whitespace-nowrap">{formatDate(b.created_at)}</td>
                  <td className="px-4 py-3 text-gray-600 font-mono text-xs max-w-[200px] truncate">{b.filename}</td>
                  <td className="px-4 py-3 text-gray-600">{formatBytes(b.size_bytes)}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                      b.backup_type === "auto"
                        ? "bg-gray-100 text-gray-600"
                        : "bg-indigo-100 text-indigo-700"
                    }`}>
                      {t(`backups.type.${b.backup_type}`)}
                    </span>
                  </td>
                  <td className="px-4 py-3"><StatusBadge status={b.status} /></td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{b.created_by_email ?? "—"}</td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-2">
                      {b.status === "completed" && (
                        <>
                          <button
                            onClick={() => handleDownload(b)}
                            className="text-xs px-2 py-1 rounded border border-gray-300 hover:bg-gray-50 text-gray-600"
                          >
                            {t("backups.action.download")}
                          </button>
                          <button
                            onClick={() => setConfirmRestore(b)}
                            disabled={isBusy}
                            className="text-xs px-2 py-1 rounded border border-amber-400 hover:bg-amber-50 text-amber-700 disabled:opacity-50"
                          >
                            {t("backups.action.restore")}
                          </button>
                        </>
                      )}
                      {b.status === "failed" && (
                        <span className="text-xs text-red-500 max-w-[180px] truncate" title={b.error_message}>
                          {b.error_message.slice(0, 60)}…
                        </span>
                      )}
                      <button
                        onClick={() => setConfirmDelete(b)}
                        disabled={isBusy || b.status === "running"}
                        className="text-xs px-2 py-1 rounded border border-red-300 hover:bg-red-50 text-red-600 disabled:opacity-50"
                      >
                        {t("backups.action.delete")}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Modale conferma restore */}
      {confirmRestore && (
        <ConfirmModal
          title={t("backups.confirm_restore.title")}
          message={t("backups.confirm_restore.message", { filename: confirmRestore.filename })}
          confirmLabel={t("backups.action.restore")}
          danger
          onConfirm={() => {
            restoreMut.mutate(confirmRestore.id);
            setConfirmRestore(null);
          }}
          onCancel={() => setConfirmRestore(null)}
        />
      )}

      {/* Modale conferma elimina */}
      {confirmDelete && (
        <ConfirmModal
          title={t("backups.confirm_delete.title")}
          message={t("backups.confirm_delete.message", { filename: confirmDelete.filename })}
          confirmLabel={t("backups.action.delete")}
          danger
          onConfirm={() => {
            deleteMut.mutate(confirmDelete.id);
            setConfirmDelete(null);
          }}
          onCancel={() => setConfirmDelete(null)}
        />
      )}
    </div>
  );
}
