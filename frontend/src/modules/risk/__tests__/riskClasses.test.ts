import { describe, it, expect } from "vitest";
import { riskClass, classRank } from "../riskClasses";
import { overallImpact, previewClass } from "../RiskUi";

// Stessa tabella del test backend (apps/risk/tests/test_methodology.py):
// la classe del frontend deve coincidere con risk.services.risk_class.
const EXPECTED: Record<number, string[]> = {
  5: ["medium", "high", "high", "critical", "critical"],
  4: ["low", "medium", "high", "critical", "critical"],
  3: ["low", "medium", "medium", "high", "critical"],
  2: ["very_low", "low", "medium", "high", "high"],
  1: ["very_low", "low", "low", "medium", "high"],
};

describe("matrice della procedura", () => {
  it("coincide con il backend cella per cella", () => {
    for (const [p, row] of Object.entries(EXPECTED)) {
      row.forEach((cls, idx) => expect(riskClass(Number(p), idx + 1)).toBe(cls));
    }
  });

  it("non usa il prodotto P × I", () => {
    expect(riskClass(5, 3)).toBe("high");
    expect(riskClass(1, 5)).toBe("high");
  });

  it("valori mancanti → nessuna classe", () => {
    expect(riskClass(null, 3)).toBeNull();
    expect(classRank("")).toBe(-1);
  });

  it("impatto = caso peggiore, override di un livello nei limiti", () => {
    expect(overallImpact({ economic: 2, legal: 4, operational: null })).toBe(4);
    expect(overallImpact({})).toBeNull();
    expect(previewClass(3, 3, 1)).toBe("high");
    expect(previewClass(5, 5, 1)).toBe("critical");
    expect(previewClass(1, 1, -1)).toBe("very_low");
  });
});
