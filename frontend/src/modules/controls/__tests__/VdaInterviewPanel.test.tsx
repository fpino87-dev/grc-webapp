import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { VdaInterviewPanel } from "../drawer/VdaInterviewPanel";
import type { VdaInterview } from "../../../api/endpoints/controls";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (k: string, o?: Record<string, unknown>) => (o?.count !== undefined ? `${k}:${o.count}` : k),
    i18n: { language: "pl" },
  }),
}));

vi.mock("../../../api/endpoints/controls", () => ({
  controlsApi: { getVdaInterview: vi.fn(), saveVdaInterview: vi.fn(), draftVdaInterview: vi.fn() },
}));

import { controlsApi } from "../../../api/endpoints/controls";

const interview: VdaInterview = {
  lang: "pl",
  requirements: [
    { id: "r1", level: "must", source: "L2", text_en: "A policy is released.", question: "Czy polityka jest zatwierdzona?" },
    { id: "r2", level: "should", source: "L2", text_en: "Policies are reviewed.", question: "" },
  ],
  answers: { r1: "Tak, przez zarząd" },
  answers_lang: "pl",
  answers_updated_at: null,
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

describe("VdaInterviewPanel", () => {
  beforeEach(() => vi.clearAllMocks());

  it("mostra la domanda nella lingua utente, o il requisito originale se manca", async () => {
    vi.mocked(controlsApi.getVdaInterview).mockResolvedValue(interview);
    renderPanel();
    expect(await screen.findByText("Czy polityka jest zatwierdzona?")).toBeInTheDocument();
    expect(screen.getByText("Policies are reviewed.")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Tak, przez zarząd")).toBeInTheDocument();
    expect(controlsApi.getVdaInterview).toHaveBeenCalledWith("inst-1", "pl");
  });

  it("genera la bozza, avvisa sui must senza risposta e la passa al campo descrizione", async () => {
    vi.mocked(controlsApi.getVdaInterview).mockResolvedValue({ ...interview, answers: {} });
    vi.mocked(controlsApi.draftVdaInterview).mockResolvedValue({
      draft_en: "[TO BE COMPLETED: policy release]", draft_local: "[DO UZUPEŁNIENIA]",
      unanswered: ["r1"], not_implemented: [], interaction_id: "ai-1",
      provider: "anthropic", model: "m", used_fallback: false,
    });
    const onUseDraft = renderPanel();
    const textareas = await screen.findAllByRole("textbox");
    fireEvent.change(textareas[1], { target: { value: "Nie" } });
    fireEvent.click(screen.getByText("controls.drawer.evaluation.interview.generate"));

    expect(await screen.findByText("⚠ controls.drawer.evaluation.interview.unanswered_warning:1", { exact: false })).toBeInTheDocument();
    expect(controlsApi.draftVdaInterview).toHaveBeenCalledWith("inst-1", { r2: "Nie" }, "pl");
    fireEvent.click(screen.getByText("controls.drawer.evaluation.interview.use_draft"));
    await waitFor(() => expect(onUseDraft).toHaveBeenCalledWith("[TO BE COMPLETED: policy release]", "ai-1"));
  });

  it("senza IA configurata la bozza non è generabile", async () => {
    vi.mocked(controlsApi.getVdaInterview).mockResolvedValue({ ...interview, ai_error: "not_configured" });
    renderPanel();
    expect(await screen.findByText("controls.drawer.evaluation.interview.ai_not_configured")).toBeInTheDocument();
    expect(screen.getByText("controls.drawer.evaluation.interview.generate").closest("button")).toBeDisabled();
  });
});
