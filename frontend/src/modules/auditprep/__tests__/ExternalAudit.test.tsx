import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
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
  plantsApi: {
    list: vi.fn(() => Promise.resolve([
      { id: "p1", code: "TA", name: "Plant TA" }, { id: "p2", code: "TB", name: "Plant TB" },
    ])),
    plantFrameworks: vi.fn(() => Promise.resolve([
      { framework: "fw1", framework_code: "TISAX_L2", framework_name: "TISAX AL2" },
    ])),
  },
}));
vi.mock("../../../api/endpoints/documents", () => ({
  documentsApi: { downloadEvidence: vi.fn() },
}));
vi.mock("../../../api/endpoints/auditPrep", () => ({
  auditPrepApi: {
    list: vi.fn(), programs: vi.fn(), findings: vi.fn(), evidence: vi.fn(), create: vi.fn(),
    update: vi.fn(), uploadReportFile: vi.fn(), detachReportFile: vi.fn(), downloadPrepReport: vi.fn(),
    downloadReportFile: vi.fn(), createGroup: vi.fn(), updateGroup: vi.fn(), createFinding: vi.fn(),
    updateFinding: vi.fn(), openPdca: vi.fn(), linkPdca: vi.fn(), unlinkPdca: vi.fn(), closeFinding: vi.fn(), closeWithPdca: vi.fn(), replacePdca: vi.fn(),
  },
}));

import { auditPrepApi } from "../../../api/endpoints/auditPrep";

const api = vi.mocked(auditPrepApi);

function prep(overrides = {}) {
  return {
    id: "a1", plant: "p1", framework: null, framework_code: null, title: "Audit cliente OEM",
    audit_date: "2026-09-10", auditor_name: "Ente Beta", status: "in_corso", readiness_score: null,
    owner: null, audit_program: null, audit_entry_id: "", coverage_type: "campione",
    audit_type: "seconda_parte", external_consultant: false, requesting_party: "OEM Alfa",
    report_evidence: null, report_evidence_title: null, report_evidence_filename: null,
    group: null, group_title: null, group_scope_id: null, group_sites: [],
    ...overrides,
  };
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}><MemoryRouter><AuditPrepPage /></MemoryRouter></QueryClientProvider>,
  );
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

const grouped = {
  group: "g1", group_title: "TISAX AL2 2026", group_scope_id: "S123",
  group_sites: [{ prep: "a1", plant: "p1", plant_code: "TA" }, { prep: "a2", plant: "p2", plant_code: "TB" }],
};

describe("Audit Prep — audit multi-sito", () => {
  it("crea un audit su più siti con framework comune e Scope ID", async () => {
    api.createGroup.mockResolvedValue({} as never);
    renderPage();
    fireEvent.click(await screen.findByText("audit_prep.tab_in_progress"));
    fireEvent.click(await screen.findByText("audit_prep.new_prep_btn"));
    fireEvent.click(screen.getByLabelText("audit_prep.group.multi_toggle"));
    fireEvent.click(await screen.findByLabelText("TA — Plant TA"));
    fireEvent.click(screen.getByLabelText("TB — Plant TB"));
    fireEvent.change(document.querySelector('input[name="title"]')!, { target: { value: "TISAX AL2 2026" } });
    fireEvent.change(screen.getByPlaceholderText("audit_prep.group.scope_id_placeholder"), { target: { value: "S123" } });
    // TISAX L2/L3 compaiono come unica voce "TISAX" con il livello (default L2)
    const fwSelect = (await screen.findByText("TISAX — VDA ISA 6.0")).closest("select")!;
    fireEvent.change(fwSelect, { target: { value: "TISAX" } });
    fireEvent.click(screen.getByText("audit_prep.create_prep_btn"));
    await vi.waitFor(() => expect(api.createGroup).toHaveBeenCalled());
    expect(api.createGroup.mock.calls[0][0]).toMatchObject({
      title: "TISAX AL2 2026", plants: ["p1", "p2"], framework: "fw1", scope_id: "S123",
    });
  });

  it("badge multi-sito, dati comuni salvati sul gruppo e rilievo comune", async () => {
    api.list.mockResolvedValue({ results: [prep(grouped)] } as never);
    api.updateGroup.mockResolvedValue({} as never);
    api.createFinding.mockResolvedValue({} as never);
    await openInfo();
    expect(screen.getAllByText("audit_prep.group.badge").length).toBeGreaterThan(0);
    expect(screen.getByText(/audit_prep\.group\.shared_hint/)).toBeInTheDocument();
    fireEvent.change(screen.getByDisplayValue("OEM Alfa"), { target: { value: "OEM Beta" } });
    fireEvent.click(screen.getByText("audit_prep.external.save_btn"));
    await vi.waitFor(() => expect(api.updateGroup).toHaveBeenCalledWith("g1",
      { audit_type: "seconda_parte", requesting_party: "OEM Beta", external_consultant: false }));
    expect(api.update).not.toHaveBeenCalled();

    fireEvent.click(screen.getByText(/audit_prep\.tab_findings/));
    fireEvent.click(await screen.findByText(/audit_prep\.add_finding/));
    const common = screen.getByLabelText("audit_prep.group.common_finding_label") as HTMLInputElement;
    fireEvent.click(common);
    expect(common.checked).toBe(true);
  });
});

