import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { VdaInterviewPanel } from "../drawer/VdaInterviewPanel";
import type { VdaInterview } from "../../../api/endpoints/controls";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (k: string, o?: Record<string, unknown>) => {
      if (!o) return k;
      const vals = Object.values(o).filter(v => typeof v !== "object").join(",");
      return vals ? `${k}:${vals}` : k;
    },
    i18n: { language: "pl" },
  }),
}));

vi.mock("../../../api/endpoints/controls", () => ({
  controlsApi: {
    getVdaInterview: vi.fn(), saveVdaInterview: vi.fn(),
    reviewVdaInterview: vi.fn(), draftVdaInterview: vi.fn(),
  },
}));

import { controlsApi } from "../../../api/endpoints/controls";

const base: VdaInterview = {
  lang: "pl",
  requirements: [
    { id: "r1", level: "must", source: "L2", text_en: "A policy is released." },
    { id: "r2", level: "should", source: "L2", text_en: "Policies are reviewed." },
  ],
  topics: [
    { id: "t1", question: "Jakie dokumenty macie?", auditor_intent: "Zrozumieć dokumenty",
      what_to_mention: ["polityka", "podręcznik"], example: "Dokument [kod]", req_ids: ["r1", "r2"] },
  ],
  answers: {},
  reviews: [],
  followups: [],
  followup_answers: {},
  rounds_used: 0,
  max_rounds: 2,
  declared_maturity: 3,
  updated_at: null,
  ai_error: "",
};

function renderPanel(onUseDraft = vi.fn()) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <VdaInterviewPanel instanceId="inst-1" onUseDraft={onUseDraft} />
    </QueryClientProvider>,
  );
  return onUseDraft;
}

const K = "controls.drawer.evaluation.interview";

describe("VdaInterviewPanel", () => {
  beforeEach(() => vi.clearAllMocks());

  it("mostra il tema con intento, cosa citare ed esempio a richiesta", async () => {
    vi.mocked(controlsApi.getVdaInterview).mockResolvedValue(base);
    renderPanel();
    expect(await screen.findByText("Jakie dokumenty macie?")).toBeInTheDocument();
    expect(screen.getByText("Zrozumieć dokumenty")).toBeInTheDocument();
    expect(screen.getByText("podręcznik")).toBeInTheDocument();
    expect(screen.queryByText("Dokument [kod]")).not.toBeInTheDocument();
    fireEvent.click(screen.getByText(`${K}.example_toggle`, { exact: false }));
    expect(screen.getByText("Dokument [kod]")).toBeInTheDocument();
    expect(controlsApi.getVdaInterview).toHaveBeenCalledWith("inst-1", "pl");
  });

  it("la verifica mostra copertura, maturità insufficiente e domande di approfondimento", async () => {
    vi.mocked(controlsApi.getVdaInterview).mockResolvedValue(base);
    vi.mocked(controlsApi.reviewVdaInterview).mockResolvedValue({
      ...base,
      answers: { t1: "Polityka POL-1" },
      rounds_used: 1,
      reviews: [{
        round: 1, at: "", summary: "Podstawa jest.", coverage: { r1: "covered", r2: "missing" },
        followups: [], evidence: [{ item: "Protokół zarządu", linked: "" }],
        maturity: { supported_level: 2, comment: "Brak przeglądu" },
      }],
      followups: [{ id: "f1_1", round: 1, question: "Jak często przeglądacie?", req_ids: ["r2"] }],
    });
    renderPanel();
    fireEvent.change(await screen.findByRole("textbox"), { target: { value: "Polityka POL-1" } });
    fireEvent.click(screen.getByText(`${K}.review:0,2`));

    expect(await screen.findByText("Podstawa jest.")).toBeInTheDocument();
    expect(controlsApi.reviewVdaInterview).toHaveBeenCalledWith("inst-1", {
      answers: { t1: "Polityka POL-1" }, followup_answers: {}, lang: "pl",
    });
    expect(screen.getByText(`✓ ${K}.coverage_covered:1`)).toBeInTheDocument();
    expect(screen.getByText(`⚠ ${K}.maturity_gap`)).toBeInTheDocument();  // 2 < dichiarata 3
    expect(screen.getByText("Jak często przeglądacie?")).toBeInTheDocument();
    expect(screen.getAllByRole("textbox")).toHaveLength(2);
  });

  it("genera la bozza, avvisa sui buchi obbligatori e la passa al campo descrizione", async () => {
    vi.mocked(controlsApi.getVdaInterview).mockResolvedValue({ ...base, answers: { t1: "Tak" } });
    vi.mocked(controlsApi.draftVdaInterview).mockResolvedValue({
      draft_en: "The policy is released.", draft_local: "Polityka jest wydana.",
      gaps: ["r1", "r2"], interaction_id: "ai-1", provider: "anthropic", model: "m", used_fallback: false,
    });
    const onUseDraft = renderPanel();
    fireEvent.click(await screen.findByText(`${K}.generate`));
    // r2 è "should": solo r1 conta tra i buchi obbligatori
    expect(await screen.findByText(`⚠ ${K}.gaps_warning:1`)).toBeInTheDocument();
    fireEvent.click(screen.getByText(`${K}.use_draft`));
    await waitFor(() => expect(onUseDraft).toHaveBeenCalledWith("The policy is released.", "ai-1"));
  });

  it("finiti i giri la verifica è disattivata e si può ricominciare con conferma", async () => {
    vi.mocked(controlsApi.getVdaInterview).mockResolvedValue({ ...base, answers: { t1: "Tak" }, rounds_used: 2 });
    vi.mocked(controlsApi.saveVdaInterview).mockResolvedValue({ ...base, answers: { t1: "Tak" } });
    renderPanel();
    expect((await screen.findByText(`${K}.review:2,2`)).closest("button")).toBeDisabled();
    fireEvent.click(screen.getByText(`${K}.reset`));
    fireEvent.click(screen.getByText(`${K}.reset_confirm`));
    await waitFor(() => expect(controlsApi.saveVdaInterview).toHaveBeenCalledWith("inst-1", {
      answers: { t1: "Tak" }, followup_answers: {}, lang: "pl", reset_reviews: true,
    }));
  });

  it("senza IA mostra solo i requisiti originali", async () => {
    vi.mocked(controlsApi.getVdaInterview).mockResolvedValue({ ...base, topics: [], ai_error: "not_configured" });
    renderPanel();
    expect(await screen.findByText(`${K}.ai_not_configured`)).toBeInTheDocument();
    expect(screen.getByText("A policy is released.")).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });
});
