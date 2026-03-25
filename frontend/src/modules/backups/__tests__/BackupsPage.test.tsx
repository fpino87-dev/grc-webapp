import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { BackupsPage } from "../BackupsPage";

// ── Mock ──────────────────────────────────────────────────────────────────────

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

vi.mock("../../../store/auth", () => ({
  useAuthStore: () => ({ token: "test-token" }),
}));

vi.mock("../../../api/endpoints/backups", () => ({
  listBackupsApi: vi.fn(),
  createBackupApi: vi.fn(),
  restoreBackupApi: vi.fn(),
  deleteBackupApi: vi.fn(),
  backupDownloadUrl: (id: string) => `/api/v1/backups/${id}/download/`,
}));

import {
  listBackupsApi,
  createBackupApi,
  deleteBackupApi,
} from "../../../api/endpoints/backups";

const mockList = vi.mocked(listBackupsApi);
const mockCreate = vi.mocked(createBackupApi);
const mockDelete = vi.mocked(deleteBackupApi);

// ── Helper ────────────────────────────────────────────────────────────────────

function makeBackup(overrides = {}) {
  return {
    id: "uuid-1",
    filename: "backup_20260325_020000_auto.dump",
    size_bytes: 512000,
    size_mb: 0.49,
    status: "completed" as const,
    backup_type: "auto" as const,
    notes: "",
    error_message: "",
    completed_at: "2026-03-25T02:00:00Z",
    created_at: "2026-03-25T02:00:00Z",
    created_by_email: "adm***@test.com",
    ...overrides,
  };
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <BackupsPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

// ── Test ──────────────────────────────────────────────────────────────────────

describe("BackupsPage", () => {
  beforeEach(() => vi.clearAllMocks());

  it("mostra loading inizialmente", () => {
    mockList.mockReturnValue(new Promise(() => {})); // never resolves
    renderPage();
    expect(screen.getByText("common.loading")).toBeInTheDocument();
  });

  it("mostra messaggio vuoto se nessun backup", async () => {
    mockList.mockResolvedValue([]);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("backups.empty")).toBeInTheDocument();
    });
  });

  it("mostra la lista dei backup", async () => {
    mockList.mockResolvedValue([makeBackup()]);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("backup_20260325_020000_auto.dump")).toBeInTheDocument();
    });
  });

  it("pulsante crea backup è visibile", async () => {
    mockList.mockResolvedValue([]);
    renderPage();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "backups.create" })).toBeInTheDocument();
    });
  });

  it("click crea backup chiama createBackupApi", async () => {
    mockList.mockResolvedValue([]);
    mockCreate.mockResolvedValue(makeBackup({ status: "completed" }));

    renderPage();
    await waitFor(() => screen.getByRole("button", { name: "backups.create" }));

    fireEvent.click(screen.getByRole("button", { name: "backups.create" }));
    await waitFor(() => expect(mockCreate).toHaveBeenCalledOnce());
  });

  it("backup fallito mostra messaggio di errore troncato", async () => {
    mockList.mockResolvedValue([
      makeBackup({
        status: "failed",
        error_message: "pg_dump: error: connection to server failed: FATAL: password authentication failed",
      }),
    ]);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/pg_dump.*error/)).toBeInTheDocument();
    });
  });

  it("backup in corso NON mostra pulsante elimina abilitato", async () => {
    mockList.mockResolvedValue([makeBackup({ status: "running" })]);
    renderPage();
    await waitFor(() => {
      const deleteBtn = screen.getByRole("button", { name: "backups.action.delete" });
      expect(deleteBtn).toBeDisabled();
    });
  });

  it("click elimina mostra modal di conferma", async () => {
    mockList.mockResolvedValue([makeBackup()]);
    renderPage();
    await waitFor(() => screen.getByRole("button", { name: "backups.action.delete" }));

    fireEvent.click(screen.getByRole("button", { name: "backups.action.delete" }));

    await waitFor(() => {
      expect(screen.getByText("backups.confirm_delete.title")).toBeInTheDocument();
    });
  });

  it("conferma elimina chiama deleteBackupApi", async () => {
    mockList.mockResolvedValue([makeBackup()]);
    mockDelete.mockResolvedValue(undefined);

    renderPage();
    await waitFor(() => screen.getByRole("button", { name: "backups.action.delete" }));
    fireEvent.click(screen.getByRole("button", { name: "backups.action.delete" }));

    await waitFor(() => screen.getByText("backups.confirm_delete.title"));
    // When modal is open there are two delete buttons: row + modal confirm.
    // Pick the modal confirm (last one).
    const deleteBtns = screen.getAllByRole("button", { name: "backups.action.delete" });
    fireEvent.click(deleteBtns[deleteBtns.length - 1]);

    await waitFor(() => expect(mockDelete).toHaveBeenCalledWith("uuid-1"));
  });
});
