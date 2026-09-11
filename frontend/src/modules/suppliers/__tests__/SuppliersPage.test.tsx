import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { SuppliersPage } from "../SuppliersPage";

// ── Mock ──────────────────────────────────────────────────────────────────────

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (k: string, opts?: Record<string, unknown>) => (opts && "query" in opts ? `${k}:${opts.query}` : k) }),
}));

vi.mock("../../../i18n", () => ({
  default: { language: "it", t: (k: string) => k },
}));

vi.mock("../../../lib/scrollAndHighlight", () => ({ scrollAndHighlight: vi.fn() }));
vi.mock("../../settings/SupplierEvaluationSettingsPage", () => ({ SupplierEvaluationSettingsPage: () => null }));
vi.mock("../InternalEvaluationSection", () => ({ InternalEvaluationSection: () => null }));

vi.mock("../../../api/client", () => ({
  apiClient: { get: vi.fn(() => Promise.resolve({ data: { results: [] } })), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

vi.mock("../../../api/endpoints/suppliers", () => ({
  suppliersApi: {
    list: vi.fn(),
    get: vi.fn(),
    registerExistingEvaluation: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    suggestCpv: vi.fn(),
    sendQuestionnaire: vi.fn(),
    listQuestionnaires: vi.fn(),
    resendQuestionnaire: vi.fn(),
    evaluateQuestionnaire: vi.fn(),
    listTemplates: vi.fn(),
    createTemplate: vi.fn(),
    updateTemplate: vi.fn(),
    deleteTemplate: vi.fn(),
    ndaList: vi.fn(),
    ndaUpload: vi.fn(),
    exportCsv: vi.fn(),
  },
}));

vi.mock("../../../api/endpoints/reporting", () => ({
  reportingApi: { kpiOverview: vi.fn() },
}));

import { suppliersApi } from "../../../api/endpoints/suppliers";

const mockList = vi.mocked(suppliersApi.list);
const mockQuests = vi.mocked(suppliersApi.listQuestionnaires);

// ── Helper ────────────────────────────────────────────────────────────────────

function makeSupplier(overrides = {}) {
  return {
    id: "sup-1",
    name: "Acme S.p.A.",
    vat_number: "01234567890",
    country: "IT",
    email: "info@acme.it",
    additional_emails: [],
    description: "",
    risk_level: "basso",
    status: "attivo",
    evaluation_date: null,
    evaluation_expires_at: null,
    evaluation_source: "",
    nis2_relevant: false,
    nis2_relevance_criterion: "",
    supply_concentration_pct: null,
    concentration_threshold: "nd",
    cpv_codes: [],
    risk_adj: "basso",
    internal_risk_level: null,
    latest_questionnaire_status: null,
    ...overrides,
  };
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <SuppliersPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockList.mockResolvedValue({ results: [] } as never);
  mockQuests.mockResolvedValue([] as never);
});

// ── Test ──────────────────────────────────────────────────────────────────────

describe("SuppliersPage", () => {
  it("mostra i fornitori in tabella", async () => {
    mockList.mockResolvedValue({ results: [makeSupplier()] } as never);
    renderPage();
    expect(await screen.findByText("Acme S.p.A.")).toBeInTheDocument();
    expect(screen.getByText("01234567890")).toBeInTheDocument();
  });

  it("mostra lo stato vuoto senza fornitori", async () => {
    renderPage();
    expect(await screen.findByText("suppliers.list.empty")).toBeInTheDocument();
  });

  it("la ricerca filtra i fornitori lato client", async () => {
    mockList.mockResolvedValue({
      results: [makeSupplier(), makeSupplier({ id: "sup-2", name: "Beta Srl", vat_number: "09876543210", email: "x@beta.it" })],
    } as never);
    renderPage();
    expect(await screen.findByText("Acme S.p.A.")).toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText("suppliers.list.search_placeholder"), { target: { value: "beta" } });
    expect(screen.getByText("Beta Srl")).toBeInTheDocument();
    expect(screen.queryByText("Acme S.p.A.")).not.toBeInTheDocument();
  });

  it("il tab Questionari mostra i questionari", async () => {
    mockQuests.mockResolvedValue([
      {
        id: "q-1",
        supplier_name: "Acme S.p.A.",
        sent_to: "info@acme.it",
        sent_at: "2026-06-01T10:00:00Z",
        last_sent_at: "2026-06-01T10:00:00Z",
        status: "inviato",
        send_count: 1,
        origin: "piattaforma",
        evaluation_date: null,
        risk_result: null,
        expires_at: null,
      },
    ] as never);
    renderPage();
    fireEvent.click(screen.getByText("suppliers.tabs.questionnaires"));
    expect(await screen.findByText("Acme S.p.A.")).toBeInTheDocument();
    expect(screen.getByText("suppliers.qstatus.waiting")).toBeInTheDocument();
  });

  it("il filtro rischio segue il Rischio Adj e offre i non valutati", async () => {
    renderPage();
    await screen.findByText("suppliers.list.empty");
    const riskSelect = screen.getByDisplayValue("suppliers.list.all_risks");
    fireEvent.change(riskSelect, { target: { value: "alto" } });
    await vi.waitFor(() => expect(mockList).toHaveBeenLastCalledWith({ risk_adj: "alto" }));
    fireEvent.change(riskSelect, { target: { value: "none" } });
    await vi.waitFor(() => expect(mockList).toHaveBeenLastCalledWith({ risk_adj_missing: "true" }));
  });

  it("la scadenza in elenco è quella calcolata dal backend", async () => {
    mockList.mockResolvedValue({
      results: [makeSupplier({
        evaluation_date: "2026-01-10",
        evaluation_expires_at: "2099-01-05",
        evaluation_source: "esistente",
      })],
    } as never);
    renderPage();
    expect(await screen.findByText(new Date("2099-01-05").toLocaleDateString("it"))).toBeInTheDocument();
    expect(screen.getByText("suppliers.eval_source.esistente")).toBeInTheDocument();
  });

  it("il nuovo fornitore non chiede la data di valutazione", async () => {
    renderPage();
    fireEvent.click(await screen.findByText("suppliers.list.new_btn"));
    expect(screen.getByText("suppliers.form.eval_new_hint")).toBeInTheDocument();
    expect(document.querySelector('input[name="evaluation_date"]')).toBeNull();
  });

  it("il tab Questionari distingue le valutazioni esistenti registrate", async () => {
    mockQuests.mockResolvedValue([
      {
        id: "q-2",
        supplier_name: "Storico Srl",
        sent_to: "",
        sent_at: "2025-03-01T00:00:00Z",
        last_sent_at: "2025-03-01T00:00:00Z",
        status: "risposto",
        send_count: 0,
        origin: "esistente",
        evaluation_date: "2025-03-01",
        risk_result: "medio",
        expires_at: "2026-02-24",
        notes: "Questionario cartaceo",
      },
    ] as never);
    renderPage();
    fireEvent.click(screen.getByText("suppliers.tabs.questionnaires"));
    expect(await screen.findByText("Storico Srl")).toBeInTheDocument();
    expect(screen.getByText("suppliers.quests.origin_existing")).toHaveAttribute("title", "Questionario cartaceo");
    expect(screen.queryByText("suppliers.quests.resend")).not.toBeInTheDocument();
    expect(screen.getByText("suppliers.register_existing.btn")).toBeInTheDocument();
  });
});
