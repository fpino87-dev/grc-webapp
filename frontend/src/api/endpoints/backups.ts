import { apiClient } from "../client";

export interface BackupRecord {
  id: string;
  filename: string;
  size_bytes: number | null;
  size_mb: number | null;
  status: "pending" | "running" | "completed" | "failed" | "restored";
  backup_type: "auto" | "manual";
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

export async function restoreBackupApi(id: string): Promise<void> {
  await apiClient.post(`/backups/${id}/restore/`);
}

export async function deleteBackupApi(id: string): Promise<void> {
  await apiClient.delete(`/backups/${id}/remove/`);
}

export function backupDownloadUrl(id: string): string {
  return `/api/v1/backups/${id}/download/`;
}
