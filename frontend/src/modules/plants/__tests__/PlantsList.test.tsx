import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PlantsList } from "../PlantsList";

// ── Mock ──────────────────────────────────────────────────────────────────────

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

vi.mock("../../../i18n", () => ({
  default: { language: "it", t: (k: string) => k },
}));

vi.mock("../../../api/endpoints/plants", () => ({
  plantsApi: {
    list: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    remove: vi.fn(),
    uploadLogo: vi.fn(),
    plantFrameworks: vi.fn(),
    assignFramework: vi.fn(),
    toggleFramework: vi.fn(),
    removeFramework: vi.fn(),
  },
}));

vi.mock("../../../api/endpoints/controls", () => ({
  controlsApi: { frameworks: vi.fn() },
}));

vi.mock("../../../store/auth", () => ({
  useAuthStore: () => ({ setPlant: vi.fn() }),
}));

import { plantsApi } from "../../../api/endpoints/plants";

const mockList = vi.mocked(plantsApi.list);

function makePlant(overrides = {}) {
  return {
    id: "p-1",
    code: "TO01",
    name: "Stabilimento Torino",
    country: "IT",
    nis2_scope: "importante" as const,
    status: "attivo" as const,
    has_ot: true,
    timezone: "Europe/Rome",
    logo_url: "",
    ...overrides,
  };
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <PlantsList />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockList.mockResolvedValue([makePlant()]);
});

// ── Test ──────────────────────────────────────────────────────────────────────

describe("PlantsList — M01", () => {
  it("mostra la lista dei siti", async () => {
    renderPage();
    expect(await screen.findByText("Stabilimento Torino")).toBeInTheDocument();
    expect(screen.getByText("TO01")).toBeInTheDocument();
  });

  it("il form Nuovo sito ha la select del fuso orario con default Europe/Rome (F3)", async () => {
    renderPage();
    await screen.findByText("Stabilimento Torino");
    fireEvent.click(screen.getByText("plants.new.open"));

    expect(screen.getByText("plants.fields.timezone")).toBeInTheDocument();
    const select = screen.getByText("plants.fields.timezone")
      .parentElement!.querySelector("select")!;
    expect(select.value).toBe("Europe/Rome");
  });

  it("il form Modifica precompila il fuso orario del sito", async () => {
    mockList.mockResolvedValue([makePlant({ timezone: "Europe/Istanbul" })]);
    renderPage();
    await screen.findByText("Stabilimento Torino");
    fireEvent.click(screen.getByTitle("plants.actions.edit_title"));

    const select = screen.getByText("plants.fields.timezone")
      .parentElement!.querySelector("select")!;
    expect(select.value).toBe("Europe/Istanbul");
  });
});
