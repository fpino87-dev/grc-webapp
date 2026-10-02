import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AiDraftButton } from "../RiskAi";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (k: string) => k, i18n: { language: "it" } }),
}));
const api = vi.hoisted(() => ({ aiDraft: vi.fn(), aiFeedback: vi.fn(() => Promise.resolve({})) }));
vi.mock("../../../api/endpoints/risk", () => ({
  IMPACT_DIMENSIONS: ["economic", "legal", "customer", "reputational", "people", "operational"],
  apiError: (_e: unknown, f: string) => f,
  riskApi: api,
}));

describe("AiDraftButton", () => {
  it("applica solo i campi scelti e registra l'esito", async () => {
    api.aiDraft.mockResolvedValue({
      provider: "t", model: "m", used_fallback: false, interaction_id: "i1",
      proposal: { vulnerability: "Patch in ritardo", probability: 4, impact_operational: 4 },
    });
    const onApply = vi.fn();
    const qc = new QueryClient();
    render(
      <QueryClientProvider client={qc}>
        <AiDraftButton risk={{ id: "r1" } as never} form={{ vulnerability: "", probability: null }} onApply={onApply} />
      </QueryClientProvider>,
    );
    fireEvent.click(screen.getByText(/risk.ai.draft/));
    expect(await screen.findByText("Patch in ritardo")).toBeTruthy();
    expect(onApply).not.toHaveBeenCalled(); // nulla applicato senza scelta
    const boxes = screen.getAllByRole("checkbox");
    fireEvent.click(boxes[1]); // deseleziona la probabilità
    fireEvent.click(screen.getByText("risk.ai.apply_selected"));
    expect(onApply).toHaveBeenCalledWith({ vulnerability: "Patch in ritardo", probability: null, impact_operational: 4 });
    await waitFor(() => expect(api.aiFeedback).toHaveBeenCalledWith("i1", "confirm", "vulnerability, impact_operational"));
  });
});
