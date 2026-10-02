import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { RiskPage } from "../RiskPage";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (k: string) => k, i18n: { language: "it" } }),
}));
vi.mock("../../../store/auth", () => ({
  useAuthStore: (sel: (s: { selectedPlant: { id: string; code: string; name: string } }) => unknown) =>
    sel({ selectedPlant: { id: "p1", code: "P1", name: "Sito 1" } }),
}));
vi.mock("../../../components/ui/ModuleHelp", () => ({ ModuleHelp: () => null }));
vi.mock("../../../lib/scrollAndHighlight", () => ({ scrollAndHighlight: vi.fn() }));
vi.mock("../RiskIntegratedRegisters", () => ({ RiskIntegratedRegisters: () => null }));

const { policy, risk, cycle } = vi.hoisted(() => {
const CLASSES = ["very_low", "low", "medium", "high", "critical"];
const rule = { roles: ["risk_owner"], scope: "plant", requires_body: false };
const policy = {
  preset: "centralizzato", configured: false, group_register_enabled: true, user_org_scope: true,
  acceptance_matrix: Object.fromEntries(CLASSES.map(c => [c, rule])),
  upper_opinion: Object.fromEntries(CLASSES.map(c => [c, "none"])),
  acceptance_max_months: Object.fromEntries(CLASSES.map(c => [c, 12])),
  treatment_months: { critical: 3, high: 12, medium: 24, low: 60, very_low: 60 },
  economic_thresholds: { "2": 10000, "3": 50000, "4": 250000, "5": 500000 },
  overdue_escalation_days: 30, review_frequency_months: 12, org_policy_id: null, plant_policy_id: null,
};
const risk = {
  id: "r1", plant: "p1", plant_name: "Sito 1", cycle: "c1", evaluated_in_cycle: "c1", is_legacy: false,
  is_inherited: false, affected_plants: [], name: "Ransomware MES", display_name: "Ransomware MES", status: "completato", asset_type: "IT",
  asset: null, asset_name: null, asset_group_label: "Server", supplier: null, supplier_name: null,
  threat: "t1", threat_code: "IN_MAL", threat_title: "Malware", information_classes: [],
  critical_process: null, critical_process_name: null, vulnerability: "", consequence: "", applicable: true,
  not_applicable_reason: "", probability: 4, probability_method: "fer", probability_rationale: "x",
  impact_economic: null, impact_legal: null, impact_customer: null, impact_reputational: null, impact_people: null,
  impact_operational: 4, impact: 4, impact_rationale: "y", matrix_class: "critical", class_override: 0,
  override_rationale: "", current_class: "critical", legal_or_contract_violation: false, treatment: "mitigare",
  treatment_rationale: "", treatment_rule: { rule: "mandatory", months: 3 }, expected_probability: 2,
  expected_impact: 4, expected_class: "high", can_apply_expected: false, owner: 1, owner_name: "Mario",
  treatment_owner: null, treatment_owner_external: "MSP", treatment_owner_name: "MSP", plan_due_date: null,
  nis2_in_scope: true, nis2_art21_category: "art21_b", impacted_systems: "", significant_incident_potential: false,
  significant_incident_note: "", assessed_by: 1, assessed_by_name: "Mario", assessed_at: "2026-10-01T10:00:00Z",
  mitigation_plans_count: 1, mitigation_plans_completed: 0, mitigation_plans_verified: 0, active_acceptance: null,
  legacy_snapshot: {}, created_at: "", updated_at: "",
};
const cycle = { id: "c1", plant: "p1", plant_name: "Sito 1", kind: "primo", trigger_reason: "", status: "in_corso",
  started_at: "2026-10-01T10:00:00Z", closed_at: null, approved_by_body: null, approved_by_body_name: null,
  approval_review: null, approved_at: null, local_adoption_ref: "", risks_count: 1 };
  return { policy, risk, cycle };
});

