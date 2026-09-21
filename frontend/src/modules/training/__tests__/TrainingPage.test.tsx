import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TrainingPage } from "../TrainingPage";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (k: string, o?: Record<string, unknown>) => (o ? `${k} ${JSON.stringify(o)}` : k),
    i18n: { language: "it" },
  }),
}));

vi.mock("../../../i18n", () => ({ default: { language: "it", t: (k: string) => k } }));

const PLANT = { id: "p1", code: "TA", name: "Plant A" };
vi.mock("../../../store/auth", () => ({
  useAuthStore: (selector: (s: { selectedPlant: typeof PLANT }) => unknown) => selector({ selectedPlant: PLANT }),
}));

vi.mock("../../../api/endpoints/documents", () => ({
  documentsApi: { searchDocuments: vi.fn(), downloadEvidence: vi.fn() },
}));

vi.mock("../../../api/endpoints/training", () => ({
  trainingApi: {
    capabilities: vi.fn(),
    courses: vi.fn(),
    controlOptions: vi.fn(),
    audiences: vi.fn(),
    plans: vi.fn(),
    planStatus: vi.fn(),
    planItems: vi.fn(),
    sessions: vi.fn(),
    createPlan: vi.fn(),
    registerSession: vi.fn(),
    deleteSession: vi.fn(),
  },
}));

import { trainingApi } from "../../../api/endpoints/training";
const api = vi.mocked(trainingApi);

const course = {
  id: "c1", title: "Awareness base", description: "", source: "interno" as const, status: "attivo" as const,
  kind: "corso" as const, audience_kind: "generale" as const, mandatory: true, duration_minutes: 60,
  validity_months: 12, controls: ["k1"],
  controls_detail: [{ id: "k1", external_id: "A.6.3", framework_code: "ISO27001", title: "Awareness" }],
};

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}><TrainingPage /></QueryClientProvider>);
}

beforeEach(() => {
  vi.clearAllMocks();
  api.courses.mockResolvedValue([course]);
  api.audiences.mockResolvedValue([
    { id: "a1", plant: "p1", plant_code: "TA", name: "Produzione", headcount: 200,
      headcount_updated_at: "2020-01-01", notes: "" },
  ]);
  api.plans.mockResolvedValue([
    { id: "pl1", plant: "p1", plant_code: "TA", year: new Date().getFullYear(), document: null,
      document_title: null, document_status: null, notes: "" },
  ]);
  api.planStatus.mockResolvedValue({
    plan_id: "pl1", year: 2026, counts: { fatto: 0, in_ritardo: 1, in_scadenza: 0, pianificato: 0 },
    items: [{ item_id: "i1", course_id: "c1", course_title: "Awareness base", due_date: "2026-03-31",
              state: "in_ritardo", sessions: 0, target_count: 200, trained_count: 0, coverage_pct: 0 }],
  });
  api.sessions.mockResolvedValue([
    { id: "s1", course: "c1", course_title: "Awareness base", course_kind: "corso", plan_item: null,
      plant: "p1", plant_code: "TA", held_on: "2026-05-10", audiences: ["a1"], target_count: 200,
      trained_count: 150, sent_count: null, clicked_count: null, reported_count: null, evidence: "e1",
      evidence_valid_until: "2027-05-10", evidence_file_path: "evidences/e1/registro.pdf", legacy: false, notes: "" },
  ]);
});

describe("TrainingPage", () => {
  it("per chi non legge i registri mostra solo il catalogo, senza azioni", async () => {
    api.capabilities.mockResolvedValue({
      can_read_records: false, can_manage_courses: false, can_manage_org: false, manage_plant_ids: [],
    });
    renderPage();
    expect(await screen.findByText("Awareness base")).toBeInTheDocument();
    expect(screen.queryByText("training.tabs.plan")).not.toBeInTheDocument();
    expect(screen.queryByText("training.courses.new")).not.toBeInTheDocument();
    expect(screen.getByText("A.6.3")).toBeInTheDocument();
  });

  it("il gestore del sito vede piano, erogazioni e gruppi con le azioni", async () => {
    api.capabilities.mockResolvedValue({
      can_read_records: true, can_manage_courses: true, can_manage_org: false, manage_plant_ids: ["p1"],
    });
    renderPage();
    expect(await screen.findByText("training.plan.add_item")).toBeInTheDocument();
    expect(await screen.findAllByText("training.item_states.in_ritardo")).toHaveLength(2);
    expect(screen.queryByText(/training.plan.create_org/)).not.toBeInTheDocument();

    fireEvent.click(screen.getByText("training.tabs.sessions"));
    expect(await screen.findByText("150/200")).toBeInTheDocument();
    expect(screen.getByText("Produzione")).toBeInTheDocument();
    expect(screen.getByText("training.sessions.download")).toBeInTheDocument();

    fireEvent.click(screen.getByText("training.sessions.new"));
    expect(await screen.findByText("training.sessions.register")).toBeDisabled();

    fireEvent.click(screen.getByText("training.tabs.audiences"));
    expect(await screen.findByText("training.audiences.stale")).toBeInTheDocument();
  });

  it("l'auditor legge i registri senza azioni di scrittura", async () => {
    api.capabilities.mockResolvedValue({
      can_read_records: true, can_manage_courses: false, can_manage_org: false, manage_plant_ids: [],
    });
    renderPage();
    expect(await screen.findAllByText("training.item_states.in_ritardo")).toHaveLength(2);
    expect(screen.queryByText("training.plan.add_item")).not.toBeInTheDocument();
    fireEvent.click(screen.getByText("training.tabs.sessions"));
    expect(await screen.findByText("150/200")).toBeInTheDocument();
    expect(screen.queryByText("training.sessions.new")).not.toBeInTheDocument();
  });
});
