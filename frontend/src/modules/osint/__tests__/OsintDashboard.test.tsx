import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { OsintDashboard } from "../OsintDashboard";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (k: string) => k, i18n: { language: "it" } }),
}));
vi.mock("../../../i18n", () => ({
  default: { language: "it", getFixedT: () => (k: string) => k, t: (k: string) => k },
}));
vi.mock("../OsintAiPanel", () => ({ OsintAiPanel: () => null }));
vi.mock("../../../api/endpoints/osint", async (orig) => {
  const actual = await orig<typeof import("../../../api/endpoints/osint")>();
  return {
    ...actual,
    osintApi: {
      posture: vi.fn(), changes: vi.fn(), dashboardSummary: vi.fn(), entities: vi.fn(), findings: vi.fn(),
      reportFinding: vi.fn(), entity: vi.fn(), entityHistory: vi.fn(), setPosture: vi.fn(), forceScan: vi.fn(),
    },
  };
});

import { osintApi } from "../../../api/endpoints/osint";

const api = vi.mocked(osintApi);

const supplierFinding = {
  id: "f2", entity: "e2", entity_domain: "fornitore.it", entity_display_name: "Fornitore Srl", entity_type: "supplier",
  is_nis2_critical: true, scan: null, code: "ssl_expired", severity: "critical", params: {}, status: "open",
  first_seen: "2026-09-01T00:00:00Z", last_seen: "2026-09-20T00:00:00Z", resolved_at: null, resolution_note: "",
  accepted_risk_until: null, linked_task_id: null, reported_at: null, reported_by_name: null, report_note: "",
  report_overdue: false, playbook: null,
};
const ownFinding = { ...supplierFinding, id: "f1", entity: "e1", entity_domain: "azienda.it", entity_display_name: "Azienda", entity_type: "my_domain", code: "blacklist" };

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}><MemoryRouter><OsintDashboard /></MemoryRouter></QueryClientProvider>);
}

beforeEach(() => {
  vi.clearAllMocks();
  api.posture.mockResolvedValue({
    security: 78, grade: "B", entities: 2, trend: [{ week_end: "2026-09-01", security: 70 }, { week_end: "2026-09-08", security: 78 }],
    own: { critical: 1, warning: 2, info: 0, resolved_week: 3 }, suppliers: { to_report: 1, reported_open: 0, overdue: 0 },
  } as never);
  api.changes.mockResolvedValue({ days: 7, new_own: { count: 1, items: [] }, resolved_own: 3, new_supplier_critical: { count: 1, items: [] }, score_changes: [], pending_subdomains: 0 } as never);
  api.dashboardSummary.mockResolvedValue({ pending_subdomains: 0 } as never);
  api.entities.mockResolvedValue([
    { id: "e1", entity_type: "my_domain", domain: "azienda.it", display_name: "Azienda", is_nis2_critical: false, grade: "B", security: 78, trend: [70, 78], open_findings: { critical: 1, warning: 0, info: 0 }, last_scan: null, delta: 0, active_alerts_count: 0 },
    { id: "e2", entity_type: "supplier", domain: "fornitore.it", display_name: "Fornitore Srl", is_nis2_critical: true, grade: "F", security: 20, trend: [30, 20], open_findings: { critical: 1, warning: 0, info: 0 }, last_scan: null, delta: 0, active_alerts_count: 0 },
  ] as never);
  api.findings.mockImplementation((params?: Record<string, string>) =>
    Promise.resolve((params?.ownership === "supplier" ? [supplierFinding] : [ownFinding]) as never));
  api.reportFinding.mockResolvedValue({} as never);
});

describe("OSINT — dashboard", () => {
  it("mostra voto, coda da correggere e fornitori da segnalare separati", async () => {
    renderPage();
    expect(await screen.findAllByText("B")).not.toHaveLength(0);
    expect(await screen.findByText("azienda.it · osint.dash.since_days")).toBeInTheDocument();
    expect(screen.getByText("Fornitore Srl")).toBeInTheDocument();
    expect(api.findings).toHaveBeenCalledWith({ ownership: "own", open_only: "1", severity: "critical" });
    expect(api.findings).toHaveBeenCalledWith({ ownership: "supplier", open_only: "1", severity: "critical" });
  });

  it("segnala al fornitore: testo pronto e registrazione della segnalazione", async () => {
    renderPage();
    fireEvent.click(await screen.findByText("osint.dash.report_btn"));
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText("osint.report.subject")).toBeInTheDocument();
    fireEvent.change(within(dialog).getByPlaceholderText("osint.report.note_placeholder"), { target: { value: "mail al referente" } });
    fireEvent.click(within(dialog).getByText("osint.report.mark"));
    await vi.waitFor(() => expect(api.reportFinding).toHaveBeenCalledWith("f2", "mail al referente"));
  });

  it("la tab fornitori mostra voto e stato delle segnalazioni, non il dettaglio tecnico", async () => {
    renderPage();
    fireEvent.click(await screen.findByText(/osint\.dash\.tab_supplier/));
    expect(await screen.findByText("osint.dash.supplier_tab_hint")).toBeInTheDocument();
    expect(screen.getByText("osint.dash.sup_to_report")).toBeInTheDocument();
    expect(screen.queryByText("SSL")).not.toBeInTheDocument();
  });
});
