import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RegisterTab } from "../RegisterTab";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (k: string) => k, i18n: { language: "it" } }),
}));

const base = {
  plant: "p1", plant_name: "Sito", is_legacy: false, is_inherited: false, status: "completato",
  asset_name: null, asset_group_label: "", supplier_name: null, critical_process_name: null,
  owner_name: "Mario", treatment: "mitigare", mitigation_plans_count: 0, mitigation_plans_completed: 0,
  mitigation_plans_verified: 0, active_acceptance: null, threat_title: "",
};
const list = vi.hoisted(() => vi.fn());
vi.mock("../../../api/endpoints/risk", () => ({
  ASSET_TYPES: ["IT", "OT", "SEDE", "PERSONALE", "FORNITORI", "PROTOTIPI"],
  riskApi: { list: (...a: unknown[]) => list(...a) },
}));

function renderTab(onOpen = vi.fn()) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={qc}><RegisterTab registerId="p1" onOpen={onOpen} /></QueryClientProvider>);
  return onOpen;
}

describe("RegisterTab", () => {
  it("ordina per classe, nasconde i non applicabili e apre la scheda", async () => {
    list.mockResolvedValue([
      { ...base, id: "a", name: "Basso", threat_code: "LO_ALE", asset_type: "SEDE", applicable: true, current_class: "low", expected_class: "" },
      { ...base, id: "b", name: "Critico", threat_code: "IN_MAL", asset_type: "IT", applicable: true, current_class: "critical", expected_class: "medium" },
      { ...base, id: "c", name: "Fuori", threat_code: "LO_AST", asset_type: "SEDE", applicable: false, current_class: "", expected_class: "" },
    ]);
    const onOpen = renderTab();
    const rows = await screen.findAllByRole("row");
    expect(rows[1].textContent).toContain("Critico");
    expect(rows[2].textContent).toContain("Basso");
    expect(screen.queryByText("Fuori")).toBeNull();
    expect(list).toHaveBeenCalledWith("p1", { include_inherited: "1" });
    fireEvent.click(rows[1]);
    expect(onOpen).toHaveBeenCalledWith("b");
  });
});
