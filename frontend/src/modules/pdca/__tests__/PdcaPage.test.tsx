import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PdcaPage } from "../PdcaPage";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));
vi.mock("../../../i18n", () => ({ default: { language: "it", t: (k: string) => k } }));
vi.mock("../../../api/client", () => ({
  apiClient: { get: vi.fn(() => Promise.resolve({ data: { results: [] } })), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));
vi.mock("../../../api/endpoints/pdca", () => ({
  pdcaApi: { list: vi.fn(), create: vi.fn(), update: vi.fn(), remove: vi.fn(), archivia: vi.fn(), capabilities: vi.fn() },
}));
vi.mock("../../../api/endpoints/plants", () => ({
  plantsApi: { list: vi.fn(() => Promise.resolve([{ id: "p1", code: "TA", name: "Plant TA" }])) },
}));

import { pdcaApi } from "../../../api/endpoints/pdca";

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

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}><PdcaPage /></QueryClientProvider>);
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
