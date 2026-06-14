/**
 * Sentry initialization for the govrico frontend.
 * Loaded once in main.tsx BEFORE React renders.
 *
 * Env vars (defined in .env / Docker):
 *   VITE_SENTRY_DSN                 — Sentry DSN (empty = Sentry disabled)
 *   VITE_SENTRY_ENVIRONMENT         — "development" | "staging" | "production"
 *   VITE_SENTRY_TRACES_RATE         — 0.0–1.0 (default 0.1)
 *   VITE_APP_VERSION                — release tag injected at build time
 *
 *   Session Replay (registra le sessioni utente → dato personale): DISATTIVATO
 *   di default per privacy-by-default (GDPR Art. 25). Va abilitato consapevolmente
 *   dal titolare, valutando base giuridica/consenso (vedi compliance/).
 *   VITE_SENTRY_REPLAY_ENABLED      — "true" per attivare il Session Replay
 *   VITE_SENTRY_REPLAY_SESSION_RATE — 0.0–1.0 (default 0.1, usato solo se abilitato)
 *   VITE_SENTRY_REPLAY_ERROR_RATE   — 0.0–1.0 (default 1.0, usato solo se abilitato)
 */
import * as Sentry from "@sentry/react";

const dsn = import.meta.env.VITE_SENTRY_DSN as string | undefined;

function rate(value: unknown, fallback: number): number {
  const n = parseFloat(value as string);
  return Number.isFinite(n) ? n : fallback;
}

export function initSentry(): void {
  if (!dsn) return;

  const replayEnabled =
    (import.meta.env.VITE_SENTRY_REPLAY_ENABLED as string) === "true";

  const integrations = [Sentry.browserTracingIntegration()];
  if (replayEnabled) {
    integrations.push(
      Sentry.replayIntegration({
        // GDPR: maschera tutto il testo, i campi input e i media
        maskAllText: true,
        blockAllMedia: true,
      })
    );
  }

  Sentry.init({
    dsn,
    environment: (import.meta.env.VITE_SENTRY_ENVIRONMENT as string) ?? "development",
    release: (import.meta.env.VITE_APP_VERSION as string) ?? "unknown",

    integrations,

    // Performance tracing
    tracesSampleRate: rate(import.meta.env.VITE_SENTRY_TRACES_RATE, 0.1),

    // Session Replay: solo se esplicitamente abilitato (vedi sopra).
    replaysSessionSampleRate: replayEnabled
      ? rate(import.meta.env.VITE_SENTRY_REPLAY_SESSION_RATE, 0.1)
      : 0,
    replaysOnErrorSampleRate: replayEnabled
      ? rate(import.meta.env.VITE_SENTRY_REPLAY_ERROR_RATE, 1.0)
      : 0,

    // GDPR: non allegare dati personali
    sendDefaultPii: false,

    beforeSend(event) {
      // Rimuovi Authorization header se presente
      if (event.request?.headers) {
        delete event.request.headers["Authorization"];
        delete event.request.headers["authorization"];
      }
      return event;
    },
  });
}
