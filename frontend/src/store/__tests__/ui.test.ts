/**
 * Test preferenze UI per dispositivo: sidebar collassabile e scala
 * interfaccia con memoria per monitor (firma = risoluzione × pixel ratio).
 */
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { SCALE_MAX, SCALE_MIN, screenSignature, useUiStore } from "../ui";

beforeEach(() => {
  localStorage.clear();
  document.documentElement.style.fontSize = "";
  useUiStore.setState({
    sidebarCollapsed: false,
    scaleByScreen: {},
    signature: screenSignature(),
  });
});

afterEach(() => {
  localStorage.clear();
  document.documentElement.style.fontSize = "";
});

describe("useUiStore — sidebar", () => {
  it("toggleSidebar inverte e persiste lo stato", () => {
    useUiStore.getState().toggleSidebar();
    expect(useUiStore.getState().sidebarCollapsed).toBe(true);

    const persisted = JSON.parse(localStorage.getItem("grc-ui") ?? "{}");
    expect(persisted.state.sidebarCollapsed).toBe(true);
  });
});

describe("useUiStore — scala per monitor", () => {
  it("changeScale applica il font-size alla root e salva per firma schermo", () => {
    useUiStore.getState().changeScale(+0.1);
    expect(document.documentElement.style.fontSize).toBe("17.6px"); // 16 × 1.1

    const persisted = JSON.parse(localStorage.getItem("grc-ui") ?? "{}");
    expect(persisted.state.scaleByScreen[screenSignature()]).toBe(1.1);
  });

  it("la scala è clampata tra SCALE_MIN e SCALE_MAX", () => {
    for (let i = 0; i < 20; i++) useUiStore.getState().changeScale(+0.1);
    expect(useUiStore.getState().currentScale()).toBe(SCALE_MAX);

    for (let i = 0; i < 20; i++) useUiStore.getState().changeScale(-0.1);
    expect(useUiStore.getState().currentScale()).toBe(SCALE_MIN);
  });

  it("monitor diversi ricordano scale diverse", () => {
    // Schermo A: scala 1.2
    useUiStore.setState({ signature: "1920x1200@1.5" });
    useUiStore.getState().changeScale(+0.1);
    useUiStore.getState().changeScale(+0.1);

    // Schermo B: scala 0.9
    useUiStore.setState({ signature: "2560x1440@1" });
    useUiStore.getState().changeScale(-0.1);

    const map = useUiStore.getState().scaleByScreen;
    expect(map["1920x1200@1.5"]).toBe(1.2);
    expect(map["2560x1440@1"]).toBe(0.9);

    // Tornando sullo schermo A la scala è quella sua
    useUiStore.setState({ signature: "1920x1200@1.5" });
    expect(useUiStore.getState().currentScale()).toBe(1.2);
  });

  it("resetScale riporta al 100% solo lo schermo corrente", () => {
    useUiStore.setState({ signature: "A" });
    useUiStore.getState().changeScale(+0.2);
    useUiStore.setState({ signature: "B" });
    useUiStore.getState().changeScale(+0.3);

    useUiStore.getState().resetScale(); // su B
    expect(useUiStore.getState().scaleByScreen["B"]).toBe(1);
    expect(useUiStore.getState().scaleByScreen["A"]).toBe(1.2);
    expect(document.documentElement.style.fontSize).toBe("16px");
  });

  it("la firma non viene persistita (ricalcolata a ogni avvio)", () => {
    useUiStore.getState().changeScale(+0.1);
    const persisted = JSON.parse(localStorage.getItem("grc-ui") ?? "{}");
    expect(persisted.state.signature).toBeUndefined();
  });
});
