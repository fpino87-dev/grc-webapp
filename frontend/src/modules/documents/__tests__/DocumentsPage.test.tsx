import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { DocumentsPage } from "../DocumentsPage";

// ── Mock ──────────────────────────────────────────────────────────────────────

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

vi.mock("../../../i18n", () => ({
  default: { language: "it", t: (k: string) => k },
}));

vi.mock("../../../store/auth", () => ({
  useAuthStore: (selector: (s: { selectedPlant: null }) => unknown) => selector({ selectedPlant: null }),
}));

vi.mock("../../../lib/scrollAndHighlight", () => ({ scrollAndHighlight: vi.fn() }));

vi.mock("../../../api/endpoints/documents", () => ({
  documentsApi: {
    list: vi.fn(),
    evidences: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    submit: vi.fn(),
    approve: vi.fn(),
    reject: vi.fn(),
    remove: vi.fn(),
    uploadVersion: vi.fn(),
    downloadDocument: vi.fn(),
    downloadEvidence: vi.fn(),
    createEvidence: vi.fn(),
    removeEvidence: vi.fn(),
    shareDocument: vi.fn(),
    linkControls: vi.fn(),
  },
}));

vi.mock("../../../api/endpoints/controls", () => ({
  controlsApi: { frameworks: vi.fn(), instances: vi.fn(), linkEvidence: vi.fn() },
}));

vi.mock("../../../api/endpoints/plants", () => ({ plantsApi: { list: vi.fn() } }));
vi.mock("../../../api/endpoints/suppliers", () => ({ suppliersApi: { list: vi.fn() } }));

import { documentsApi } from "../../../api/endpoints/documents";

const mockList = vi.mocked(documentsApi.list);
const mockEvidences = vi.mocked(documentsApi.evidences);

// ── Helper ────────────────────────────────────────────────────────────────────

function makeDoc(overrides = {}) {
  return {
    id: "doc-1",
    title: "Politica sicurezza informazioni",
    document_code: "D-ITA-INF-001",
    document_type: "policy",
    category: "politica",
    status: "approvato",
    is_mandatory: false,
    review_due_date: null,
    expiry_date: null,
    approved_at: null,
    plant: "p-1",
    plant_code: "ITA",
    plant_name: "Stabilimento ITA",
    latest_version: null,
    shared_plant_names: [],
    is_shared_with_current: false,
    supplier: null,
    supplier_name: null,
    ...overrides,
  };
}

function makeEvidence(overrides = {}) {
  return {
    id: "ev-1",
    title: "Screenshot configurazione MFA",
    evidence_type: "screenshot",
    valid_until: null,
    description: "",
    plant_name: "Stabilimento ITA",
    uploaded_by_username: "admin",
    control_instances_count: 0,
    linked_controls: [],
    file_url: null,
    file_path: null,
    ...overrides,
  };
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <DocumentsPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockList.mockResolvedValue({ results: [] } as never);
  mockEvidences.mockResolvedValue({ results: [] } as never);
});

// ── Test ──────────────────────────────────────────────────────────────────────

describe("DocumentsPage", () => {
  it("mostra i documenti in tabella", async () => {
    mockList.mockResolvedValue({ results: [makeDoc()] } as never);
    renderPage();
    expect(await screen.findByText("Politica sicurezza informazioni")).toBeInTheDocument();
    expect(screen.getByText("D-ITA-INF-001")).toBeInTheDocument();
  });

  it("esclude i contratti dal tab Documenti e dai contatori del banner", async () => {
    const contrattoScaduto = makeDoc({
      id: "doc-nda",
      title: "NDA Fornitore XYZ",
      document_type: "contratto",
      is_mandatory: true,
      status: "bozza",
      expiry_date: "2020-01-01",
      review_due_date: "2020-01-01",
    });
    mockList.mockResolvedValue({ results: [makeDoc(), contrattoScaduto] } as never);
    renderPage();
    expect(await screen.findByText("Politica sicurezza informazioni")).toBeInTheDocument();
    // il contratto non compare nella lista...
    expect(screen.queryByText("NDA Fornitore XYZ")).not.toBeInTheDocument();
    // ...e non gonfia i contatori del banner (prima del fix mostrava 1 scaduto/1 mandatory gap)
    expect(screen.queryByText("documents.dashboard.expired")).not.toBeInTheDocument();
    expect(screen.queryByText("documents.dashboard.mandatory_gap")).not.toBeInTheDocument();
  });

  it("il tab NDA mostra i contratti", async () => {
    mockList.mockImplementation(((params: Record<string, string>) =>
      Promise.resolve(
        params?.document_type === "contratto"
          ? { results: [makeDoc({ id: "doc-nda", title: "NDA Fornitore XYZ", document_type: "contratto", supplier_name: "Fornitore XYZ" })] }
          : { results: [] }
      )) as never);
    renderPage();
    fireEvent.click(screen.getByText(/documents.tabs.nda/));
    expect(await screen.findByText("NDA Fornitore XYZ")).toBeInTheDocument();
    expect(screen.getByText("Fornitore XYZ")).toBeInTheDocument();
  });

  it("il tab Evidenze mostra le evidenze", async () => {
    mockEvidences.mockResolvedValue({ results: [makeEvidence()] } as never);
    renderPage();
    fireEvent.click(screen.getByText(/documents.tabs.evidences/));
    expect(await screen.findByText("Screenshot configurazione MFA")).toBeInTheDocument();
  });
});
