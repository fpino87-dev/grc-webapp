import { describe, it, expect, vi, afterEach } from "vitest";
import { addDaysISO, addYearsISO, todayISO, nowLocalForInput } from "../dates";

// 2026-06-10 23:30 UTC: a Roma (UTC+2) è già l'11 giugno,
// a New York (UTC-4) ancora il 10 — il caso dell'off-by-one serale.
const FROZEN = new Date("2026-06-10T23:30:00Z");

afterEach(() => {
  vi.useRealTimers();
});

describe("todayISO", () => {
  it("usa la mezzanotte del fuso richiesto, non quella UTC", () => {
    vi.useFakeTimers();
    vi.setSystemTime(FROZEN);
    expect(todayISO("Europe/Rome")).toBe("2026-06-11");
    expect(todayISO("America/New_York")).toBe("2026-06-10");
  });

  it("ripiega sul fuso del browser se il timezone non è valido", () => {
    vi.useFakeTimers();
    vi.setSystemTime(FROZEN);
    expect(todayISO("Mars/Olympus_Mons")).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });
});

describe("addDaysISO / addYearsISO", () => {
  it("somma giorni in puro spazio date (cambio mese/anno)", () => {
    expect(addDaysISO("2026-06-10", 30)).toBe("2026-07-10");
    expect(addDaysISO("2026-12-31", 1)).toBe("2027-01-01");
    expect(addDaysISO("2026-03-01", -1)).toBe("2026-02-28");
  });

  it("somma anni gestendo il 29 febbraio", () => {
    expect(addYearsISO("2026-06-10", 1)).toBe("2027-06-10");
    expect(addYearsISO("2024-02-29", 1)).toBe("2025-02-28");
  });
});

describe("nowLocalForInput", () => {
  it("produce il formato datetime-local YYYY-MM-DDTHH:mm", () => {
    expect(nowLocalForInput()).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/);
  });
});
