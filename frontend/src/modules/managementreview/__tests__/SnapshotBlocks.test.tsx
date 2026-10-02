import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ObjectivesBlock, RisksBlock, SitesBlock } from "../SnapshotBlocks";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (k: string, o?: unknown) => (typeof o === "string" ? o : k), i18n: { language: "it" } }),
  initReactI18next: { type: "3rdParty", init: () => undefined },
}));

// Struttura reale dello snapshot (metodo "classi") generata dal backend.
const snap = {
  rischi: {
    metodo: "classi", oltre_soglia: 1, rosso: 2, giallo: 1, verde: 0,
    by_class: { very_low: 0, low: 0, medium: 1, high: 1, critical: 1 },
    senza_piano: 0, senza_owner: 0, accettati_formalmente: 1, misure_in_ritardo: 1, valutazioni: [],
    top_critici: [{ id: "r1", name: "Malware e ransomware", threat: "IN_MAL", asset: null, process: null,
      current_class: "critical", expected_class: "high", treatment: "mitigare", owner: "Mario", has_plan: true }],
    elenco_accettati: [{ id: "r2", name: "Incendio", current_class: "high", signatures: [], body: null, acceptance_expiry: "2026-10-22" }],
    per_obiettivo: [
      { name: "Continuity of supply to OEM customers", count: 3, worst_class: "critical", untreated_high: 1, ereditati: 1 },
      { name: "Financial result", count: 0, worst_class: "", untreated_high: 0 },
      { name: null, count: 0, worst_class: "", untreated_high: 0 },
    ],
    ereditati_gruppo: { count: 1, untreated_high: 1,
      elenco: [{ name: "Accesso non autorizzato", current_class: "critical", treatment: "mitigare", accettato: false }] },
  },
  compliance_rule: 3,
  siti: [
    { plant_id: "p1", code: "IT-CH-01", name: "Chivasso", pct_compliant: 80, rischi_critici: 1, rischi_oltre_soglia: 1,
      rischi_ereditati_gruppo: 1, incidenti_aperti: 0, task_scaduti: 2 },
    { plant_id: null, code: "GRUPPO", name: null, is_group: true, pct_compliant: null, rischi_critici: 1,
      rischi_oltre_soglia: 1, rischi_ereditati_gruppo: null, incidenti_aperti: null, task_scaduti: null },
  ],
  obiettivi: {
    totale: 1, attivi: 1, a_rischio: 0, mancati: 0, raggiunti: 0,
    elenco: [{ id: "o1", code: "OBJ-VER", title: "Test di ripristino MES", plant_code: "IT-CH-01", owner_role: "",
      status: "attivo", baseline_value: 0, target_value: 100, target_date: "2026-12-31", current_value: null,
      unit: "%", progress_pct: null, track: "senza_misure",
      rischi: [{ name: "Malware e ransomware", current_class: "critical", obiettivi_aziendali: ["Continuity of supply to OEM customers"] }] }],
  },
};

describe("Snapshot del riesame con la nuova metodologia", () => {
  it("mostra i rischi per obiettivo aziendale", () => {
    render(<RisksBlock snap={snap as never} />);
    expect(screen.getByText("management_review.snap.risks_by_objective")).toBeTruthy();
    expect(screen.getAllByText("Continuity of supply to OEM customers").length).toBeGreaterThan(0);
    expect(screen.getByText("Financial result")).toBeTruthy(); // anche senza rischi: segnale per il riesame
    expect(screen.queryByText("risk.objectives.none")).toBeNull(); // nessun rischio senza obiettivo
    expect(screen.getAllByText("Malware e ransomware").length).toBeGreaterThan(0);
  });

  it("elenca a parte i rischi di gruppo del sito e la riga del gruppo nel quadro per sito", () => {
    render(<RisksBlock snap={snap as never} />);
    expect(screen.getByText("management_review.snap.inherited_title")).toBeTruthy();
    expect(screen.getByText("Accesso non autorizzato")).toBeTruthy();
    render(<SitesBlock snap={snap as never} />);
    expect(screen.getByText("management_review.snap.group_row")).toBeTruthy();
    expect(screen.getAllByText("management_review.snap.col_from_group").length).toBe(2); // per obiettivo e per sito
  });

  it("mostra la catena obiettivo di sicurezza ← rischio ← obiettivo aziendale", () => {
    render(<ObjectivesBlock snap={snap as never} />);
    expect(screen.getByText(/Malware e ransomware \(critical\) ← Continuity of supply to OEM customers/)).toBeTruthy();
  });
});
