// Lint frontend (newfix 2026-06-09 #8). Baseline pragmatica:
// recommended JS/TS + regole React hooks. `no-explicit-any` resta off:
// attivarlo sul codice esistente produce centinaia di errori — valutare
// in un passaggio dedicato di tipizzazione.
import js from "@eslint/js";
import tseslint from "typescript-eslint";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";

export default tseslint.config(
  { ignores: ["dist", "node_modules", "coverage"] },
  {
    files: ["src/**/*.{ts,tsx}"],
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    languageOptions: {
      globals: { ...globals.browser },
    },
    plugins: { "react-hooks": reactHooks },
    rules: {
      ...reactHooks.configs.recommended.rules,
      // Regole compiler-based di react-hooks v6: segnalano pattern legacy
      // diffusi nel codice esistente (setState in effect di sync, ref in
      // render). Baseline a warn — da portare a error modulo per modulo.
      "react-hooks/set-state-in-effect": "warn",
      "react-hooks/refs": "warn",
      "react-hooks/purity": "warn",
      "@typescript-eslint/no-explicit-any": "off",
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_", caughtErrors: "none" },
      ],
    },
  },
);
