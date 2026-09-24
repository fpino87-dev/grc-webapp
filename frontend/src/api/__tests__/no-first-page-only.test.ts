import { describe, it, expect } from "vitest";

/**
 * Guardia contro gli elenchi troncati a 25: il backend pagina (PAGE_SIZE 25)
 * e un `apiClient.get<{ results: … }>` letto una volta sola mostra solo la
 * prima pagina. Gli elenchi completi passano da `fetchAllPages`; qui sono
 * ammesse solo le eccezioni motivate (endpoint non paginati o pagina esplicita).
 */
const ALLOWED = [
  "/audit-trail/audit-logs/",           // paginazione esplicita nella pagina (migliaia di eventi)
  "/controls/frameworks/governance/",   // azione custom, non paginata
  "/schedule/activity/",                // azione custom con campi extra
  "/schedule/framework-controls/",      // azione custom, non paginata
  "/reporting/kpi-trend/",              // azione custom con campi extra
  "/nda/",                              // azione custom fornitori, non paginata
  "/internal-evaluation/history/",      // azione custom fornitori, non paginata
  "/incidents/nis2-configurations/",    // legge la configurazione del sito (1 record)
  "/incidents/rca/",                    // una RCA per incidente: si legge il primo record
];

// Sorgenti dei client API (Vite: contenuto testuale dei file).
const SOURCES = import.meta.glob("../endpoints/*.ts", { query: "?raw", import: "default", eager: true }) as Record<string, string>;

describe("elenchi API", () => {
  it("nessun elenco paginato letto solo alla prima pagina", () => {
    const offenders: string[] = [];
    expect(Object.keys(SOURCES).length).toBeGreaterThan(20);
    for (const [file, src] of Object.entries(SOURCES)) {
      const re = /apiClient\s*\.get<\s*\{\s*results\s*[?]?:[^>]*>\(\s*([^,)]+)/g;
      for (const m of src.matchAll(re)) {
        const url = m[1];
        if (!ALLOWED.some(a => url.includes(a))) offenders.push(`${file}: ${url.trim()}`);
      }
    }
    expect(offenders).toEqual([]);
  });
});
