import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TabDocEvidence } from "../drawer/TabDocEvidence";
import type { RequirementsCheck } from "../../../api/endpoints/controls";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (k: string) => k, i18n: { language: "it" } }),
}));

vi.mock("../../../i18n", () => ({ default: { language: "it" } }));

vi.mock("../../../api/endpoints/controls", () => ({
  controlsApi: {
    linkEvidence: vi.fn(), unlinkEvidence: vi.fn(),
    linkDocument: vi.fn(), unlinkDocument: vi.fn(),
  },
}));

vi.mock("../../../api/endpoints/documents", () => ({
  documentsApi: { searchEvidences: vi.fn(), searchDocuments: vi.fn(), createEvidence: vi.fn() },
}));

// Sito selezionato in alto DIVERSO da quello del controllo: la ricerca deve
// usare il sito del controllo.
vi.mock("../../../store/auth", () => ({
  useAuthStore: (sel: (s: unknown) => unknown) => sel({ selectedPlant: { id: "plant-selected" } }),
}));

import { controlsApi } from "../../../api/endpoints/controls";
import { documentsApi } from "../../../api/endpoints/documents";

const requirements = {
  satisfied: true, missing_documents: [], missing_evidences: [],
  expired_evidences: [], warnings: [], not_applicable: false,
} as unknown as RequirementsCheck;

function renderTab() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <TabDocEvidence
        instanceId="inst-1"
        evidences={[]}
        documents={[]}
        requirements={requirements}
        evidenceRequirement={{ documents: [], evidences: [], min_documents: 0, min_evidences: 0 }}
        plantId="plant-control"
      />
    </QueryClientProvider>,
  );
}

const K = "controls.drawer.docs";

function typeSearch(index: number, value: string) {
  fireEvent.change(screen.getAllByPlaceholderText(`${K}.search_placeholder`)[index], { target: { value } });
}

describe("TabDocEvidence — collega esistenti", () => {
  beforeEach(() => vi.clearAllMocks());

  it("cerca evidenze e documenti nel sito del controllo, non in quello selezionato", async () => {
    vi.mocked(documentsApi.searchDocuments).mockResolvedValue({ results: [], count: 0 });
    vi.mocked(documentsApi.searchEvidences).mockResolvedValue({ results: [], count: 0 });
    renderTab();
    typeSearch(0, "policy");
    typeSearch(1, "report");
    await waitFor(() => expect(documentsApi.searchEvidences).toHaveBeenCalledWith("report", "plant-control"));
    expect(documentsApi.searchDocuments).toHaveBeenCalledWith("policy", "plant-control");
    // nessun risultato: lo si dice, invece di non mostrare nulla
    expect(await screen.findByText(`${K}.no_linkable_evidence`)).toBeInTheDocument();
    expect(await screen.findByText(`${K}.no_linkable_docs`)).toBeInTheDocument();
  });

  it("mostra l'errore se il collegamento dell'evidenza viene rifiutato", async () => {
    vi.mocked(documentsApi.searchEvidences).mockResolvedValue({
      results: [{ id: "ev-1", title: "Report pentest", evidence_type: "report", valid_until: null }],
      count: 1,
    } as never);
    vi.mocked(controlsApi.linkEvidence).mockRejectedValue(new Error("404"));
    renderTab();
    typeSearch(1, "report");
    fireEvent.click(await screen.findByText("Report pentest"));
    expect(await screen.findByText(`${K}.link_evidence_failed`)).toBeInTheDocument();
    expect(controlsApi.linkEvidence).toHaveBeenCalledWith("inst-1", "ev-1");
  });
});
