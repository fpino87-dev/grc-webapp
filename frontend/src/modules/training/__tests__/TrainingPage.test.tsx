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

vi.mock("../../../api/endpoints/training", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../../api/endpoints/training")>()),
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
    participantOptions: vi.fn(),
    boardStatus: vi.fn(),
    competencyOptions: vi.fn(),
  },
}));

import { trainingApi } from "../../../api/endpoints/training";
const api = vi.mocked(trainingApi);

const course = {
  id: "c1", title: "Awareness base", description: "", source: "interno" as const, status: "attivo" as const,
  kind: "corso" as const, audience_kind: "generale" as const, mandatory: true, duration_minutes: 60,
  validity_months: 12, controls: ["k1"],
  controls_detail: [{ id: "k1", external_id: "A.6.3", framework_code: "ISO27001", title: "Awareness" }],
  competency: "", competency_level: 1 as const,
};
const boardCourse = {
  ...course, id: "c2", title: "Cyber per il CdA", audience_kind: "organo_gestione" as const,
  controls: [], controls_detail: [], competency: "NIS2 Compliance", competency_level: 2 as const,
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
      evidence_valid_until: "2027-05-10", evidence_file_path: "evidences/e1/registro.pdf", legacy: false, notes: "",
      participants_detail: [] },
    { id: "s2", course: "c2", course_title: "Cyber per il CdA", course_kind: "corso", plan_item: null,
      plant: "p1", plant_code: "TA", held_on: "2026-04-02", audiences: [], target_count: 1,
      trained_count: 1, sent_count: null, clicked_count: null, reported_count: null, evidence: "e2",
      evidence_valid_until: "2027-04-02", evidence_file_path: "evidences/e2/firme.pdf", legacy: false, notes: "",
      participants_detail: [{ id: "tp1", name: "Mario Rossi", roles: [], committee: "CdA",
                              user_id: null, member_id: "m1" }] },
  ]);
  api.boardStatus.mockResolvedValue({
    total: 2, trained: 1, pct: 50,
    members: [
      { member_id: "m1", full_name: "Mario Rossi", position: "Presidente", committee: "CdA",
        trained: true, valid_until: "2027-04-02" },
      { member_id: "m2", full_name: "Giulia Bianchi", position: "", committee: "CdA",
        trained: false, valid_until: null },
    ],
  });
  api.participantOptions.mockResolvedValue({
    role_holders: [{ user_id: "u1", name: "Anna Neri", roles: ["ciso"] }],
    members: [{ member_id: "m2", name: "Giulia Bianchi", position: "", committee: "CdA",
                management_body: true, user_id: null }],
  });
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
    expect(screen.getAllByText("training.sessions.download")).toHaveLength(2);

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

  it("erogazione per il CdA: partecipanti per nome e stato dell'organo di gestione", async () => {
    api.capabilities.mockResolvedValue({
      can_read_records: true, can_manage_courses: true, can_manage_org: false, manage_plant_ids: ["p1"],
    });
    api.courses.mockResolvedValue([course, boardCourse]);
    renderPage();
    fireEvent.click(await screen.findByText("training.tabs.sessions"));

    // Riquadro NIS2 art. 20 e partecipanti nella lista.
    expect(await screen.findByText(/training.board.summary/)).toHaveTextContent('"trained":1');
    expect(screen.getByText("Giulia Bianchi")).toBeInTheDocument();
    expect(screen.getAllByText("Mario Rossi").length).toBeGreaterThanOrEqual(2);

    fireEvent.click(screen.getByText("training.sessions.new"));
    const select = (await screen.findAllByRole("combobox"))[0];
    fireEvent.change(select, { target: { value: "c2" } });
    expect(await screen.findByText("Anna Neri")).toBeInTheDocument();
    expect(screen.queryByRole("checkbox", { name: /Produzione/ })).not.toBeInTheDocument();

    const register = screen.getByText("training.sessions.register");
    fireEvent.click(screen.getByLabelText(/Anna Neri/));
    const file = new File(["x"], "firme.pdf", { type: "application/pdf" });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });
    expect(register).toBeEnabled();

    api.registerSession.mockResolvedValue({
      ...(await api.sessions.mock.results[0].value)[1], control_links: { linked: 0, not_applicable: [] },
    });
    fireEvent.click(register);
    await vi.waitFor(() => expect(api.registerSession).toHaveBeenCalled());
    const form = api.registerSession.mock.calls[0][0] as FormData;
    expect(form.getAll("participant_users")).toEqual(["u1"]);
    expect(form.getAll("audiences")).toEqual([]);
    expect(form.get("trained_count")).toBeNull();
  });
});
