/**
 * Guardia sul debito i18n (regola #14 di CLAUDE.md).
 *
 * Due invarianti che in passato si erano rotti in silenzio: i file di lingua
 * andati fuori sincrono fra loro (43 chiavi presenti solo in IT, 56 chiavi
 * morte rimaste in FR/PL/TR) e chiavi usate da t() ma mai tradotte, che in UI
 * comparivano come stringa grezza.
 *
 * Usa le primitive Vite (import JSON + import.meta.glob) invece di node:fs
 * per non introdurre @types/node fra le dipendenze del frontend.
 */
import { describe, expect, it } from "vitest";

import en from "../en/common.json";
import fr from "../fr/common.json";
import it_ from "../it/common.json";
import pl from "../pl/common.json";
import tr from "../tr/common.json";

const CATALOGS = { it: it_, en, fr, pl, tr } as const;
type Lang = keyof typeof CATALOGS;
const OTHERS: Lang[] = ["en", "fr", "pl", "tr"];

function flatten(obj: unknown, prefix = ""): string[] {
  if (typeof obj !== "object" || obj === null) return [];
  return Object.entries(obj as Record<string, unknown>).flatMap(([k, v]) =>
    typeof v === "object" && v !== null
      ? flatten(v, `${prefix}${k}.`)
      : [`${prefix}${k}`],
  );
}

const keys = Object.fromEntries(
  (Object.keys(CATALOGS) as Lang[]).map((l) => [l, new Set(flatten(CATALOGS[l]))]),
) as Record<Lang, Set<string>>;

describe("i18n", () => {
  it.each(OTHERS)("%s ha esattamente le stesse chiavi di it", (lang) => {
    const missing = [...keys.it].filter((k) => !keys[lang].has(k)).sort();
    const extra = [...keys[lang]].filter((k) => !keys.it.has(k)).sort();
    expect({ missing, extra }).toEqual({ missing: [], extra: [] });
  });

  it('ogni chiave t("...") statica esiste nelle traduzioni', () => {
    const sources = import.meta.glob("../../**/*.{ts,tsx}", {
      query: "?raw",
      import: "default",
      eager: true,
    }) as Record<string, string>;
    // Il lookbehind evita i falsi positivi da funzioni che finiscono per "t"
    // (parseInt(", .at(", format(") e dalle chiamate del tipo obj.t(").
    const CALL = /(?<![A-Za-z0-9_$.])t\(\s*"([a-zA-Z0-9_.]+)"/g;
    const unresolved = new Set<string>();
    for (const [path, text] of Object.entries(sources)) {
      if (path.includes("/i18n/")) continue;
      for (const m of text.matchAll(CALL)) {
        if (!keys.it.has(m[1])) unresolved.add(m[1]);
      }
    }
    expect([...unresolved].sort()).toEqual([]);
  });
});
