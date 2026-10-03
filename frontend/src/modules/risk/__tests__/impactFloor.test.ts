import { describe, it, expect } from "vitest";
import { impactFloor, previewClass } from "../RiskUi";
import { riskClass } from "../riskClasses";

describe("soglia di riservatezza nell'anteprima", () => {
  it("vale solo per minacce alla riservatezza con informazioni classificate", () => {
    expect(impactFloor(["C", "I"], ["normal", "very_high"])).toBe(5);
    expect(impactFloor(["A"], ["very_high"])).toBeNull();
    expect(impactFloor(["C"], [])).toBeNull();
    expect(impactFloor(undefined, ["high"])).toBeNull();
  });

  it("il rischio atteso non scende sotto la soglia (come il backend)", () => {
    expect(previewClass(2, 3)).toBe(riskClass(2, 3));
    expect(previewClass(2, 3, 0, 5)).toBe(riskClass(2, 5));
    expect(previewClass(2, 5, 0, 5)).toBe(riskClass(2, 5));
    expect(previewClass(2, null, 0, 5)).toBeNull();
  });

  it("l'override non porta la classe sotto quella della soglia", () => {
    expect(previewClass(2, 5, -1, 5)).toBe(riskClass(2, 5));
    expect(previewClass(2, 5, -1)).not.toBe(riskClass(2, 5));
  });
});
