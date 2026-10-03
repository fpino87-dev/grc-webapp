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
const attention = vi.hoisted(() => vi.fn());
vi.mock("../../../api/endpoints/risk", () => ({
  ASSET_TYPES: ["IT", "OT", "SEDE", "PERSONALE", "FORNITORI", "PROTOTIPI"],
  ATTENTION_KEYS: ["critical_untreated", "high_untreated", "acceptances_expiring", "overdue_measures"],
  riskApi: { list: (...a: unknown[]) => list(...a), attention: (...a: unknown[]) => attention(...a) },
}));
vi.mock("../../../api/endpoints/plants", () => ({
  plantsApi: { list: () => Promise.resolve([{ id: "p1", code: "S1", name: "Sito Nord" }, { id: "p2", code: "S2", name: "Sito Sud" }]) },
}));
const none = { count: 0, risk_ids: [] };

function renderTab(onOpen = vi.fn(), registerId: string | null = "p1") {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={qc}><RegisterTab registerId={registerId} onOpen={onOpen} /></QueryClientProvider>);
  return onOpen;
}

describe("RegisterTab", () => {
  it("i contatori filtrano il registro sui rischi da trattare", async () => {
    list.mockResolvedValue([
      { ...base, id: "a", name: "Basso", display_name: "Basso", threat_code: "LO_ALE", asset_type: "SEDE", applicable: true, current_class: "low", expected_class: "" },
      { ...base, id: "b", name: "Critico", display_name: "Critico", threat_code: "IN_MAL", asset_type: "IT", applicable: true, current_class: "critical", expected_class: "" },
    ]);
    attention.mockResolvedValue({
      critical_untreated: { count: 1, risk_ids: ["b"] }, high_untreated: none,
      acceptances_expiring: none, overdue_measures: { ...none, measures: 0 },
    });
    renderTab();
    expect(await screen.findAllByRole("row")).toHaveLength(3);
    const counter = (await screen.findByText("risk.attention.critical_untreated")).closest("button")!;
    expect(screen.getByText("risk.attention.high_untreated").closest("button")!.hasAttribute("disabled")).toBe(true);
    fireEvent.click(counter);
    const rows = screen.getAllByRole("row");
    expect(rows).toHaveLength(2);
    expect(rows[1].textContent).toContain("Critico");
    fireEvent.click(counter);
    expect(screen.getAllByRole("row")).toHaveLength(3);
  });

  it("ordina per classe, nasconde i non applicabili e apre la scheda", async () => {
    list.mockResolvedValue([
      { ...base, id: "a", name: "Basso", display_name: "Basso", threat_code: "LO_ALE", asset_type: "SEDE", applicable: true, current_class: "low", expected_class: "" },
      { ...base, id: "b", name: "Critico", display_name: "Critico", threat_code: "IN_MAL", asset_type: "IT", applicable: true, current_class: "critical", expected_class: "medium" },
      { ...base, id: "c", name: "Fuori", display_name: "Fuori", threat_code: "LO_AST", asset_type: "SEDE", applicable: false, current_class: "", expected_class: "" },
    ]);
    attention.mockResolvedValue({ critical_untreated: none, high_untreated: none, acceptances_expiring: none, overdue_measures: none });
    const onOpen = renderTab();
    const rows = await screen.findAllByRole("row");
    expect(rows[1].textContent).toContain("Critico");
    expect(rows[2].textContent).toContain("Basso");
    expect(screen.queryByText("Fuori")).toBeNull();
    expect(list).toHaveBeenCalledWith("p1", { include_inherited: "1" });
    fireEvent.click(rows[1]);
    expect(onOpen).toHaveBeenCalledWith("b");
  });

  it("vista gruppo: ultima colonna con i siti che ereditano il rischio", async () => {
    list.mockResolvedValue([
      { ...base, plant: null, id: "g1", name: "Accesso remoto", display_name: "Accesso remoto", threat_code: "FO_RMT",
        asset_type: "FORNITORI", applicable: true, current_class: "high", expected_class: "", affected_plants: ["p1", "p2"] },
      { ...base, plant: null, id: "g2", name: "Phishing", display_name: "Phishing", threat_code: "PE_PHI",
        asset_type: "PERSONALE", applicable: true, current_class: "medium", expected_class: "", affected_plants: [] },
    ]);
    attention.mockResolvedValue({
      critical_untreated: none, high_untreated: none, acceptances_expiring: none, overdue_measures: { ...none, measures: 0 },
    });
    renderTab(vi.fn(), null);
    expect(await screen.findByText("risk.register.col_affected_plants")).toBeTruthy();
    expect(await screen.findByText("S2")).toBeTruthy();
    expect(screen.getByText("S1").closest("span[title]")!.getAttribute("title")).toBe("Sito Nord, Sito Sud");
    expect(screen.getByText("risk.register.no_affected_plants")).toBeTruthy();
  });

  it("vista sito: niente colonna dei siti", async () => {
    list.mockResolvedValue([]);
    attention.mockResolvedValue({
      critical_untreated: none, high_untreated: none, acceptances_expiring: none, overdue_measures: { ...none, measures: 0 },
    });
    renderTab();
    await screen.findByText("risk.register.empty");
    expect(screen.queryByText("risk.register.col_affected_plants")).toBeNull();
  });
});
