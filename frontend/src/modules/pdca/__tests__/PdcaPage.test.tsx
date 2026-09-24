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
vi.mock("../../../api/endpoints/plants", () => ({
  plantsApi: { list: vi.fn(() => Promise.resolve([{ id: "p1", code: "TA", name: "Plant TA" }])) },
}));

import { pdcaApi } from "../../../api/endpoints/pdca";
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

  it("il deep link ?cycle= mostra solo il ciclo collegato", async () => {
    renderPage("/pdca?cycle=c9");
    expect(await screen.findByText("pdca.link.single_cycle")).toBeInTheDocument();
    await vi.waitFor(() => expect(mockList).toHaveBeenLastCalledWith({ id: "c9" }));
  });
});

