import { useState } from "react";
import { suppliersApi, type CpvCode } from "../../api/endpoints/suppliers";
import { useTranslation } from "react-i18next";

// ─── CPV tag input con AI suggest ────────────────────────────────────────────

export function CpvInput({
  value,
  onChange,
  description,
}: {
  value: CpvCode[];
  onChange: (codes: CpvCode[]) => void;
  description: string;
}) {
  const { t } = useTranslation();
  const [codeInput, setCodeInput] = useState("");
  const [labelInput, setLabelInput] = useState("");
  const [aiOpen, setAiOpen] = useState(false);
  const [suggestions, setSuggestions] = useState<CpvCode[]>([]);
  const [aiError, setAiError] = useState("");
  const [aiLoading, setAiLoading] = useState(false);

  // CPV standard: 8 cifre + trattino + 1 cifra di controllo (es. 79211100-0)
  const CPV_PATTERN = /^\d{8}-\d$/;

  function formatCpv(raw: string): string {
    const digits = raw.replace(/\D/g, "").slice(0, 9);
    if (digits.length <= 8) return digits;
    return `${digits.slice(0, 8)}-${digits.slice(8)}`;
  }

  function addCode() {
    const code = codeInput.trim();
    const label = labelInput.trim();
    if (!CPV_PATTERN.test(code)) return;
    if (value.some(c => c.code === code)) return;
    onChange([...value, { code, label }]);
    setCodeInput("");
    setLabelInput("");
  }

  function removeCode(code: string) {
    onChange(value.filter(c => c.code !== code));
  }

  async function fetchSuggestions() {
    if (!description.trim()) {
      setAiError(t("suppliers.cpv.ai_need_desc"));
      setAiOpen(true);
      return;
    }
    setAiLoading(true);
    setAiError("");
    setAiOpen(true);
    setSuggestions([]);
    try {
      const res = await suppliersApi.suggestCpv(description);
      setSuggestions(res.suggestions ?? []);
    } catch (e: any) {
      setAiError(e?.response?.data?.error || t("suppliers.cpv.ai_error"));
    } finally {
      setAiLoading(false);
    }
  }

  function acceptSuggestion(s: CpvCode) {
    if (!value.some(c => c.code === s.code)) {
      onChange([...value, s]);
    }
  }

  return (
    <div>
      {/* Tag esistenti */}
      {value.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {value.map(c => (
            <span key={c.code} className="inline-flex items-center gap-1 bg-indigo-50 text-indigo-800 text-xs px-2 py-0.5 rounded-full border border-indigo-200">
              <span className="font-mono font-medium">{c.code}</span>
              {c.label && <span className="text-indigo-600">— {c.label}</span>}
              <button onClick={() => removeCode(c.code)} className="ml-0.5 text-indigo-400 hover:text-red-500 font-bold leading-none">&times;</button>
            </span>
          ))}
        </div>
      )}

      {/* Input aggiunta manuale */}
      <div className="flex gap-1.5 items-end">
        <div>
          <label className="block text-xs text-gray-500 mb-0.5">{t("suppliers.cpv.code_label")}</label>
          <input
            type="text"
            value={codeInput}
            onChange={e => setCodeInput(formatCpv(e.target.value))}
            onKeyDown={e => e.key === "Enter" && (e.preventDefault(), addCode())}
            placeholder="79211100-0"
            className="w-32 border rounded px-2 py-1 text-xs font-mono"
          />
        </div>
        <div className="flex-1">
          <label className="block text-xs text-gray-500 mb-0.5">{t("suppliers.cpv.desc_label")}</label>
          <input
            type="text"
            value={labelInput}
            onChange={e => setLabelInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && (e.preventDefault(), addCode())}
            placeholder={t("suppliers.cpv.desc_placeholder")}
            className="w-full border rounded px-2 py-1 text-xs"
          />
        </div>
        <button
          type="button"
          onClick={addCode}
          disabled={!CPV_PATTERN.test(codeInput)}
          className="px-2 py-1 text-xs bg-indigo-600 text-white rounded disabled:opacity-40 whitespace-nowrap"
        >
          {t("suppliers.cpv.add_btn")}
        </button>
        <button
          type="button"
          onClick={fetchSuggestions}
          title={t("suppliers.cpv.ai_btn_title")}
          className="px-2 py-1 text-xs border border-violet-300 text-violet-700 rounded hover:bg-violet-50 whitespace-nowrap flex items-center gap-1"
        >
          <span>✦</span> AI
        </button>
      </div>

      {/* Pannello suggerimenti AI */}
      {aiOpen && (
        <div className="mt-2 p-3 bg-violet-50 border border-violet-200 rounded-lg">
          <div className="flex items-center justify-between mb-1.5">
            <p className="text-xs font-medium text-violet-800">{t("suppliers.cpv.ai_panel_title")}</p>
            <button onClick={() => setAiOpen(false)} className="text-xs text-violet-400 hover:text-violet-700">{t("suppliers.cpv.ai_close")}</button>
          </div>
          <p className="text-xs text-violet-500 mb-2">
            {t("suppliers.cpv.ai_privacy")}
          </p>
          {aiLoading && <p className="text-xs text-violet-600 animate-pulse">{t("suppliers.cpv.ai_loading")}</p>}
          {aiError && <p className="text-xs text-red-600">{aiError}</p>}
          {!aiLoading && suggestions.length > 0 && (
            <div className="space-y-1">
              {suggestions.map(s => {
                const alreadyAdded = value.some(c => c.code === s.code);
                return (
                  <div key={s.code} className="flex items-center justify-between bg-white border border-violet-100 rounded px-2 py-1">
                    <span className="text-xs">
                      <span className="font-mono font-semibold text-indigo-700">{s.code}</span>
                      {s.label && <span className="text-gray-600 ml-2">{s.label}</span>}
                    </span>
                    <button
                      onClick={() => acceptSuggestion(s)}
                      disabled={alreadyAdded}
                      className={`text-xs px-2 py-0.5 rounded border ${alreadyAdded ? "border-gray-200 text-gray-400 bg-gray-50" : "border-green-300 text-green-700 hover:bg-green-50"}`}
                    >
                      {alreadyAdded ? t("suppliers.cpv.accepted") : t("suppliers.cpv.accept")}
                    </button>
                  </div>
                );
              })}
            </div>
          )}
          {!aiLoading && suggestions.length === 0 && !aiError && (
            <p className="text-xs text-violet-500 italic">{t("suppliers.cpv.ai_none")}</p>
          )}
        </div>
      )}
    </div>
  );
}
