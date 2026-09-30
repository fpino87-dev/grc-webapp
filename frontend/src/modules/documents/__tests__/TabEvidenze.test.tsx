import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TabEvidenze } from "../TabEvidenze";
import type { Evidence } from "../../../api/endpoints/documents";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

vi.mock("../../../i18n", () => ({ default: { language: "it", t: (k: string) => k } }));

vi.mock("../../../store/auth", () => ({
  useAuthStore: (sel: (s: unknown) => unknown) => sel({ selectedPlant: { id: "plant-b" } }),
}));

vi.mock("../../../api/endpoints/documents", () => ({
  documentsApi: {
    evidences: vi.fn(), removeEvidence: vi.fn(), shareEvidence: vi.fn(),
    shareDocument: vi.fn(), createEvidence: vi.fn(), downloadEvidence: vi.fn(),
    update: vi.fn(), linkControls: vi.fn(),
  },
}));

vi.mock("../../../api/endpoints/controls", () => ({
  controlsApi: { frameworks: vi.fn(), instances: vi.fn(), linkEvidence: vi.fn() },
}));

vi.mock("../../../api/endpoints/plants", () => ({ plantsApi: { list: vi.fn() } }));

import { documentsApi } from "../../../api/endpoints/documents";
import { plantsApi } from "../../../api/endpoints/plants";

function makeEvidence(overrides: Partial<Evidence>): Evidence {
  return {
    id: "ev-1", title: "Report pentest", description: "", evidence_type: "report",
    valid_until: null, plant: "plant-b", plant_name: "Plant B", file_path: "",
    uploaded_by: null, uploaded_by_username: null, control_instances_count: 0,
    shared_plant_names: [], is_shared_with_current: false, can_manage: true,
    created_at: "2026-09-01T00:00:00Z",
    ...overrides,
  };
}

function renderTab() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <TabEvidenze />
    </QueryClientProvider>,
  );
}

describe("TabEvidenze — condivisione fra siti", () => {
  beforeEach(() => vi.clearAllMocks());

  it("l'evidenza ricevuta in condivisione è segnalata e non si elimina né si ricondivide", async () => {
    vi.mocked(documentsApi.evidences).mockResolvedValue({
      results: [makeEvidence({
        plant: "plant-a", plant_name: "Plant A", is_shared_with_current: true, can_manage: false,
        shared_plant_names: [{ id: "plant-b", name: "Plant B", code: "B" }],
      })],
      count: 1,
    });
    renderTab();
    expect(await screen.findByText("documents.evidence.share.badge", { exact: false })).toBeInTheDocument();
    expect(screen.queryByTitle("documents.actions.share_hint")).not.toBeInTheDocument();
    expect(screen.queryByTitle("documents.evidence.actions.delete_title")).not.toBeInTheDocument();
  });

  it("il sito proprietario condivide l'evidenza con un altro sito", async () => {
    vi.mocked(documentsApi.evidences).mockResolvedValue({ results: [makeEvidence({})], count: 1 });
    vi.mocked(plantsApi.list).mockResolvedValue([
      { id: "plant-b", code: "B", name: "Plant B" },
      { id: "plant-c", code: "C", name: "Plant C" },
    ] as never);
    vi.mocked(documentsApi.shareEvidence).mockResolvedValue({ shared_with: [] });
    renderTab();
    fireEvent.click(await screen.findByTitle("documents.actions.share_hint"));
    // il sito proprietario non è fra quelli selezionabili
    fireEvent.click(await screen.findByText("Plant C"));
    expect(screen.getAllByText("Plant B")).toHaveLength(1);
    fireEvent.click(screen.getByText("actions.save"));
    await waitFor(() => expect(documentsApi.shareEvidence).toHaveBeenCalledWith("ev-1", ["plant-c"]));
  });
});
