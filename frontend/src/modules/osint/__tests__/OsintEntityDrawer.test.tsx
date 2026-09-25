import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { OsintEntityDrawer } from "../OsintEntityDrawer";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (k: string) => k, i18n: { language: "it" } }),
}));
vi.mock("../../../i18n", () => ({
  default: { language: "it", getFixedT: () => (k: string) => k, t: (k: string) => k },
}));
vi.mock("../../../api/endpoints/osint", async (orig) => {
  const actual = await orig<typeof import("../../../api/endpoints/osint")>();
  return { ...actual, osintApi: { entity: vi.fn(), entityHistory: vi.fn(), setPosture: vi.fn(), forceScan: vi.fn(), reportFinding: vi.fn() } };
});

import { osintApi } from "../../../api/endpoints/osint";

const api = vi.mocked(osintApi);
const finding = (o = {}) => ({
  id: "f1", entity: "e1", entity_domain: "x.it", entity_display_name: "X", entity_type: "supplier", is_nis2_critical: false,
  scan: null, code: "blacklist", severity: "critical", params: {}, status: "reported", first_seen: "2026-08-01T00:00:00Z",
  last_seen: "2026-09-01T00:00:00Z", resolved_at: null, resolution_note: "", accepted_risk_until: null, linked_task_id: null,
  reported_at: "2026-08-02T00:00:00Z", reported_by_name: "Mario", report_note: "", report_overdue: true, playbook: null, ...o,
});
const entity = (o = {}) => ({
  id: "e1", entity_type: "supplier", domain: "x.it", display_name: "X", is_nis2_critical: false, grade: "F", security: 20,
  last_scan: null, delta: 0, active_alerts: [], active_alerts_count: 0, pending_subdomains_count: 0, events: [],
  findings: [finding(), finding({ id: "f2", severity: "warning", code: "dkim_missing", status: "open", reported_at: null, report_overdue: false })],
  expected_mail: "unknown", expected_web: "unknown", ...o,
});

function renderDrawer() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}><MemoryRouter><OsintEntityDrawer entityId="e1" onClose={() => {}} /></MemoryRouter></QueryClientProvider>);
}

beforeEach(() => {
  vi.clearAllMocks();
  api.entityHistory.mockResolvedValue([] as never);
});

describe("OSINT — scheda entità", () => {
  it("fornitore: critici da sollecitare, gli altri solo informativi, niente correzione", async () => {
    api.entity.mockResolvedValue(entity() as never);
    renderDrawer();
    fireEvent.click(await screen.findByText(/osint\.drawer\.tabs\.problems/));
    expect(screen.getByText(/osint\.drawer\.still_open/)).toBeInTheDocument();
    expect(screen.getByText("osint.dash.remind")).toBeInTheDocument();
    expect(screen.getByText("osint.drawer.minor_info")).toBeInTheDocument();
    expect(screen.queryByText(/osint\.drawer\.go_fix/)).not.toBeInTheDocument();
  });

  it("dominio proprio: problemi da correggere con rimando a Da correggere", async () => {
    api.entity.mockResolvedValue(entity({ entity_type: "my_domain", findings: [finding({ entity_type: "my_domain", status: "open", reported_at: null, report_overdue: false })] }) as never);
    renderDrawer();
    fireEvent.click(await screen.findByText(/osint\.drawer\.tabs\.problems/));
    expect(screen.getByText(/osint\.drawer\.go_fix/)).toBeInTheDocument();
    expect(screen.queryByText("osint.dash.report_btn")).not.toBeInTheDocument();
  });

  it("fornitore critico: pilastri del voto, cosa fare tu, dati di supply chain", async () => {
    api.entity.mockResolvedValue(entity({
      deep_monitoring: true, service_hosts: ["portale.x.it"],
      findings: [finding({ code: "domain_spoofable", status: "open", reported_at: null, report_overdue: false })],
      last_scan: {
        scan_date: "2026-09-20T00:00:00Z", score_total: 60, score_ssl: 0, score_dns: 0, score_reputation: 0, score_grc_context: 0,
        score_compromise: 0, score_impersonation: 60, score_exposure: 100, score_maturity: 20,
        remote_access: [{ host: "vpn.x.it", ip: "203.0.113.1", ports: [443], admin_ports: [], kev: ["CVE-2024-21762"], vulns_count: 2 }],
        service_checks: [{ host: "portale.x.it", reachable: true, days_remaining: -1, expiry: "2026-09-19" }],
        ransomware_hits: [], hibp_domain_breaches: [], lookalike_domains: [{ domain: "x-it.com", mx: true }],
        enricher_errors: {}, blacklist_sources: [],
      },
    }) as never);
    renderDrawer();
    expect(await screen.findByText("osint.chain.pillar_impersonation")).toBeInTheDocument();
    expect(screen.getByText("osint.chain.deep_badge")).toBeInTheDocument();
    fireEvent.click(screen.getByText(/osint\.drawer\.tabs\.problems/));
    expect(screen.getByText("osint.chain.your_action")).toBeInTheDocument();
    fireEvent.click(screen.getByText("osint.drawer.tabs.tech"));
    expect(screen.getByText(/KEV: CVE-2024-21762/)).toBeInTheDocument();
    expect(screen.getByText("osint.chain.cert_expired")).toBeInTheDocument();
    expect(screen.getByText("x-it.com")).toBeInTheDocument();
  });
});
