/**
 * Sentry initialization for GRC Frontend.
 * Loaded once in main.tsx BEFORE React renders.
 *
 * Env vars (defined in .env / Docker):
 *   VITE_SENTRY_DSN              — Sentry DSN (empty = Sentry disabled)
 *   VITE_SENTRY_ENVIRONMENT      — "development" | "staging" | "production"
 *   VITE_SENTRY_TRACES_RATE      — 0.0–1.0 (default 0.1)
 *   VITE_APP_VERSION             — release tag injected at build time
 */
import * as Sentry from "@sentry/react";

const dsn = import.meta.env.VITE_SENTRY_DSN as string | undefined;

export function initSentry(): void {
  if (!dsn) return;

  Sentry.init({
    dsn,
    environment: (import.meta.env.VITE_SENTRY_ENVIRONMENT as string) ?? "development",
    release: (import.meta.env.VITE_APP_VERSION as string) ?? "unknown",

    integrations: [
      Sentry.browserTracingIntegration(),
      Sentry.replayIntegration({
        // GDPR: maschera tutto il testo e i campi input
        maskAllText: true,
        blockAllMedia: true,
      }),
    ],

    // Performance tracing
    tracesSampleRate: parseFloat(
      (import.meta.env.VITE_SENTRY_TRACES_RATE as string) ?? "0.1"
    ),

    // Session Replay: 10% delle sessioni normali, 100% sugli errori
    replaysSessionSampleRate: 0.1,
    replaysOnErrorSampleRate: 1.0,

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
