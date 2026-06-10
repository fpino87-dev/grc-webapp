import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AssetsPage } from "../AssetsPage";

// ── Mock ──────────────────────────────────────────────────────────────────────

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

vi.mock("../../../i18n", () => ({
  default: { language: "it", t: (k: string) => k },
}));

vi.mock("../../../api/endpoints/assets", () => ({
  assetsApi: {
    listIT: vi.fn(),
    listOT: vi.fn(),
    listSW: vi.fn(),
    deleteIT: vi.fn(),
    deleteOT: vi.fn(),
    deleteSW: vi.fn(),
  },
}));

vi.mock("../../../api/endpoints/plants", () => ({
  plantsApi: { list: vi.fn() },
}));

vi.mock("../../../api/endpoints/bia", () => ({
  biaApi: { list: vi.fn() },
}));

vi.mock("../../../api/endpoints/suppliers", () => ({
  suppliersApi: { list: vi.fn() },
}));

import { assetsApi } from "../../../api/endpoints/assets";
import { plantsApi } from "../../../api/endpoints/plants";
import { biaApi } from "../../../api/endpoints/bia";

const mockListIT = vi.mocked(assetsApi.listIT);
const mockListOT = vi.mocked(assetsApi.listOT);
const mockListSW = vi.mocked(assetsApi.listSW);
const mockPlants = vi.mocked(plantsApi.list);
const mockBia = vi.mocked(biaApi.list);

// ── Helper ────────────────────────────────────────────────────────────────────

function makeAssetIT(overrides = {}) {
  return {
    id: "it-1",
    name: "Server ERP",
    asset_type: "IT",
    criticality: 4,
    deployment_type: "on_prem",
    provider: "",
    service_name: "",
    fqdn: "erp.azienda.local",
    os: "Ubuntu 22.04",
    eol_date: null,
    data_classification: "internal",
    internet_exposed: false,
    processes: [],
    has_recent_change: false,
    needs_revaluation: false,
    last_change_ref: "",
    ...overrides,
  };
}

function makeAssetOT(overrides = {}) {
  return {
    id: "ot-1",
    name: "PLC Linea 1",
    asset_type: "OT",
    criticality: 5,
    category: "PLC",
    purdue_level: 1,
    patchable: false,
    vendor: "Siemens",
    processes: [],
    has_recent_change: false,
    needs_revaluation: false,
    last_change_ref: "",
    ...overrides,
  };
}

function makeAssetSW(overrides = {}) {
  return {
    id: "sw-1",
    name: "DocFlow",
    asset_type: "SW",
    criticality: 3,
    vendor: "Able Tech",
    version: "3.2.1",
    approval_status: "approvato",
    license_type: "commerciale",
    end_of_support: null,
    is_eos: false,
    days_to_eos: null,
    external_ref: "",
    processes: [],
    ...overrides,
  };
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <AssetsPage />
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockPlants.mockResolvedValue([] as never);
  mockBia.mockResolvedValue({ results: [] } as never);
  mockListIT.mockResolvedValue({ results: [] } as never);
  mockListOT.mockResolvedValue({ results: [] } as never);
  mockListSW.mockResolvedValue({ results: [] } as never);
});

// ── Test ──────────────────────────────────────────────────────────────────────

describe("AssetsPage", () => {
  it("mostra gli asset IT nella tabella del tab iniziale", async () => {
    mockListIT.mockResolvedValue({ results: [makeAssetIT()] } as never);
    renderPage();
    expect(await screen.findByText("Server ERP")).toBeInTheDocument();
    expect(screen.getByText("erp.azienda.local")).toBeInTheDocument();
  });

  it("mostra lo stato vuoto quando non ci sono asset IT", async () => {
    renderPage();
    expect(await screen.findByText("assets.empty_it")).toBeInTheDocument();
  });

  it("cambia tab e mostra gli asset OT", async () => {
    mockListOT.mockResolvedValue({ results: [makeAssetOT()] } as never);
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: "Asset OT" }));
    expect(await screen.findByText("PLC Linea 1")).toBeInTheDocument();
    expect(screen.getByText("Siemens")).toBeInTheDocument();
  });

  it("cambia tab e mostra gli asset SW", async () => {
    mockListSW.mockResolvedValue({ results: [makeAssetSW()] } as never);
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: "Software (ASL)" }));
    expect(await screen.findByText("DocFlow")).toBeInTheDocument();
    expect(screen.getByText("3.2.1")).toBeInTheDocument();
  });

  it("filtra gli asset IT con la ricerca per nome", async () => {
    mockListIT.mockResolvedValue({
      results: [makeAssetIT(), makeAssetIT({ id: "it-2", name: "NAS Backup", fqdn: "nas.azienda.local" })],
    } as never);
    renderPage();
    expect(await screen.findByText("Server ERP")).toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText("assets.search_placeholder"), { target: { value: "nas" } });
    expect(screen.getByText("NAS Backup")).toBeInTheDocument();
    expect(screen.queryByText("Server ERP")).not.toBeInTheDocument();
  });
});
