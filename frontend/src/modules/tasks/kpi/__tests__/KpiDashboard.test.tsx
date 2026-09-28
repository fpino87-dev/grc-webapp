import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { KpiDashboard } from "../KpiDashboard";

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }));
vi.mock("../../../../i18n", () => ({ default: { language: "it", t: (k: string) => k } }));
vi.mock("recharts", () => ({
  ResponsiveContainer: () => null, LineChart: () => null, Line: () => null, XAxis: () => null,
  YAxis: () => null, Tooltip: () => null, ReferenceLine: () => null, CartesianGrid: () => null,
}));
vi.mock("../../../../api/endpoints/kpi", () => ({
  kpiApi: {
    getKpiDefinitions: vi.fn(), getKpiTrend: vi.fn(), getKpiBySite: vi.fn(), computeNow: vi.fn(),
  },
}));
vi.mock("../../../../api/endpoints/plants", () => ({
  plantsApi: { list: vi.fn(() => Promise.resolve([{ id: "p1", code: "PL", name: "Plant PL" }])) },
}));

import { kpiApi } from "../../../../api/endpoints/kpi";

function kpi(overrides = {}) {
  return {
    id: "k1", kpi_code: "dr_test_age_days", name: "Anzianità ultimo test DR", unit: "gg",
    threshold_warning: 200, threshold_critical: 365, threshold_direction: "below",
    source: "internal", is_active: true, plant: "p1", last_status: "ok", last_value: 186,
    last_sites: null, last_note: "",
    ...overrides,
  };
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter><KpiDashboard /></MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(kpiApi.getKpiTrend).mockResolvedValue({ results: [] } as never);
  vi.mocked(kpiApi.getKpiBySite).mockResolvedValue({ results: [] } as never);
});

describe("KpiDashboard — dettaglio in «Tutti i siti»", () => {
  it("una definizione di sito legge l'andamento del suo sito", async () => {
    vi.mocked(kpiApi.getKpiDefinitions).mockResolvedValue({ results: [kpi()], count: 1 } as never);
    renderPage();
    fireEvent.click(await screen.findByText("Anzianità ultimo test DR"));
    await vi.waitFor(() => expect(kpiApi.getKpiTrend).toHaveBeenCalledWith("dr_test_age_days", "p1", 12));
    expect(kpiApi.getKpiBySite).not.toHaveBeenCalled();
  });

  it("una definizione globale legge il valore di organizzazione e il dettaglio per sito", async () => {
    vi.mocked(kpiApi.getKpiDefinitions).mockResolvedValue({
      results: [kpi({ id: "k2", kpi_code: "osint_security_score", name: "Postura esterna", plant: null })], count: 1,
    } as never);
    renderPage();
    fireEvent.click(await screen.findByText("Postura esterna"));
    await vi.waitFor(() => expect(kpiApi.getKpiTrend).toHaveBeenCalledWith("osint_security_score", undefined, 12));
    await vi.waitFor(() => expect(kpiApi.getKpiBySite).toHaveBeenCalledWith("osint_security_score"));
  });
});