vi.mock("../../../api/endpoints/risk", () => {
  const ok = <T,>(v: T) => vi.fn(() => Promise.resolve(v));
  return {
    ASSET_TYPES: ["IT", "OT", "SEDE", "PERSONALE", "FORNITORI", "PROTOTIPI"],
    ATTENTION_KEYS: ["critical_untreated", "high_untreated", "acceptances_expiring", "overdue_measures"],
    IMPACT_DIMENSIONS: ["economic", "legal", "customer", "reputational", "people", "operational"],
    apiError: (_e: unknown, f: string) => f,
    riskApi: {
      resolvedPolicy: ok(policy), presets: ok({ centralizzato: policy }), cycles: ok([cycle]), triggers: ok([]),
      attention: ok({ critical_untreated: { count: 1, risk_ids: ["r1"] }, high_untreated: { count: 0, risk_ids: [] }, acceptances_expiring: { count: 0, risk_ids: [] }, overdue_measures: { count: 1, risk_ids: ["r1"], measures: 1 } }),
      list: ok([risk]), get: ok(risk), legacy: ok([]),
      coverage: ok({ asset_types: ["IT"], pairs: [{ asset_type: "IT", threat_id: "t1", threat_code: "IN_MAL", state: "evaluated", risk_ids: ["r1"], worst_class: "critical" }], total: 1, closed: 1, missing: 0, pct: 100 }),
      matrix: ok([5, 4, 3, 2, 1].flatMap(p => [1, 2, 3, 4, 5].map(i => ({ probability: p, impact: i, count: p === 4 && i === 4 ? 1 : 0, class: "medium" })))),
      threats: ok([{ id: "t1", code: "IN_MAL", title: "Malware", asset_types: ["IT"], cia: ["C"], translations: {}, source: "catalog", catalog_version: "1", active: true }]),
      informationClasses: ok([]), measures: ok([]),
      plans: ok([{ id: "m1", assessment: "r1", action: "EDR", owner: null, owner_external: "MSP", owner_name: "MSP", due_date: "2020-01-01", expected_effect: "probabilita", bcp_plan: null, bcp_plan_title: null, bcp_plan_status: null, control_instance: null, control_title: null, completed_at: null, verified_at: null, verified_by: null, verified_by_name: null, verification_note: "", escalation_level: 1, created_at: "" }]),
      acceptances: ok([]), acceptanceRequirements: ok({ class: "critical", roles: [], scope: "org", requires_body: true, notify: [], upper_opinion: "binding", max_months: 6, not_acceptable: false }),
      localImpactReports: ok([]), exportExcel: ok({ data: "" }), exportCycle: ok({ data: "" }),
    },
  };
});
vi.mock("../../../api/endpoints/plants", () => ({ plantsApi: { list: () => Promise.resolve([{ id: "p1", code: "P1", name: "Sito 1" }]) } }));
vi.mock("../../../api/endpoints/managementReview", () => ({ managementReviewApi: { list: () => Promise.resolve({ results: [] }) } }));
vi.mock("../../../api/endpoints/governance", () => ({ governanceApi: { committees: () => Promise.resolve([]) } }));
vi.mock("../../../api/endpoints/users", () => ({ usersApi: { list: () => Promise.resolve([{ id: 1, username: "m", email: "m@x", first_name: "Mario", last_name: "" }]) } }));
vi.mock("../../../api/endpoints/assets", () => ({ assetsApi: { listIT: () => Promise.resolve({ results: [] }), listSW: () => Promise.resolve({ results: [] }), listOT: () => Promise.resolve({ results: [] }), listFacility: () => Promise.resolve({ results: [] }) } }));
vi.mock("../../../api/endpoints/suppliers", () => ({ suppliersApi: { list: () => Promise.resolve({ results: [] }) } }));
vi.mock("../../../api/endpoints/bia", () => ({ biaApi: { list: () => Promise.resolve({ results: [] }) } }));
vi.mock("../../../api/endpoints/controls", () => ({ controlsApi: { instances: () => Promise.resolve({ results: [] }) } }));

describe("RiskPage", () => {
  it("passa per tutte le schede e apre la scheda del rischio senza errori", async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={qc}><MemoryRouter><RiskPage /></MemoryRouter></QueryClientProvider>);
    expect(await screen.findByText("Ransomware MES")).toBeTruthy();
    for (const tab of ["matrix", "coverage", "plan", "acceptances", "cycles", "settings", "register"]) {
      fireEvent.click(screen.getByText(`risk.page.tabs.${tab}`));
      await waitFor(() => expect(screen.getByText(`risk.page.tabs.${tab}`)).toBeTruthy());
    }
    fireEvent.click(await screen.findByText("Ransomware MES"));
    expect(await screen.findByText("risk.drawer.identification")).toBeTruthy();
    expect(await screen.findByText("risk.drawer.treatment_plan")).toBeTruthy();
    expect(screen.getByText("risk.drawer.complete")).toBeTruthy();
  });
});
