import { apiClient } from "../client";

export interface BackupRecord {
  id: string;
  filename: string;
  size_bytes: number | null;
  size_mb: number | null;
  status: "pending" | "running" | "completed" | "failed" | "restoring" | "restored";
  backup_type: "auto" | "manual" | "imported";
  notes: string;
  error_message: string;
  completed_at: string | null;
  created_at: string;
  created_by_email: string | null;
}

export async function listBackupsApi(): Promise<BackupRecord[]> {
  const res = await apiClient.get("/backups/");
  return res.data.results ?? res.data;
}

export async function createBackupApi(): Promise<BackupRecord> {
  const res = await apiClient.post("/backups/create/");
  return res.data;
}

// Import di un backup scaricato in precedenza (.dump / .dump.enc).
// Il backend valida magic PGDMP e, per i cifrati, la decifrabilità con la
// chiave corrente prima di accettare il file.
export async function importBackupApi(file: File): Promise<BackupRecord> {
  const form = new FormData();
  form.append("file", file);
  const res = await apiClient.post("/backups/import/", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
}

// Risponde 202: il restore è asincrono (Celery). Lo stato passa a "restoring"
// e va monitorato via polling su listBackupsApi finché non torna definitivo.
export async function restoreBackupApi(id: string): Promise<void> {
  await apiClient.post(`/backups/${id}/restore/`);
}

export async function deleteBackupApi(id: string): Promise<void> {
  await apiClient.delete(`/backups/${id}/remove/`);
}

export function backupDownloadUrl(id: string): string {
  return `/api/v1/backups/${id}/download/`;
}
