import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AiDraftButton, AiIdentifyDialog } from "../RiskAi";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (k: string) => k, i18n: { language: "it" } }),
}));
const api = vi.hoisted(() => ({
  aiDraft: vi.fn(), aiIdentify: vi.fn(), aiIdentifyApply: vi.fn(), aiFeedback: vi.fn(() => Promise.resolve({})),
}));
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

describe("AiIdentifyDialog", () => {
  it("registra solo le proposte scelte e chiede il motivo della non applicabilità", async () => {
    api.aiIdentify.mockResolvedValue({
      provider: "t", model: "m", used_fallback: false, interaction_id: "i2", remaining: 3,
      names: { processes: {}, objectives: { o1: "Continuità forniture OEM" } },
      items: [
        { threat_id: "t1", threat_code: "IN_PHI", applicable: true, reason: "",
          proposal: { vulnerability: "Posta senza filtro", probability: 4 }, critical_process: null, business_objectives: ["o1"] },
        { threat_id: "t2", threat_code: "IN_MAL", applicable: true, reason: "", proposal: {} },
      ],
    });
    api.aiIdentifyApply.mockResolvedValue({ created: ["r1"], not_applicable: 1, skipped: 0 });
    render(
      <QueryClientProvider client={new QueryClient()}>
        <AiIdentifyDialog registerId="p1" assetType="IT" titles={new Map([["t1", "Phishing"]])} onClose={vi.fn()} />
      </QueryClientProvider>,
    );
    fireEvent.click(screen.getByText("risk.ai.identify_run"));
    expect(await screen.findByText(/Posta senza filtro/)).toBeTruthy();
    expect(screen.getByText("Continuità forniture OEM")).toBeTruthy();
    expect(api.aiIdentifyApply).not.toHaveBeenCalled(); // nulla registrato senza conferma
    // la seconda diventa non applicabile: senza motivo non si registra
    fireEvent.change(screen.getAllByRole("combobox")[1], { target: { value: "no" } });
    const applyBtn = screen.getByText("risk.ai.identify_apply") as HTMLButtonElement;
    expect(applyBtn.disabled).toBe(true);
    fireEvent.change(screen.getByPlaceholderText("risk.coverage.not_applicable_reason"), { target: { value: "Nessun asset" } });
    expect(applyBtn.disabled).toBe(false);
    fireEvent.click(applyBtn);
    await waitFor(() => expect(api.aiIdentifyApply).toHaveBeenCalled());
    const [, , sent] = api.aiIdentifyApply.mock.calls[0];
    expect(sent.map((i: { threat_code: string; applicable: boolean }) => [i.threat_code, i.applicable]))
      .toEqual([["IN_PHI", true], ["IN_MAL", false]]);
    expect(await screen.findByText("risk.ai.identify_done")).toBeTruthy();
    expect(screen.getByText("risk.ai.identify_next")).toBeTruthy(); // ne restano 3
    expect(api.aiFeedback).toHaveBeenCalledWith("i2", "confirm", expect.stringContaining("IN_MAL: n/a — Nessun asset"));
  });
});
