import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { PdcaPage } from "../PdcaPage";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));
vi.mock("../../../i18n", () => ({ default: { language: "it", t: (k: string) => k } }));
vi.mock("../../../api/client", () => ({
  apiClient: { get: vi.fn(() => Promise.resolve({ data: { results: [] } })), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));
vi.mock("../../../api/endpoints/pdca", () => ({
  pdcaApi: {
    list: vi.fn(), create: vi.fn(), update: vi.fn(), remove: vi.fn(), archivia: vi.fn(), capabilities: vi.fn(),
    linkFinding: vi.fn(), unlinkFinding: vi.fn(),
  },
}));
vi.mock("../../../api/endpoints/auditPrep", () => ({
  auditPrepApi: { list: vi.fn(), findings: vi.fn() },
}));
vi.mock("../../../api/endpoints/plants", () => ({
  plantsApi: { list: vi.fn(() => Promise.resolve([{ id: "p1", code: "TA", name: "Plant TA" }])) },
}));

import { pdcaApi } from "../../../api/endpoints/pdca";
import { auditPrepApi } from "../../../api/endpoints/auditPrep";
import { apiClient } from "../../../api/client";

const mockList = vi.mocked(pdcaApi.list);
const mockCaps = vi.mocked(pdcaApi.capabilities);
const mockCreate = vi.mocked(pdcaApi.create);

function cycle(overrides = {}) {
  return {
    id: "c1", plant: "p1", plant_code: "TA", plant_name: "Plant TA", can_manage: true,
    title: "Ciclo del sito", trigger_type: "manual", scope_type: "plant", fase_corrente: "plan",
    phases: [], created_at: "2026-09-01T10:00:00Z",
    ...overrides,
  };
}

function renderPage(url = "/pdca") {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[url]}><PdcaPage /></MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockList.mockResolvedValue({ results: [] } as never);
  mockCaps.mockResolvedValue({ can_manage_org: true } as never);
  mockCreate.mockResolvedValue(cycle() as never);
});

describe("PdcaPage — cicli di organizzazione", () => {
  it("il ciclo di organizzazione è etichettato e in sola lettura per chi non lo gestisce", async () => {
    mockList.mockResolvedValue({
      results: [
        cycle(),
        cycle({ id: "c2", plant: null, plant_code: null, plant_name: null, can_manage: false,
                title: "Ciclo di organizzazione", scope_type: "org" }),
      ],
    } as never);
    renderPage();
    const orgRow = (await screen.findByText("Ciclo di organizzazione")).closest("tr")!;
    expect(within(orgRow).getAllByText("pdca.scope.org").length).toBeGreaterThan(0);
    expect(within(orgRow).getByText("pdca.read_only_org")).toBeInTheDocument();
    expect(within(orgRow).queryByText("pdca.advance.btn_do")).not.toBeInTheDocument();
    const siteRow = screen.getByText("Ciclo del sito").closest("tr")!;
    expect(within(siteRow).getByText("pdca.advance.btn_do")).toBeInTheDocument();
  });

  it("chi ha scope org crea un ciclo di organizzazione senza sito", async () => {
    renderPage();
    fireEvent.click(await screen.findByText("pdca.new_btn"));
    const site = document.querySelector('select[name="plant"]') as HTMLSelectElement;
    const orgOption = await screen.findByText("pdca.form.plant_org_option");
    await vi.waitFor(() => expect((orgOption as HTMLOptionElement).disabled).toBe(false));
    fireEvent.change(site, { target: { value: "__org__" } });
    expect((document.querySelector('select[name="scope_type"]') as HTMLSelectElement).disabled).toBe(true);
    fireEvent.change(document.querySelector('input[name="title"]')!, { target: { value: "Awareness phishing" } });
    fireEvent.click(screen.getByText("pdca.form.create_btn"));
    await vi.waitFor(() => expect(mockCreate).toHaveBeenCalled());
    expect(mockCreate.mock.calls[0][0]).toMatchObject({ plant: null, scope_type: "org", title: "Awareness phishing" });
  });

  it("senza scope org l'opzione Organizzazione è disabilitata", async () => {
    mockCaps.mockResolvedValue({ can_manage_org: false } as never);
    renderPage();
    fireEvent.click(await screen.findByText("pdca.new_btn"));
    expect(await screen.findByText("pdca.form.plant_org_denied")).toBeInTheDocument();
    expect((screen.getByText("pdca.form.plant_org_option") as HTMLOptionElement).disabled).toBe(true);
  });

  it("il filtro per sito include i cicli di organizzazione", async () => {
    renderPage();
    await screen.findByText("pdca.new_btn");
    const selects = screen.getAllByRole("combobox");
    const plantFilter = selects[1];
    await screen.findAllByText("TA — Plant TA");
    fireEvent.change(plantFilter, { target: { value: "p1" } });
    await vi.waitFor(() => expect(mockList).toHaveBeenLastCalledWith({ site: "p1" }));
    fireEvent.change(plantFilter, { target: { value: "__org__" } });
    await vi.waitFor(() => expect(mockList).toHaveBeenLastCalledWith({ org: "true" }));
  });
});

