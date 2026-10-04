// Bake only explicit API/Sentry origins into CSP. Never emit DSN credentials.
import { readFileSync, writeFileSync } from 'node:fs';
const origins = new Set(["'self'"]);
for (const value of [process.env.VITE_API_URL, process.env.VITE_SENTRY_DSN]) {
  if (!value) continue;
  const url = new URL(value);
  if (url.protocol !== 'https:') throw new Error('Production external origins must use HTTPS');
  origins.add(url.origin);
}
let config = readFileSync('nginx.conf', 'utf8');
config = config.replace("connect-src 'self'", `connect-src ${[...origins].join(' ')}`);
if (process.env.VITE_SENTRY_REPLAY_ENABLED === 'true') {
  config = config.replace("worker-src 'none'", "worker-src 'self' blob:");
}
writeFileSync('/tmp/grc-nginx.conf', config);
