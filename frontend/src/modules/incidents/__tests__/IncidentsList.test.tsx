import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { IncidentsList } from "../IncidentsList";

// ── Mock ──────────────────────────────────────────────────────────────────────

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

vi.mock("../../../i18n", () => ({
  default: { language: "it", t: (k: string) => k },
}));

vi.mock("../../../store/auth", () => ({
  useAuthStore: (selector: (s: { selectedPlant: null; user: { role: string } }) => unknown) =>
    selector({ selectedPlant: null, user: { role: "super_admin" } }),
}));

vi.mock("../../../components/ui/ModuleHelp", () => ({ ModuleHelp: () => null }));
vi.mock("../../../components/ui/AiSuggestionBanner", () => ({ AiSuggestionBanner: () => null }));

vi.mock("../../../api/endpoints/incidents", () => ({
  incidentsApi: {
    list: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    close: vi.fn(),
    delete: vi.fn(),
    timeline: vi.fn(),
    classificationMethod: vi.fn(),
    notifications: vi.fn(),
    classificationBreakdown: vi.fn(),
    classificationPreview: vi.fn(),
    classifySignificance: vi.fn(),
    markSent: vi.fn(),
    generateDocument: vi.fn(),
    listConfig: vi.fn(),
    createConfig: vi.fn(),
    updateConfig: vi.fn(),
  },
}));

vi.mock("../../../api/endpoints/plants", () => ({ plantsApi: { list: vi.fn() } }));

import { incidentsApi } from "../../../api/endpoints/incidents";
import { plantsApi } from "../../../api/endpoints/plants";

const mockList = vi.mocked(incidentsApi.list);
const mockPlants = vi.mocked(plantsApi.list);

// ── Helper ────────────────────────────────────────────────────────────────────

function makeIncident(overrides = {}) {
  return {
    id: "inc-1",
    title: "Ransomware linea produzione",
    description: "",
    plant: "p-1",
    severity: "alta",
    status: "aperto",
    nis2_notifiable: "da_valutare",
    detected_at: "2026-06-01T08:30:00Z",
    incident_category: "",
    incident_subcategory: "",
    affected_users_count: null,
    service_disruption_hours: null,
    financial_impact_eur: null,
    personal_data_involved: false,
    cross_border_impact: false,
    critical_infrastructure_impact: false,
    is_recurrent: false,
    is_significant: null,
    significance_override: null,
    ...overrides,
  };
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <IncidentsList />
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockList.mockResolvedValue({ results: [] } as never);
  mockPlants.mockResolvedValue([] as never);
  vi.mocked(incidentsApi.timeline).mockResolvedValue({ steps: [] } as never);
  vi.mocked(incidentsApi.classificationMethod).mockResolvedValue({
    taxonomy: { categories: [], subcategories: {} },
    nis2_method: { criteria: [], rule: "", decision_model: null, criteria_disclaimer: "", thresholds: null },
    scores: null,
  } as never);
  vi.mocked(incidentsApi.notifications).mockResolvedValue([] as never);
  vi.mocked(incidentsApi.classificationBreakdown).mockResolvedValue({} as never);
});

// ── Test ──────────────────────────────────────────────────────────────────────

describe("IncidentsList", () => {
  it("mostra gli incidenti in tabella", async () => {
    mockList.mockResolvedValue({ results: [makeIncident()] } as never);
    renderPage();
    expect(await screen.findByText("Ransomware linea produzione")).toBeInTheDocument();
  });

  it("mostra lo stato vuoto senza incidenti", async () => {
    renderPage();
    expect(await screen.findByText("incidents.empty")).toBeInTheDocument();
  });

  it("apre il modal di dettaglio al click sulla riga", async () => {
    mockList.mockResolvedValue({ results: [makeIncident()] } as never);
    renderPage();
    fireEvent.click(await screen.findByText("Ransomware linea produzione"));
    expect(await screen.findByText("incidents.detail_tabs.management")).toBeInTheDocument();
    expect(screen.getByText("incidents.detail_tabs.timeline")).toBeInTheDocument();
    expect(screen.getByText("incidents.management.save_btn")).toBeInTheDocument();
  });

  it("la vista configurazione NIS2 chiede di selezionare un plant", async () => {
    renderPage();
    fireEvent.click(await screen.findByText("incidents.views.nis2_config"));
    expect(await screen.findByText("incidents.nis2_config_select_plant")).toBeInTheDocument();
  });
});