describe("PdcaPage — evidenza DO → CHECK", () => {
  it("si può caricare il file direttamente invece di sceglierne uno esistente", async () => {
    mockList.mockResolvedValue({ results: [cycle({ fase_corrente: "do" })] } as never);
    const post = vi.mocked(apiClient.post);
    post.mockResolvedValue({ data: { ok: true, fase_corrente: "check" } } as never);
    renderPage();
    fireEvent.click(await screen.findByText("pdca.advance.btn_check"));
    fireEvent.click(screen.getByLabelText("pdca.advance.evidence_mode_upload"));
    const file = new File(["%PDF-1.4"], "verbale.pdf", { type: "application/pdf" });
    fireEvent.change(screen.getByLabelText("pdca.advance.evidence_file_label"), { target: { files: [file] } });
    fireEvent.change(screen.getByPlaceholderText("pdca.advance.evidence_title_placeholder"),
                     { target: { value: "Verbale formazione" } });
    fireEvent.click(screen.getByText("pdca.advance.confirm"));
    await vi.waitFor(() => expect(post).toHaveBeenCalled());
    const [url, body] = post.mock.calls[0];
    expect(url).toBe("/pdca/cycles/c1/advance/");
    expect(body).toBeInstanceOf(FormData);
    expect((body as FormData).get("file")).toBe(file);
    expect((body as FormData).get("evidence_title")).toBe("Verbale formazione");
  });
});

describe("PdcaPage — collegamento ai finding di audit", () => {
  it("mostra i finding collegati con audit e committente", async () => {
    mockList.mockResolvedValue({ results: [cycle({ findings: [{
      id: "f1", title: "Classificazione", finding_type: "observation", status: "open",
      audit_prep: "a1", audit_title: "Audit OEM", audit_type: "seconda_parte", requesting_party: "OEM Alfa",
    }] })] } as never);
    renderPage();
    expect(await screen.findByText(/\[OBSERVATION\] Classificazione/)).toBeInTheDocument();
    expect(screen.getByText(/Audit OEM/)).toBeInTheDocument();
    expect(screen.getByText(/OEM Alfa/)).toBeInTheDocument();
  });

  it("il rilievo comune sta su una riga con un chip per sito, senza ripetere il titolo", async () => {
    const common = { title: "OSS.05 Offboarding", finding_type: "observation", audit_type: "interno",
      requesting_party: "", common_key: "k1", group_title: "TISAX AL2 PreCert" };
    mockList.mockResolvedValue({ results: [cycle({
      plant: null, plant_code: null, plant_name: null, scope_type: "org", trigger_type: "finding_observation",
      title: "[OBSERVATION] OSS.05 Offboarding", findings: [
        { ...common, id: "f1", status: "open", audit_prep: "a1", audit_title: "TISAX AL2 PreCert — PL", plant_code: "PL-HP-01" },
        { ...common, id: "f2", status: "closed", audit_prep: "a2", audit_title: "TISAX AL2 PreCert — TN", plant_code: "TN-TUN-01" },
      ] })] } as never);
    renderPage();
    expect(await screen.findByText("PL-HP-01")).toBeInTheDocument();
    expect(screen.getByText("TN-TUN-01")).toBeInTheDocument();
    expect(screen.getAllByText(/TISAX AL2 PreCert/)).toHaveLength(1);
    expect(screen.getAllByText(/OSS\.05 Offboarding/)).toHaveLength(1);
    // origine "Audit" come i PDCA creati a mano (il tipo è nel titolo)
    expect(screen.getByText("pdca.trigger.audit")).toBeInTheDocument();
    expect(screen.queryByText("pdca.trigger.finding_observation")).not.toBeInTheDocument();
    // il collegamento ai finding c'è anche sui cicli di organizzazione
    fireEvent.click(screen.getByText(/pdca\.link\.btn$/));
    expect(await screen.findByText("pdca.link.org_rule_hint")).toBeInTheDocument();
    // "Organizzazione" solo nella colonna Sito (la colonna Ambito non c'è più)
    expect(screen.getAllByText("pdca.scope.org")).toHaveLength(1);
    expect(screen.queryByText("pdca.table.scope")).not.toBeInTheDocument();
  });

  it("il riferimento testuale si nasconde se c'è il finding collegato", async () => {
    const linked = { id: "f1", title: "SdM_09 zone", finding_type: "opportunity", status: "open", audit_prep: "a1",
      audit_title: "Audit TISAX AL3", plant_code: "IT-CH-01", common_key: null, group_title: null,
      audit_type: "interno", requesting_party: "" };
    mockList.mockResolvedValue({ results: [
      cycle({ id: "c1", title: "Sospensione badge", riferimento_finding: "SdM_09", findings: [linked] }),
      cycle({ id: "c2", title: "Vecchio", riferimento_finding: "NC-OLD-1", findings: [] }),
    ] } as never);
    renderPage();
    expect(await screen.findByText("NC-OLD-1")).toBeInTheDocument();
    expect(screen.queryByText("SdM_09")).not.toBeInTheDocument();
  });

  it("il deep link ?cycle= mostra solo il ciclo collegato", async () => {
    renderPage("/pdca?cycle=c9");
    expect(await screen.findByText("pdca.link.single_cycle")).toBeInTheDocument();
    await vi.waitFor(() => expect(mockList).toHaveBeenLastCalledWith({ id: "c9" }));
  });
});

