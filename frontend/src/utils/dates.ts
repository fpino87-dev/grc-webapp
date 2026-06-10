import { useAuthStore } from "../store/auth";

/**
 * Utility date F3 (timezone per Plant).
 *
 * `new Date().toISOString()` produce la data UTC: la sera (es. 23:30 a Roma,
 * 21:30 UTC… o 00:30 con UTC ancora al giorno prima) i confronti
 * scaduto/in-scadenza sbagliano di un giorno. Qui "oggi" è calcolato nel fuso
 * IANA richiesto via Intl, senza dipendenze.
 */

/** "Oggi" (YYYY-MM-DD) nel fuso IANA indicato; senza argomento usa il fuso del browser. */
export function todayISO(timeZone?: string): string {
  try {
    return new Intl.DateTimeFormat("en-CA", {
      timeZone, year: "numeric", month: "2-digit", day: "2-digit",
    }).format(new Date());
  } catch {
    // timezone sconosciuto al browser: ripiega sul fuso locale
    return new Intl.DateTimeFormat("en-CA", {
      year: "numeric", month: "2-digit", day: "2-digit",
    }).format(new Date());
  }
}

/** Sposta una data YYYY-MM-DD di `days` giorni (aritmetica pura sulle date, niente DST). */
export function addDaysISO(iso: string, days: number): string {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d + days)).toISOString().slice(0, 10);
}

/** Sposta una data YYYY-MM-DD di `years` anni (29/02 → 28/02 quando serve). */
export function addYearsISO(iso: string, years: number): string {
  const [y, m, d] = iso.split("-").map(Number);
  const dt = new Date(Date.UTC(y + years, m - 1, d));
  if (dt.getUTCMonth() !== m - 1) dt.setUTCDate(0); // overflow di fine mese
  return dt.toISOString().slice(0, 10);
}

/** Hook: "oggi" nel fuso del sito selezionato (fallback: fuso del browser). */
export function usePlantToday(): string {
  const tz = useAuthStore(s => s.selectedPlant?.timezone);
  return todayISO(tz);
}

/** Adesso in formato per input datetime-local (YYYY-MM-DDTHH:mm), ora del browser. */
export function nowLocalForInput(): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
