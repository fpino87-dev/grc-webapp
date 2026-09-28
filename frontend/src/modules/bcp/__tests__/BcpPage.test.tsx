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
    addTestEvidences: vi.fn(),
  },
}));
vi.mock("../../../api/endpoints/bia", () => ({
  biaApi: { list: vi.fn(() => Promise.resolve({ results: [] })) },
}));
vi.mock("../../../api/endpoints/documents", () => ({
  documentsApi: {
    list: vi.fn(() => Promise.resolve({ results: [] })),
    evidences: vi.fn(() => Promise.resolve({ results: [
      { id: "e1", title: "Log ripristino ERP", plant: "p1", valid_until: null },
      { id: "e2", title: "Report DR di gruppo", plant: null, valid_until: "2027-01-31" },
    ] })),
    downloadEvidence: vi.fn(),
  },
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

describe("BcpPage — evidenze dei test", () => {
  it("un test senza evidenze si rafforza collegando un'evidenza esistente", async () => {
    const test = {
      id: "t1", plan: "b1", plan_title: "Piano stampaggio", plant: "p1", test_date: "2026-09-20",
      result: "superato", test_type: "drill", objectives: [], rto_achieved_hours: 6, rpo_achieved_hours: 2,
      participants_count: 4, objectives_met_pct: null, evidences_count: 0, evidence_items: [], notes: "",
    };
    vi.mocked(bcpApi.tests).mockResolvedValue([test] as never);
    vi.mocked(bcpApi.addTestEvidences).mockResolvedValue({
      ...test, evidences_count: 1,
      evidence_items: [{ id: "e2", title: "Report DR di gruppo", evidence_type: "report", valid_until: "2027-01-31", file_name: "dr.pdf" }],
    } as never);
    renderPage("/bcp?tab=tests");
    fireEvent.click(await screen.findByText("bcp.evidence.add_short"));
    expect(screen.getByText("bcp.evidence.missing")).toBeInTheDocument();
    fireEvent.click(await screen.findByText("Report DR di gruppo"));
    fireEvent.click(screen.getByText("bcp.evidence.attach"));
    expect(await screen.findByText("bcp.evidence.download")).toBeInTheDocument();
    expect(bcpApi.addTestEvidences).toHaveBeenCalledWith("t1", { evidenceIds: ["e2"], file: null });
  });
});

describe("BcpPage — nuovo piano", () => {
  it("si crea anche su un sito senza processi BIA, con avviso", async () => {
    vi.mocked(bcpApi.create).mockResolvedValue(plan() as never);
    renderPage("/bcp?tab=plans");
    fireEvent.click(await screen.findByText("bcp.actions.new_plan"));
    const create = screen.getByText("bcp.actions.create");
    expect(create).toBeDisabled();
    expect(screen.getByText("bcp.form.missing")).toBeInTheDocument();

    const [titleInput] = screen.getAllByRole("textbox");
    fireEvent.change(titleInput, { target: { value: "Piano DR" } });
    fireEvent.change(await screen.findByDisplayValue("bcp.form.select"), { target: { value: "p1" } });
    expect(await screen.findByText("bcp.form.processes_empty", { exact: false })).toBeInTheDocument();
    expect(screen.getByText("bcp.form.no_processes_warning")).toBeInTheDocument();
    expect(create).not.toBeDisabled();
    fireEvent.click(create);
    await vi.waitFor(() => expect(bcpApi.create).toHaveBeenCalled());
    expect(vi.mocked(bcpApi.create).mock.calls[0][0]).toMatchObject({ plant: "p1", title: "Piano DR", critical_processes: [] });
  });
});