function finding(overrides = {}) {
  return {
    id: "f1", audit_prep: "a1", finding_type: "observation", title: "Osservazione classificazione",
    description: "", auditor_name: "", audit_date: "2026-09-10", response_deadline: null, status: "open",
    root_cause: "", corrective_action: "", pdca_cycle: null, pdca_title: null, pdca_phase: null,
    common_key: null, is_overdue: false, auto_generated: false, control_external_id: null,
    ...overrides,
  };
}

async function openFindings() {
  renderPage();
  fireEvent.click(await screen.findByText("audit_prep.tab_in_progress"));
  fireEvent.click(await screen.findByText("audit_prep.open_btn"));
  fireEvent.click(await screen.findByText(/audit_prep\.tab_findings/));
}

describe("Audit Prep — finding e PDCA", () => {
  it("da un'osservazione si apre il PDCA collegato", async () => {
    api.findings.mockResolvedValue([finding()] as never);
    api.openPdca.mockResolvedValue(finding() as never);
    await openFindings();
    fireEvent.click(await screen.findByText("audit_prep.pdca_link.open"));
    await vi.waitFor(() => expect(api.openPdca).toHaveBeenCalledWith("f1"));
  });

  it("con PDCA collegato mostra la fase e la chiusura avvisa della regola", async () => {
    api.findings.mockResolvedValue([finding({ finding_type: "minor_nc", pdca_cycle: "c1", pdca_phase: "plan",
                                              pdca_title: "[MINOR_NC] x" })] as never);
    await openFindings();
    expect(await screen.findByText("audit_prep.pdca_link.linked")).toBeInTheDocument();
    expect(screen.queryByText("audit_prep.pdca_link.open")).not.toBeInTheDocument();
    fireEvent.click(screen.getByText("audit_prep.close_finding.btn"));
    expect(screen.getByText("audit_prep.close_finding.pdca_hint")).toBeInTheDocument();
    // NC: servono evidenza e note ≥ 20 caratteri prima di poter confermare
    expect(screen.getByText("audit_prep.close_finding.confirm")).toBeDisabled();
  });
});

describe("Audit Prep — seconda parte senza checklist", () => {
  it("la card mostra i rilievi al posto della prontezza e il dettaglio non ha il tab Checklist", async () => {
    api.findings.mockResolvedValue([finding(), finding({ id: "f2", finding_type: "minor_nc", status: "closed" })] as never);
    renderPage();
    fireEvent.click(await screen.findByText("audit_prep.tab_in_progress"));
    expect(await screen.findByText("audit_prep.second_party.summary")).toBeInTheDocument();
    expect(screen.getByText("audit_prep.second_party.report_missing")).toBeInTheDocument();
    fireEvent.click(screen.getByText("audit_prep.open_btn"));
    expect(await screen.findByText(/audit_prep\.tab_findings/)).toBeInTheDocument();
    expect(screen.queryByText("audit_prep.tab_checklist")).not.toBeInTheDocument();
  });

  it("un audit interno mantiene checklist e prontezza", async () => {
    api.list.mockResolvedValue({ results: [prep({ audit_type: "interno", requesting_party: "" })] } as never);
    renderPage();
    fireEvent.click(await screen.findByText("audit_prep.tab_in_progress"));
    fireEvent.click(await screen.findByText("audit_prep.open_btn"));
    expect(await screen.findByText("audit_prep.tab_checklist")).toBeInTheDocument();
    expect(screen.queryByText("audit_prep.second_party.summary")).not.toBeInTheDocument();
  });
});

describe("Audit Prep — collegamento a posteriori", () => {
  it("un finding chiuso senza PDCA si collega a un PDCA esistente ma non ne apre uno nuovo", async () => {
    api.findings.mockResolvedValue([finding({ status: "closed" })] as never);
    await openFindings();
    expect(await screen.findByText("audit_prep.pdca_link.link_existing")).toBeInTheDocument();
    expect(screen.queryByText("audit_prep.pdca_link.open")).not.toBeInTheDocument();
    expect(screen.queryByText("audit_prep.close_finding.btn")).not.toBeInTheDocument();
  });
});

describe("Audit Prep — chiudi con il PDCA", () => {
  it("un finding in risposta con PDCA chiuso si chiude con un clic", async () => {
    api.findings.mockResolvedValue([finding({ finding_type: "opportunity", status: "in_response",
                                              pdca_cycle: "c1", pdca_phase: "chiuso", pdca_title: "PDCA manuale" })] as never);
    api.closeWithPdca.mockResolvedValue(finding({ status: "closed" }) as never);
    await openFindings();
    fireEvent.click(await screen.findByText("audit_prep.pdca_link.close_with"));
    await vi.waitFor(() => expect(api.closeWithPdca).toHaveBeenCalledWith("f1"));
  });
});

