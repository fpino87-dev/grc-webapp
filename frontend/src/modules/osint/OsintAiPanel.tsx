import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { osintApi } from "../../api/endpoints/osint";

type AiType = "attack_surface" | "suppliers_nis2" | "board_report";

export function OsintAiPanel({ type, onClose }: { type: AiType; onClose: () => void }) {
  const { t } = useTranslation();
  const [result, setResult] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const mutation = useMutation({
    mutationFn: () => osintApi.aiAnalyze(type),
    onSuccess: data => setResult(data.analysis),
  });

  const titleMap: Record<AiType, string> = {
    attack_surface: t("osint.ai.attack_surface"),
    suppliers_nis2: t("osint.ai.suppliers_nis2"),
    board_report: t("osint.ai.board_report"),
  };

  function handleCopy() {
    if (result) {
      navigator.clipboard.writeText(result);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }

  function handleDownload() {
    if (!result) return;
    const blob = new Blob([result], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `osint_${type}_${new Date().toISOString().slice(0, 10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/30 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-xl">🤖</span>
            <h2 className="font-semibold text-gray-900">{titleMap[type]}</h2>
          </div>
          <button onClick={onClose} className="p-1.5 hover:bg-gray-100 rounded">✕</button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {!result && !mutation.isPending && (
            <div className="text-center py-8">
              <p className="text-gray-500 mb-4 text-sm">{t("osint.ai.description")}</p>
              <button
                onClick={() => mutation.mutate()}
                className="px-6 py-2.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm font-medium"
              >
                {t("osint.ai.start")}
              </button>
            </div>
          )}

          {mutation.isPending && (
            <div className="text-center py-8">
              <div className="animate-spin text-3xl mb-3">⏳</div>
              <p className="text-gray-500 text-sm">{t("osint.ai.loading")}</p>
            </div>
          )}

          {mutation.isError && (
            <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
              {t("osint.ai.error")}
            </div>
          )}

          {result && (
            <pre className="whitespace-pre-wrap text-sm text-gray-800 font-sans leading-relaxed">
              {result}
            </pre>
          )}
        </div>

        {/* Footer con azioni */}
        {result && (
          <div className="px-6 py-3 border-t shrink-0 flex gap-2 justify-end bg-gray-50 rounded-b-xl">
            <button
              onClick={handleCopy}
              className="px-3 py-1.5 text-sm border rounded hover:bg-gray-100"
            >
              {copied ? "✓ Copiato" : "📋 " + t("osint.ai.copy")}
            </button>
            <button
              onClick={handleDownload}
              className="px-3 py-1.5 text-sm border rounded hover:bg-gray-100"
            >
              ⬇ {t("osint.ai.download")}
            </button>
            <button
              onClick={() => { setResult(null); mutation.mutate(); }}
              className="px-3 py-1.5 text-sm bg-primary-600 text-white rounded hover:bg-primary-700"
            >
              🔄 {t("osint.ai.regenerate")}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
