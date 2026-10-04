import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const gate = fileURLToPath(new URL('./npm-audit-gate.mjs', import.meta.url));
const metadata = { vulnerabilities: { high: 0, critical: 0 } };
for (const [name, report, auditExit, expected] of [
  ['reject registry failure', { error: { code: 'ENETUNREACH' } }, 1, 1],
  ['reject incomplete report', {}, 0, 1],
  ['accept successful audit', { vulnerabilities: {}, metadata }, 0, 0],
  ['reject high severity', { metadata, vulnerabilities: {
    sample: { severity: 'high', via: [{ severity: 'high', url: 'https://example.test/GHSA-example', title: 'synthetic' }] },
  } }, 1, 1],
]) {
  test(name, () => {
    const dir = mkdtempSync(join(tmpdir(), 'grc-audit-gate-'));
    try {
      writeFileSync(join(dir, 'npm'), `#!/bin/sh\ncat <<'AUDIT_REPORT'\n${JSON.stringify(report)}\nAUDIT_REPORT\nexit ${auditExit}\n`, { mode: 0o700 });
      const result = spawnSync(process.execPath, [gate], {
        encoding: 'utf8', env: { ...process.env, PATH: `${dir}:${process.env.PATH}` },
      });
      assert.equal(result.status, expected, result.stderr);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });
}