async function openPrep() {
  renderPage();
  fireEvent.click(await screen.findByText("audit_prep.tab_in_progress"));
  fireEvent.click(await screen.findByText("audit_prep.open_btn"));
}

describe("Audit Prep — interno con consulente esterno, titolo, copertura", () => {
  it("l'audit interno del consulente esterno non ha checklist", async () => {
    api.list.mockResolvedValue({ results: [prep({ audit_type: "interno", external_consultant: true, requesting_party: "" })] } as never);
    await openPrep();
    expect((await screen.findAllByText("audit_prep.consultant.badge")).length).toBeGreaterThan(0);
    expect(screen.queryByText("audit_prep.tab_checklist")).not.toBeInTheDocument();
  });

  it("il flag si salva dal tab Info", async () => {
    api.list.mockResolvedValue({ results: [prep({ audit_type: "interno", requesting_party: "" })] } as never);
    api.update.mockResolvedValue({} as never);
    await openInfo();
    fireEvent.click(screen.getByLabelText(/audit_prep\.consultant\.flag_label/));
    fireEvent.click(screen.getByText("audit_prep.external.save_btn"));
    await vi.waitFor(() => expect(api.update).toHaveBeenCalledWith("a1",
      { audit_type: "interno", requesting_party: "", external_consultant: true }));
  });

  it("il titolo si modifica; nel multi-sito sull'audit comune", async () => {
    api.update.mockResolvedValue({} as never);
    await openPrep();
    fireEvent.click(await screen.findByLabelText("audit_prep.title_edit.btn"));
    fireEvent.change(screen.getByLabelText("audit_prep.title_label"), { target: { value: "Nuovo titolo" } });
    fireEvent.click(screen.getByText("audit_prep.external.save_btn"));
    await vi.waitFor(() => expect(api.update).toHaveBeenCalledWith("a1", { title: "Nuovo titolo" }));
  });

  it("titolo di un audit multi-sito → updateGroup", async () => {
    api.list.mockResolvedValue({ results: [prep(grouped)] } as never);
    api.updateGroup.mockResolvedValue({} as never);
    await openPrep();
    fireEvent.click(await screen.findByLabelText("audit_prep.title_edit.btn"));
    expect(screen.getByLabelText("audit_prep.title_label")).toHaveValue("TISAX AL2 2026");
    fireEvent.change(screen.getByLabelText("audit_prep.title_label"), { target: { value: "TISAX rinnovo" } });
    fireEvent.click(screen.getByText("audit_prep.external.save_btn"));
    await vi.waitFor(() => expect(api.updateGroup).toHaveBeenCalledWith("g1", { title: "TISAX rinnovo" }));
  });

  it("la copertura compare solo per gli audit del programma", async () => {
    api.list.mockResolvedValue({ results: [prep({ audit_type: "interno", coverage_type: "full" })] } as never);
    await openPrep();
    await screen.findByLabelText("audit_prep.title_edit.btn");
    expect(screen.queryByText(/audit_prep\.coverage_full/)).not.toBeInTheDocument();
  });

  it("audit del programma: la copertura resta", async () => {
    api.list.mockResolvedValue({ results: [prep({ audit_type: "interno", audit_program: "pr1" })] } as never);
    await openPrep();
    expect(await screen.findByText(/audit_prep\.coverage_campione/)).toBeInTheDocument();
  });
});

describe("Audit Prep — correzione del finding", () => {
  it("titolo e descrizione si modificano dopo il salvataggio", async () => {
    api.findings.mockResolvedValue([{
      id: "f1", audit_prep: "a1", finding_type: "observation", title: "Titlo", description: "Descrizone",
      auditor_name: "", audit_date: "2026-09-10", response_deadline: null, status: "open", root_cause: "",
      corrective_action: "", pdca_cycle: null, common_key: null, pdca_title: null, pdca_phase: null,
      pdca_is_org: false, closure_notes: "", closed_at: null, closed_by_name: null,
      is_overdue: false, auto_generated: false, control_external_id: null,
    }] as never);
    api.updateFinding.mockResolvedValue({} as never);
    await openPrep();
    fireEvent.click(await screen.findByText(/audit_prep\.finding_edit\.btn/));
    fireEvent.change(screen.getByLabelText("audit_prep.title_label"), { target: { value: "Titolo" } });
    fireEvent.change(screen.getByLabelText("audit_prep.description_label"), { target: { value: "Descrizione" } });
    fireEvent.click(screen.getByText("audit_prep.external.save_btn"));
    await vi.waitFor(() => expect(api.updateFinding).toHaveBeenCalledWith("f1", { title: "Titolo", description: "Descrizione" }));
  });
});
