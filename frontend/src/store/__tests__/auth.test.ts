/**
 * Test del persist middleware sull'auth store (newfix R1, aggiornato per #6).
 *
 * Dal newfix #6 il refresh token vive in un cookie httpOnly (mai nello store)
 * e l'access token resta SOLO in memoria: in localStorage devono persistere
 * esclusivamente user e selectedPlant. Se token o refresh finissero di nuovo
 * nello storage, un XSS tornerebbe a poter rubare la sessione.
 */
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { useAuthStore } from "../auth";

beforeEach(() => {
  localStorage.clear();
  useAuthStore.setState({
    user: null,
    token: null,
    selectedPlant: null,
  });
});

afterEach(() => {
  localStorage.clear();
});

describe("useAuthStore persist (newfix #6)", () => {
  it("setUser tiene il token in memoria e persiste solo lo user", () => {
    useAuthStore.getState().setUser(
      { id: "1", email: "x@x", role: "user", language: "it" },
      "access-token-1",
    );
    expect(useAuthStore.getState().token).toBe("access-token-1");

    const persisted = JSON.parse(localStorage.getItem("grc-auth") ?? "{}");
    expect(persisted.state.user.email).toBe("x@x");
    // Il token NON deve mai finire in localStorage (esposto a XSS)
    expect(persisted.state.token).toBeUndefined();
    expect(persisted.state.refresh).toBeUndefined();
  });

  it("setToken aggiorna il token in memoria senza persisterlo", () => {
    useAuthStore.getState().setUser(
      { id: "1", email: "x@x", role: "user", language: "it" },
      "old-access",
    );
    useAuthStore.getState().setToken("new-access");
    expect(useAuthStore.getState().token).toBe("new-access");

    const persisted = JSON.parse(localStorage.getItem("grc-auth") ?? "{}");
    expect(persisted.state.token).toBeUndefined();
  });

  it("selectedPlant viene persistito", () => {
    useAuthStore.getState().setPlant({ id: "p1", code: "PL1", name: "Plant 1" });
    const persisted = JSON.parse(localStorage.getItem("grc-auth") ?? "{}");
    expect(persisted.state.selectedPlant.code).toBe("PL1");
  });

  it("logout pulisce sia store che storage persistito", () => {
    useAuthStore.getState().setUser(
      { id: "1", email: "x@x", role: "user", language: "it" },
      "access",
    );
    useAuthStore.getState().logout();
    expect(useAuthStore.getState().token).toBeNull();
    expect(useAuthStore.getState().user).toBeNull();
    const persisted = JSON.parse(localStorage.getItem("grc-auth") ?? "{}");
    expect(persisted.state.user).toBeNull();
  });
});
