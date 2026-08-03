#!/usr/bin/env node
// Gate `npm audit` per le dipendenze di produzione del frontend.
//
// Fallisce (exit 1) su qualunque vulnerabilita' high/critical, TRANNE gli
// advisory esplicitamente esentati qui sotto con giustificazione. npm audit non
// supporta nativamente un allowlist, quindi filtriamo il suo output JSON.
//
// Va eseguito con cwd = frontend/ (dove sta package-lock.json).
import { execSync } from "node:child_process";

// Advisory ignorati, con motivazione e condizione di rimozione.
const IGNORED = new Map([
  [
    "GHSA-qwww-vcr4-c8h2",
    // React Router: RSC Mode CSRF Bypass. L'advisory riguarda ESCLUSIVAMENTE le
    // "unstable RSC APIs" (React Server Components). Questa app e' una SPA Vite
    // client-side che usa react-router-dom per il routing lato client: non usa
    // RSC, quindi non e' esposta. Nessuna patch nella serie 7.x (fix solo in
    // react-router 8.3.0, e react-router-dom non ha una major 8.x). Rimuovere
    // alla migrazione a React Router v8.
    "react-router RSC CSRF: non applicabile (nessun uso di RSC); patch solo in v8",
  ],
]);

const SEVERITIES = new Set(["high", "critical"]);

function runAudit() {
  try {
    return execSync("npm audit --omit=dev --json", {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    });
  } catch (err) {
    // npm audit esce con codice != 0 quando trova vulnerabilita': lo stdout
    // resta un JSON valido e va usato comunque.
    if (err.stdout) return err.stdout.toString();
    throw err;
  }
}

const report = JSON.parse(runAudit());
const vulns = report.vulnerabilities ?? {};

const blocking = [];
const usedExceptions = new Set();

for (const [pkg, info] of Object.entries(vulns)) {
  if (!SEVERITIES.has(info.severity)) continue;
  for (const via of info.via ?? []) {
    // via stringa = introdotta da un altro pacchetto (transitiva): l'advisory
    // vero e' contabilizzato sul pacchetto sorgente, qui si salta.
    if (typeof via !== "object") continue;
    if (!SEVERITIES.has(via.severity)) continue;
    const id = String(via.url ?? "").split("/").pop();
    if (IGNORED.has(id)) {
      usedExceptions.add(id);
      continue;
    }
    blocking.push({ pkg, id, severity: via.severity, title: via.title });
  }
}

if (blocking.length > 0) {
  console.error("npm audit: vulnerabilita' high/critical NON coperte da eccezioni:");
  for (const b of blocking) {
    console.error(`  - [${b.severity}] ${b.pkg}: ${b.id} — ${b.title}`);
  }
  console.error("\nValutare l'upgrade della dipendenza o, se non applicabile, aggiungere");
  console.error("un'eccezione documentata in .github/scripts/npm-audit-gate.mjs.");
  process.exit(1);
}

const exempt = [...usedExceptions];
console.log(
  exempt.length > 0
    ? `npm audit OK: nessuna high/critical oltre alle eccezioni documentate (${exempt.join(", ")}).`
    : "npm audit OK: nessuna vulnerabilita' high/critical.",
);
