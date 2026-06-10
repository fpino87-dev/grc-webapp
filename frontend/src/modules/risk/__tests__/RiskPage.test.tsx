import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { RiskPage } from "../RiskPage";

// ── Mock ──────────────────────────────────────────────────────────────────────

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (k: string) => k, i18n: { language: "it" } }),
}));

vi.mock("../../../i18n", () => ({
  default: { language: "it", t: (k: string) => k },
}));

vi.mock("../../../store/auth", () => ({
  useAuthStore: (selector: (s: { selectedPlant: null; user: null }) => unknown) =>
    selector({ selectedPlant: null, user: null }),
}));

vi.mock("../../../lib/scrollAndHighlight", () => ({ scrollAndHighlight: vi.fn() }));
vi.mock("../../../components/ui/AssistenteValutazione", () => ({ AssistenteValutazione: () => null }));
vi.mock("../../../components/ui/ModuleHelp", () => ({ ModuleHelp: () => null }));
vi.mock("../RiskContinuityWizard", () => ({ RiskContinuityWizard: () => null }));
vi.mock("../RiskIntegratedRegisters", () => ({ RiskIntegratedRegisters: () => null }));

vi.mock("../../../api/client", () => ({
  apiClient: { get: vi.fn(() => Promise.reject(new Error("not mocked"))) },
}));

vi.mock("../../../api/endpoints/risk", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../../api/endpoints/risk")>();
  return {
    ...actual,
    riskApi: {
      list: vi.fn(),
      context: vi.fn(),
      mitigationPlans: vi.fn(),
      suggestResidual: vi.fn(),
      complete: vi.fn(),
      delete: vi.fn(),
      reopen: vi.fn(),
      exportExcel: vi.fn(),
      acceptRisk: vi.fn(),
      renewAcceptance: vi.fn(),
      resetAcceptance: vi.fn(),
      createPlan: vi.fn(),
      updatePlan: vi.fn(),
      deletePlan: vi.fn(),
      completePlan: vi.fn(),
      uncompletePlan: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      createAppetite: vi.fn(),
      updateAppetite: vi.fn(),
    },
  };
});

vi.mock("../../../api/endpoints/plants", () => ({ plantsApi: { list: vi.fn() } }));
vi.mock("../../../api/endpoints/bia", () => ({ biaApi: { list: vi.fn() } }));
vi.mock("../../../api/endpoints/users", () => ({ usersApi: { list: vi.fn() } }));
vi.mock("../../../api/endpoints/bcp", () => ({ bcpApi: { list: vi.fn() } }));

import { riskApi } from "../../../api/endpoints/risk";
import { plantsApi } from "../../../api/endpoints/plants";

const mockList = vi.mocked(riskApi.list);
const mockContext = vi.mocked(riskApi.context);
const mockPlans = vi.mocked(riskApi.mitigationPlans);
const mockPlants = vi.mocked(plantsApi.list);

// ── Helper ────────────────────────────────────────────────────────────────────

function makeAssessment(overrides = {}) {
  return {
    id: "ra-1",
    name: "Ransomware su ERP",
    assessment_type: "IT",
    plant: "p-1",
    status: "completato",
    treatment: "mitigare",
    threat_category: null,
    owner: null,
    owner_name: null,
    critical_process: null,
    critical_process_name: null,
    inherent_probability: 4,
    inherent_impact: 4,
    inherent_score: 16,
    inherent_risk_level: "rosso",
    probability: 2,
    impact: 3,
    score: 6,
    weighted_score: null,
    risk_level: "verde",
    ale_calcolato: null,
    ale_annuo: null,
    plan_due_date: null,
    mitigation_plans_count: 0,
    mitigation_plans_completed: 0,
    last_plan_completed_at: null,
    needs_revaluation: false,
    risk_accepted_formally: false,
    risk_acceptance_expiry: null,
    risk_acceptance_note: "",
    risk_accepted_at: null,
    accepted_by_name: null,
    nis2_art21_category: "",
    nis2_relevance: "",
    impacted_systems: "",
    cause: "",
    consequence: "",
    ...overrides,
  };
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <RiskPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockPlants.mockResolvedValue([] as never);
  mockList.mockResolvedValue({ results: [] } as never);
  mockContext.mockResolvedValue({ bcp_plans: [] } as never);
  mockPlans.mockResolvedValue([] as never);
});

// ── Test ──────────────────────────────────────────────────────────────────────

describe("RiskPage", () => {
  it("mostra i risk assessment in tabella", async () => {
    mockList.mockResolvedValue({ results: [makeAssessment()] } as never);
    renderPage();
    expect(await screen.findByText("Ransomware su ERP")).toBeInTheDocument();
    expect(screen.getByText("2×3")).toBeInTheDocument();
  });

  it("mostra lo stato vuoto quando non ci sono assessment", async () => {
    renderPage();
    expect(await screen.findByText("risk.empty")).toBeInTheDocument();
  });

  it("espande la riga e mostra il pannello dei piani di mitigazione", async () => {
    mockList.mockResolvedValue({ results: [makeAssessment()] } as never);
    renderPage();
    fireEvent.click(await screen.findByText("Ransomware su ERP"));
    expect(await screen.findByText("+ risk.add_plan")).toBeInTheDocument();
    expect(screen.getByText("risk.no_mitigation_plans")).toBeInTheDocument();
  });

  it("il filtro completezza nasconde i rischi completi", async () => {
    const completo = makeAssessment({
      id: "ra-ok",
      name: "Rischio completo",
      score: 4,
      risk_level: "verde",
      treatment: "accettare",
    });
    const bozza = makeAssessment({ id: "ra-draft", name: "Rischio in bozza", status: "bozza" });
    mockList.mockResolvedValue({ results: [completo, bozza] } as never);
    renderPage();
    expect(await screen.findByText("Rischio completo")).toBeInTheDocument();

    const filterSelects = screen.getAllByRole("combobox");
    fireEvent.change(filterSelects[filterSelects.length - 1], { target: { value: "incomplete" } });

    expect(screen.getByText("Rischio in bozza")).toBeInTheDocument();
    expect(screen.queryByText("Rischio completo")).not.toBeInTheDocument();
  });
});
