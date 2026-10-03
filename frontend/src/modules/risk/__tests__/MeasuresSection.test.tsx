import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MeasuresSection } from "../RiskSections";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (k: string) => k, i18n: { language: "it" } }),
}));
const api = vi.hoisted(() => ({
  measures: vi.fn((): Promise<unknown[]> => Promise.resolve([])), createMeasure: vi.fn(() => Promise.resolve({})),
  updateMeasure: vi.fn(() => Promise.resolve({})), deleteMeasure: vi.fn(),
}));
vi.mock("../../../api/endpoints/risk", () => ({ apiError: (_e: unknown, f: string) => f, riskApi: api }));
const controls = vi.hoisted(() => ({
  instances: vi.fn(() => Promise.resolve({ results: [
    { id: "c1", plant: "p1", control_external_id: "ISA-1.1", control_title: "Policy" },
    { id: "c2", plant: "p2", control_external_id: "ISA-5.2", control_title: "Accessi remoti" },
  ] })),
}));
vi.mock("../../../api/endpoints/controls", () => ({ controlsApi: controls }));
vi.mock("../../../api/endpoints/plants", () => ({
  plantsApi: { list: vi.fn(() => Promise.resolve([{ id: "p1", code: "S1" }, { id: "p2", code: "S2" }])) },
}));
vi.mock("../../../api/endpoints/users", () => ({ usersApi: { list: vi.fn(() => Promise.resolve([])) } }));
vi.mock("../../../api/endpoints/governance", () => ({ governanceApi: { committees: vi.fn(() => Promise.resolve([])) } }));
vi.mock("../RiskAi", () => ({ AiMeasuresButton: () => null }));

const renderSection = (plant: string | null) => render(
  <QueryClientProvider client={new QueryClient()}>
    <MeasuresSection risk={{ id: "r1", plant } as never} editable />
  </QueryClientProvider>,
);

describe("MeasuresSection", () => {
  it("rischio di gruppo: controlli di tutti i siti, col codice del sito, collegabili", async () => {
    renderSection(null);
    const option = await screen.findByText("[S2] ISA-5.2 Accessi remoti");
    const select = option.closest("select")!;
    expect(select).not.toBeDisabled();
    expect(controls.instances).toHaveBeenCalledWith({});
    fireEvent.change(select, { target: { value: "c2" } });
    fireEvent.click(screen.getByText(/common.add/));
    await waitFor(() => expect(api.createMeasure).toHaveBeenCalledWith(expect.objectContaining({
      risk: "r1", control_instance: "c2",
    })));
  });

  it("rischio di sito: solo i controlli del sito, senza prefisso", async () => {
    renderSection("p1");
    await screen.findByText("ISA-1.1 Policy");
    expect(controls.instances).toHaveBeenCalledWith({ plant: "p1" });
  });

  it("una misura esistente si modifica: testo ed efficacia", async () => {
    api.measures.mockResolvedValueOnce([{ id: "m1", risk: "r1", control_instance: null, control_title: null,
      description: "Backup offline", effectiveness: "media", created_at: "" }]);
    renderSection("p1");
    fireEvent.click(await screen.findByText("common.edit"));
    fireEvent.change(screen.getByDisplayValue("Backup offline"), { target: { value: "Backup offline con test di restore" } });
    fireEvent.change(screen.getByLabelText("risk.drawer.effectiveness"), { target: { value: "alta" } });
    fireEvent.click(screen.getByText("common.save"));
    await waitFor(() => expect(api.updateMeasure).toHaveBeenCalledWith("m1", expect.objectContaining({
      description: "Backup offline con test di restore", effectiveness: "alta",
    })));
    expect(api.createMeasure).not.toHaveBeenCalledWith(expect.objectContaining({ description: "Backup offline con test di restore" }));
  });
});
