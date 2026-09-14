import { describe, it, expect, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import i18n from "../../../i18n";
import { useEvaluationLabels } from "../evaluationLabels";

const DEFAULT_IMPATTO = {
  name: "Impatto business",
  levels: ["Nessuno", "Minimo", "Degrado", "Interruzione", "Blocco"],
};

afterEach(async () => {
  await act(() => i18n.changeLanguage("it"));
});

describe("useEvaluationLabels", () => {
  it("traduce nome e livelli ancora uguali ai default italiani", async () => {
    await act(() => i18n.changeLanguage("en"));
    const { result } = renderHook(() => useEvaluationLabels());
    expect(result.current.paramName("impatto", DEFAULT_IMPATTO)).toBe("Business impact");
    expect(result.current.levelLabel("impatto", DEFAULT_IMPATTO, 4)).toBe("Disruption");
  });

  it("mostra così come sono le etichette personalizzate dall'amministratore", async () => {
    await act(() => i18n.changeLanguage("en"));
    const custom = { name: "Impatto sul business OEM", levels: ["A", "B", "C", "D", "E"] };
    const { result } = renderHook(() => useEvaluationLabels());
    expect(result.current.paramName("impatto", custom)).toBe("Impatto sul business OEM");
    expect(result.current.levelLabel("impatto", custom, 2)).toBe("B");
  });

  it("in italiano restituisce i testi originali e gestisce le etichette mancanti", () => {
    const { result } = renderHook(() => useEvaluationLabels());
    expect(result.current.paramName("impatto", DEFAULT_IMPATTO)).toBe("Impatto business");
    expect(result.current.paramName("impatto", undefined)).toBe("impatto");
    expect(result.current.levelLabel("impatto", undefined, 1)).toBeUndefined();
  });
});
