import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { BcpPage } from "../BcpPage";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));
vi.mock("../../../i18n", () => ({ default: { language: "it", t: (k: string) => k } }));
vi.mock("../../../api/endpoints/bcp", () => ({
  bcpApi: {
    list: vi.fn(), coverage: vi.fn(), tests: vi.fn(), approve: vi.fn(), archive: vi.fn(),
    delete: vi.fn(), deleteTest: vi.fn(), create: vi.fn(), update: vi.fn(), recordTest: vi.fn(),
  },
}));
vi.mock("../../../api/endpoints/bia", () => ({
  biaApi: { list: vi.fn(() => Promise.resolve({ results: [] })) },
}));
vi.mock("../../../api/endpoints/documents", () => ({
  documentsApi: { list: vi.fn(() => Promise.resolve({ results: [] })) },
}));
vi.mock("../../../api/endpoints/plants", () => ({
  plantsApi: { list: vi.fn(() => Promise.resolve([{ id: "p1", code: "TA", name: "Plant TA" }])) },
}));

import { bcpApi } from "../../../api/endpoints/bcp";

function renderPage(url = "/bcp") {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[url]}><BcpPage /></MemoryRouter>
    </QueryClientProvider>,
  );
}

function plan(overrides = {}) {
  return {
    id: "b1", plant: "p1", title: "Piano stampaggio", version: "1.0", status: "approvato",
    rto_hours: 4, rpo_hours: 2, last_test_date: null, next_test_date: null, owner: null,
    critical_processes: ["c1"], process_names: ["Stampaggio"], document: null,
    test_state: "never", last_test_result: null, can_approve: false,
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(bcpApi.list).mockResolvedValue({ results: [], count: 0 } as never);
  vi.mocked(bcpApi.tests).mockResolvedValue([] as never);
  vi.mocked(bcpApi.coverage).mockResolvedValue([] as never);
});

describe("BcpPage", () => {
  it("copertura: mostra i tre stati e il piano con test mai eseguito", async () => {
    vi.mocked(bcpApi.coverage).mockResolvedValue([
      {
        process_id: "c1", process_name: "Stampaggio", plant: "p1", criticality: 5,
        rto_target_hours: 8, rpo_target_hours: 4, mtpd_hours: 24, coverage: "test_expired",
        plans: [{
          id: "b1", title: "Piano stampaggio", status: "approvato", test_state: "never",
          last_test_date: null, next_test_date: null, last_test_result: null,
          rto_declared: 4, rto_demonstrated: 4, rto_measured: false,
        }],
      },
      {
        process_id: "c2", process_name: "Verniciatura", plant: "p1", criticality: 4,
        rto_target_hours: null, rpo_target_hours: null, mtpd_hours: null, coverage: "missing", plans: [],
      },
    ] as never);
    renderPage();
    expect(await screen.findByText("Stampaggio")).toBeInTheDocument();
    expect(screen.getAllByText("bcp.coverage.state.test_expired").length).toBeGreaterThan(0);
    expect(screen.getByText("bcp.test_state.never")).toBeInTheDocument();
    // processo senza piano: si crea il piano da qui, con il processo già scelto
    fireEvent.click(screen.getByText("bcp.coverage.create_plan"));
    expect(await screen.findByText("bcp.form.new_title")).toBeInTheDocument();
  });

  it("piani: test registrabile su un piano approvato, Approva solo se consentito", async () => {
    vi.mocked(bcpApi.list).mockResolvedValue({
      results: [plan(), plan({ id: "b2", title: "Bozza logistica", status: "bozza", can_approve: true })],
      count: 2,
    } as never);
    renderPage("/bcp?tab=plans");
    expect(await screen.findByText("Piano stampaggio")).toBeInTheDocument();
    expect(screen.getAllByText("bcp.actions.add_test")).toHaveLength(2);
    expect(screen.getAllByText("bcp.actions.approve")).toHaveLength(1);
    expect(screen.getAllByText("bcp.plans.no_document")).toHaveLength(2);
  });

  it("piani archiviati nascosti finché non si chiede di vederli", async () => {
    vi.mocked(bcpApi.list).mockResolvedValue({
      results: [plan(), plan({ id: "b3", title: "Vecchio piano", status: "archiviato" })],
      count: 2,
    } as never);
    renderPage("/bcp?tab=plans");
    expect(await screen.findByText("Piano stampaggio")).toBeInTheDocument();
    expect(screen.queryByText("Vecchio piano")).not.toBeInTheDocument();
    fireEvent.click(screen.getByText("bcp.plans.show_archived"));
    expect(screen.getByText("Vecchio piano")).toBeInTheDocument();
  });
});
