import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { GapAnalysisPage } from "../GapAnalysisPage";
import type { GapAnalysisResult } from "../../../api/endpoints/controls";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o?.count !== undefined ? `${k}:${o.count}` : k) }),
}));

vi.mock("../../../i18n", () => ({
  default: { language: "it", t: (k: string) => k },
}));

vi.mock("../../../api/endpoints/controls", () => ({
  controlsApi: { gapAnalysis: vi.fn() },
}));

vi.mock("../../../store/auth", () => ({
  useAuthStore: (sel: (s: { selectedPlant: { id: string; name: string } }) => unknown) =>
    sel({ selectedPlant: { id: "plant-1", name: "Sito IT" } }),
}));

import { controlsApi } from "../../../api/endpoints/controls";

const mockGap = vi.mocked(controlsApi.gapAnalysis);

const baseCounts = {
  coperto: 1, coperto_riuso: 1, parziale: 0, parziale_riuso: 0, scoperto: 1, escluso: 0,
};

function makeResult(overrides: Partial<GapAnalysisResult> = {}): GapAnalysisResult {
  return {
    target: "ACN_NIS2",
    profile: "importante",
    include_proto: null,
    frameworks: ["ACN_NIS2"],
    counts: baseCounts,
    coverage: { applicable: 3, direct_pct: 33.3, assisted_pct: 66.7 },
    coverage_by_domain: [],
    items: [
      {
        id: "i-1", external_id: "ACN-GV.PO-01", framework: "ACN_NIS2",
        title: "Policy di sicurezza", domain: "GV", domain_name: "GV",
        direct_status: null, state: "coperto_riuso",
        cross: [{ framework: "ISO27001", external_id: "A.5.1", title: "Politiche",
                  relationship: "equivalente", status: "compliant", via: null }],
        weight: 1,
        requirements: [{ punto: "1", applies_to: ["important", "essential"], text: "Req comune" }],
      },
      {
        id: "i-2", external_id: "ACN-PR.DS-01", framework: "ACN_NIS2",
        title: "Protezione dati", domain: "PR", domain_name: "PR",
        direct_status: "gap", state: "scoperto",
        cross: [{ framework: "ISO27001", external_id: "A.8.24", title: "Crittografia",
                  relationship: "correlato", status: "gap", via: null }],
        weight: 1,
      },
      {
        id: "i-3", external_id: "ACN-GV.RR-02", framework: "ACN_NIS2",
        title: "Ruoli", domain: "GV", domain_name: "GV",
        direct_status: "compliant", state: "coperto", cross: [], weight: 1,
      },
    ],
    ...overrides,
  };
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <GapAnalysisPage />
    </QueryClientProvider>,
  );
}

async function analyze(target = "ACN_NIS2") {
  fireEvent.change(screen.getAllByRole("combobox")[0], { target: { value: target } });
  fireEvent.click(screen.getByText("gap_analysis.actions.analyze"));
  await screen.findByText("gap_analysis.summary.direct");
}

beforeEach(() => {
  vi.clearAllMocks();
  mockGap.mockResolvedValue(makeResult());
});

describe("GapAnalysisPage — C12", () => {
  it("chiama l'API con target, plant e lingua e mostra le coperture", async () => {
    renderPage();
    await analyze();
    expect(mockGap).toHaveBeenCalledWith("ACN_NIS2", "plant-1", { profile: undefined, proto: undefined, lang: "it" });
    expect(screen.getByText("33.3%")).toBeInTheDocument();
    expect(screen.getByText("66.7%")).toBeInTheDocument();
  });

  it("mostra il cross-link anche quando la controparte NON è compliant", async () => {
    // richiesta utente: il legame resta visibile con lo stato della controparte
    renderPage();
    await analyze();
    expect(screen.getByText("A.8.24")).toBeInTheDocument(); // correlato, status gap
    expect(screen.getByText("A.5.1")).toBeInTheDocument();  // equivalente compliant
  });

  it("di default filtra i coperti (solo gap e riuso da validare)", async () => {
    renderPage();
    await analyze();
    expect(screen.queryByText("ACN-GV.RR-02")).not.toBeInTheDocument(); // coperto → nascosto
    expect(screen.getByText("ACN-GV.PO-01")).toBeInTheDocument();       // coperto_riuso → visibile
    expect(screen.getByText("ACN-PR.DS-01")).toBeInTheDocument();       // scoperto → visibile

    // disattivando il filtro compare anche il coperto
    fireEvent.click(screen.getByLabelText("gap_analysis.items.only_gaps"));
    expect(screen.getByText("ACN-GV.RR-02")).toBeInTheDocument();
  });

  it("per TISAX invia profilo AL e flag proto", async () => {
    mockGap.mockResolvedValue(makeResult({ target: "TISAX", profile: "AL3", frameworks: ["TISAX_L2", "TISAX_L3"] }));
    renderPage();
    fireEvent.change(screen.getAllByRole("combobox")[0], { target: { value: "TISAX" } });
    fireEvent.click(screen.getByLabelText("gap_analysis.include_proto"));
    fireEvent.click(screen.getByText("gap_analysis.actions.analyze"));
    await screen.findByText("gap_analysis.summary.direct");
    expect(mockGap).toHaveBeenCalledWith("TISAX", "plant-1", { profile: "AL3", proto: true, lang: "it" });
  });
});