describe("PdcaPage — PDCA chiuso collegato a un finding che ha già il PDCA automatico", () => {
  it("il finding compare con il suo PDCA e la sostituzione chiede il motivo", async () => {
    mockList.mockResolvedValue({ results: [cycle({ id: "c7", fase_corrente: "chiuso", title: "PDCA manuale", findings: [] })] } as never);
    vi.mocked(auditPrepApi.list).mockResolvedValue({ results: [
      { id: "a1", title: "Audit OEM", status: "in_corso", plant: "p1", audit_date: "2026-09-10" },
    ] } as never);
    vi.mocked(auditPrepApi.findings).mockResolvedValue([
      { id: "f1", title: "NC dal rapporto", finding_type: "minor_nc", status: "open", pdca_cycle: "auto1", pdca_title: "[MINOR_NC] NC dal rapporto" },
    ] as never);
    vi.mocked(pdcaApi.linkFinding).mockResolvedValue({} as never);
    renderPage();
    fireEvent.click(await screen.findByText(/pdca\.link\.btn$/));
    const selects = screen.getAllByRole("combobox");
    fireEvent.change(await within(document.body).findByDisplayValue("pdca.link.audit_select"), { target: { value: "a1" } });
    const findingOption = await screen.findByText(/NC dal rapporto.*pdca\.link\.has_pdca/);
    fireEvent.change(findingOption.closest("select")!, { target: { value: "f1" } });
    expect(screen.getByText("pdca.link.replace_hint")).toBeInTheDocument();
    const confirm = screen.getByText("pdca.link.link_btn");
    expect(confirm).toBeDisabled();
    fireEvent.change(screen.getByPlaceholderText("pdca.link.replace_reason"), { target: { value: "Azione già svolta nel PDCA manuale" } });
    fireEvent.click(confirm);
    await vi.waitFor(() => expect(pdcaApi.linkFinding).toHaveBeenCalledWith("c7", "f1", "Azione già svolta nel PDCA manuale"));
    expect(selects.length).toBeGreaterThan(0);
  });
});

describe("PdcaPage — filtro per stato", () => {
  it("filtra per cicli in corso o per fase", async () => {
    renderPage();
    const statusSelect = (await screen.findByText("pdca.filters.all_statuses")).closest("select")!;
    fireEvent.change(statusSelect, { target: { value: "open" } });
    await vi.waitFor(() => expect(mockList).toHaveBeenLastCalledWith({ open: "true" }));
    fireEvent.change(statusSelect, { target: { value: "chiuso" } });
    await vi.waitFor(() => expect(mockList).toHaveBeenLastCalledWith({ fase_corrente: "chiuso" }));
  });
});


