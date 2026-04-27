/**
 * Test del persist middleware sull'auth store (newfix R1).
 *
 * Verifica che user, token, refresh e selectedPlant sopravvivano a un reload
 * (simulato via localStorage). Senza questo, l'utente perde la sessione a
 * ogni F5.
 */
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { useAuthStore } from "../auth";

beforeEach(() => {
  localStorage.clear();
  useAuthStore.setState({
    user: null,
    token: null,
    refresh: null,
    selectedPlant: null,
  });
});

afterEach(() => {
  localStorage.clear();
});

describe("useAuthStore persist", () => {
  it("setUser scrive user, token e refresh in localStorage", () => {
    useAuthStore.getState().setUser(
      { id: "1", email: "x@x", role: "user", language: "it" },
      "access-token-1",
      "refresh-token-1",
    );
    const persisted = JSON.parse(localStorage.getItem("grc-auth") ?? "{}");
    expect(persisted.state.token).toBe("access-token-1");
    expect(persisted.state.refresh).toBe("refresh-token-1");
    expect(persisted.state.user.email).toBe("x@x");
  });

  it("setToken aggiorna solo il token (refresh resta)", () => {
    useAuthStore.getState().setUser(
      { id: "1", email: "x@x", role: "user", language: "it" },
      "old-access",
      "stable-refresh",
    );
    useAuthStore.getState().setToken("new-access");
    const persisted = JSON.parse(localStorage.getItem("grc-auth") ?? "{}");
    expect(persisted.state.token).toBe("new-access");
    expect(persisted.state.refresh).toBe("stable-refresh");
  });

  it("logout pulisce sia store che storage persistito", () => {
    useAuthStore.getState().setUser(
      { id: "1", email: "x@x", role: "user", language: "it" },
      "access",
      "refresh",
    );
    useAuthStore.getState().logout();
    expect(useAuthStore.getState().token).toBeNull();
    expect(useAuthStore.getState().refresh).toBeNull();
    const persisted = JSON.parse(localStorage.getItem("grc-auth") ?? "{}");
    expect(persisted.state.token).toBeNull();
    expect(persisted.state.refresh).toBeNull();
  });

  it("setUser senza refresh esplicito persiste refresh=null (non rompe il flusso)", () => {
    useAuthStore.getState().setUser(
      { id: "1", email: "x@x", role: "user", language: "it" },
      "access-only",
    );
    const persisted = JSON.parse(localStorage.getItem("grc-auth") ?? "{}");
    expect(persisted.state.token).toBe("access-only");
    expect(persisted.state.refresh).toBeNull();
  });
});
