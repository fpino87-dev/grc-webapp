import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuditPrepPage } from "../AuditPrepPage";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (k: string) => k, i18n: { language: "it" } }),
}));
vi.mock("../../../i18n", () => ({ default: { language: "it", t: (k: string) => k } }));
vi.mock("../../../components/ui/ModuleHelp", () => ({ ModuleHelp: () => null }));
vi.mock("../../../api/client", () => ({
  apiClient: { get: vi.fn(() => Promise.resolve({ data: { results: [] } })), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));
vi.mock("../../../api/endpoints/plants", () => ({
  plantsApi: { list: vi.fn(() => Promise.resolve([])), plantFrameworks: vi.fn(() => Promise.resolve([])) },
}));
vi.mock("../../../api/endpoints/documents", () => ({
  documentsApi: { downloadEvidence: vi.fn() },
}));
vi.mock("../../../api/endpoints/auditPrep", () => ({
  auditPrepApi: {
    list: vi.fn(), programs: vi.fn(), findings: vi.fn(), evidence: vi.fn(), create: vi.fn(),
    update: vi.fn(), uploadReportFile: vi.fn(), detachReportFile: vi.fn(), downloadPrepReport: vi.fn(),
  },
}));

import { auditPrepApi } from "../../../api/endpoints/auditPrep";

const api = vi.mocked(auditPrepApi);

function prep(overrides = {}) {
  return {
    id: "a1", plant: "p1", framework: null, framework_code: null, title: "Audit cliente OEM",
    audit_date: "2026-09-10", auditor_name: "Ente Beta", status: "in_corso", readiness_score: null,
    owner: null, audit_program: null, audit_entry_id: "", coverage_type: "campione",
    audit_type: "seconda_parte", requesting_party: "OEM Alfa",
    report_evidence: null, report_evidence_title: null, report_evidence_filename: null,
    ...overrides,
  };
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}><AuditPrepPage /></QueryClientProvider>);
}

beforeEach(() => {
  vi.clearAllMocks();
  api.list.mockResolvedValue({ results: [prep()] } as never);
  api.programs.mockResolvedValue({ results: [] } as never);
  api.findings.mockResolvedValue([] as never);
  api.evidence.mockResolvedValue([] as never);
  api.uploadReportFile.mockResolvedValue(prep() as never);
});

async function openInfo() {
  renderPage();
  fireEvent.click(await screen.findByText("audit_prep.tab_in_progress"));
  fireEvent.click(await screen.findByText("audit_prep.open_btn"));
  fireEvent.click(await screen.findByText("audit_prep.tab_info"));
}

describe("Audit Prep — audit di seconda parte", () => {
  it("la card mostra tipo e committente", async () => {
    renderPage();
    fireEvent.click(await screen.findByText("audit_prep.tab_in_progress"));
    expect(await screen.findByText(/audit_prep\.audit_type\.seconda_parte — OEM Alfa/)).toBeInTheDocument();
  });

  it("dal tab Info si allega il rapporto ufficiale", async () => {
    await openInfo();
    expect(screen.getByText("audit_prep.external.no_report")).toBeInTheDocument();
    const file = new File(["%PDF-1.4"], "rapporto.pdf", { type: "application/pdf" });
    fireEvent.change(screen.getByLabelText("audit_prep.external.file_label"), { target: { files: [file] } });
    fireEvent.click(screen.getByText("audit_prep.external.upload_btn"));
    await vi.waitFor(() => expect(api.uploadReportFile).toHaveBeenCalledWith("a1", file, undefined));
  });

  it("con un rapporto allegato si può scaricare, sostituire o scollegare", async () => {
    api.list.mockResolvedValue({ results: [prep({ report_evidence: "e1", report_evidence_title: "Rapporto OEM",
                                                   report_evidence_filename: "rapporto.pdf" })] } as never);
    await openInfo();
    expect(screen.getByText(/Rapporto OEM/)).toBeInTheDocument();
    expect(screen.getByText("audit_prep.external.replace_btn")).toBeInTheDocument();
    fireEvent.click(screen.getByText("audit_prep.external.detach_btn"));
    await vi.waitFor(() => expect(api.detachReportFile).toHaveBeenCalledWith("a1"));
  });
});