describe("PdcaPage — filtro per origine", () => {
  it("propone le categorie e passa la categoria al backend", async () => {
    renderPage();
    const triggerSelect = (await screen.findByText("pdca.filters.all_triggers")).closest("select")!;
    for (const code of ["audit", "incident", "bcp", "checklist", "controls"]) {
      expect(screen.getByText(`pdca.trigger_filter.${code}`)).toBeInTheDocument();
    }
    fireEvent.change(triggerSelect, { target: { value: "bcp" } });
    await vi.waitFor(() => expect(mockList).toHaveBeenLastCalledWith({ trigger_type: "bcp" }));
  });
});

describe("PdcaPage — ricerca ed esclusione organizzazione", () => {
  it("la ricerca per testo passa search al backend", async () => {
    renderPage();
    fireEvent.change(await screen.findByLabelText("pdca.filters.search_placeholder"), { target: { value: "badge" } });
    await vi.waitFor(() => expect(mockList).toHaveBeenLastCalledWith({ search: "badge" }));
  });

  it("con un sito scelto si possono escludere i cicli di organizzazione", async () => {
    renderPage();
    const plantSelect = (await screen.findByText("pdca.filters.all_plants")).closest("select")!;
    expect(screen.queryByLabelText("pdca.filters.exclude_org")).not.toBeInTheDocument();
    await screen.findByText("TA — Plant TA");
    fireEvent.change(plantSelect, { target: { value: "p1" } });
    await vi.waitFor(() => expect(mockList).toHaveBeenLastCalledWith({ site: "p1" }));
    fireEvent.click(await screen.findByLabelText("pdca.filters.exclude_org"));
    await vi.waitFor(() => expect(mockList).toHaveBeenLastCalledWith({ plant: "p1" }));
  });
});

describe("PdcaPage — responsabile e data prevista", () => {
  it("in elenco mostra responsabile e ritardo", async () => {
    mockList.mockResolvedValue({ results: [cycle({ action_owner: "HR Manager — TA", target_date: "2026-01-10", is_overdue: true })] } as never);
    renderPage();
    expect(await screen.findByText(/HR Manager — TA/)).toBeInTheDocument();
    expect(screen.getByText(/pdca\.owner\.overdue/)).toBeInTheDocument();
  });

  it("si impostano dalla modifica del ciclo", async () => {
    mockList.mockResolvedValue({ results: [cycle()] } as never);
    vi.mocked(pdcaApi.update).mockResolvedValue({} as never);
    renderPage();
    fireEvent.click(await screen.findByTitle("pdca.form.edit_tooltip"));
    fireEvent.change(screen.getByLabelText("pdca.owner.label"), { target: { value: "IT Manager" } });
    fireEvent.change(screen.getByLabelText("pdca.owner.target_date"), { target: { value: "2026-12-31" } });
    fireEvent.click(screen.getByText("pdca.form.save_btn"));
    await vi.waitFor(() => expect(pdcaApi.update).toHaveBeenCalledWith("c1",
      expect.objectContaining({ action_owner: "IT Manager", target_date: "2026-12-31" })));
  });
});

describe("PdcaPage — archiviazione con finding collegati", () => {
  it("avvisa dei rilievi non perseguiti e delle NC che restano aperte, prova facoltativa", async () => {
    const base = { audit_prep: "a1", audit_title: "Audit", plant_code: "TA", common_key: null, group_title: null,
      audit_type: "interno", requesting_party: "" };
    mockList.mockResolvedValue({ results: [cycle({ findings: [
      { ...base, id: "f1", title: "Opp", finding_type: "opportunity", status: "open" },
      { ...base, id: "f2", title: "NC", finding_type: "minor_nc", status: "open" },
    ] })] } as never);
    vi.mocked(pdcaApi.archivia).mockResolvedValue({} as never);
    renderPage();
    fireEvent.click(await screen.findByTitle("pdca.archive.tooltip"));
    expect(screen.getByText("pdca.archive.not_pursued_hint")).toBeInTheDocument();
    expect(screen.getByText("pdca.archive.nc_open_hint")).toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText("pdca.archive.reason_placeholder"),
      { target: { value: "Costo sproporzionato rispetto al beneficio" } });
    fireEvent.click(screen.getByText("pdca.archive.confirm_btn"));
    await vi.waitFor(() => expect(pdcaApi.archivia).toHaveBeenCalledWith("c1",
      "Costo sproporzionato rispetto al beneficio", { evidence_id: undefined, file: null }));
  });
});
