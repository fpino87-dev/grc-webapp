import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PlanSection } from "../RiskSections";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (k: string) => k, i18n: { language: "it" } }),
}));
const api = vi.hoisted(() => ({
  plans: vi.fn(), updatePlan: vi.fn(() => Promise.resolve({})), createPlan: vi.fn(), deletePlan: vi.fn(),
  verifyPlan: vi.fn(), uncompletePlan: vi.fn(), applyExpected: vi.fn(),
}));
vi.mock("../../../api/endpoints/risk", () => ({ apiError: (_e: unknown, f: string) => f, riskApi: api }));
vi.mock("../../../api/endpoints/controls", () => ({ controlsApi: { instances: vi.fn(() => Promise.resolve({ results: [] })) } }));
vi.mock("../../../api/endpoints/users", () => ({ usersApi: { list: vi.fn(() => Promise.resolve([])) } }));
vi.mock("../../../api/endpoints/governance", () => ({ governanceApi: { committees: vi.fn(() => Promise.resolve([])) } }));
vi.mock("../RiskAi", () => ({ AiMeasuresButton: () => null }));

const plan = {
  id: "m1", assessment: "r1", action: "EDR sulle postazioni", owner: null, owner_external: "Fornitore IT",
  owner_name: "Fornitore IT", due_date: "2026-12-31", expected_effect: "probabilita", control_instance: null,
  control_title: null, completed_at: null, verified_at: null,
};

describe("PlanSection", () => {
  it("modifica testo e scadenza di una misura esistente", async () => {
    api.plans.mockResolvedValue([plan]);
    render(
      <QueryClientProvider client={new QueryClient()}>
        <PlanSection risk={{ id: "r1", plant: "p1", treatment: "mitigare", current_class: "high" } as never} canMonitor />
      </QueryClientProvider>,
    );
    fireEvent.click(await screen.findByText("common.edit"));
    const text = screen.getByDisplayValue("EDR sulle postazioni");
    fireEvent.change(text, { target: { value: "EDR su postazioni e server MES" } });
    fireEvent.change(screen.getByDisplayValue("2026-12-31"), { target: { value: "2027-01-31" } });
    fireEvent.click(screen.getByText("common.save"));
    await waitFor(() => expect(api.updatePlan).toHaveBeenCalledWith("m1", expect.objectContaining({
      action: "EDR su postazioni e server MES", due_date: "2027-01-31", expected_effect: "probabilita",
      owner_external: "Fornitore IT",
    })));
    expect(api.createPlan).not.toHaveBeenCalled();
  });

  it("una misura verificata non si modifica", async () => {
    api.plans.mockResolvedValue([{ ...plan, completed_at: "2026-10-01", verified_at: "2026-10-02" }]);
    render(
      <QueryClientProvider client={new QueryClient()}>
        <PlanSection risk={{ id: "r1", plant: "p1", treatment: "mitigare", current_class: "high" } as never} canMonitor />
      </QueryClientProvider>,
    );
    await screen.findByText("EDR sulle postazioni");
    expect(screen.queryByText("common.edit")).toBeNull();
  });
});
