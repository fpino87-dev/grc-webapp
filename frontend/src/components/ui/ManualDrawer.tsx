import { useQuery } from "@tanstack/react-query"
import ReactMarkdown from "react-markdown"
import { apiClient } from "../../api/client"
import { useTranslation } from "react-i18next"
import i18n from "../../i18n"

interface ManualDrawerProps {
  type: "utente" | "tecnico"
  onClose: () => void
}

export function ManualDrawer({ type, onClose }: ManualDrawerProps) {
  const { t } = useTranslation()
  const label = type === "utente" ? t("manual.user_manual", "Manuale Utente") : t("manual.tech_manual", "Manuale Tecnico")
  const icon  = type === "utente" ? "📖" : "🔧"
  const lang  = i18n.language || "it"

  const { data, isLoading, isError } = useQuery({
    queryKey: ["manual", type, lang],
    queryFn: async () => {
      const res = await apiClient.get(`/manual/${type}/`)
      return res.data.content as string
    },
    staleTime: 5 * 60 * 1000, // 5 min — si aggiorna al cambio lingua
  })

  function handleDownload() {
    if (!data) return
    const blob = new Blob([data], { type: "text/markdown;charset=utf-8" })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement("a")
    a.href     = url
    a.download = `${label}_${lang}.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 bg-black/30 z-40"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed right-0 top-0 h-full w-full max-w-3xl bg-white shadow-2xl z-50 flex flex-col">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gray-50 shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-xl">{icon}</span>
            <h2 className="text-lg font-semibold text-gray-800">{label}</h2>
            <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded uppercase font-mono">{lang}</span>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleDownload}
              disabled={!data}
              className="text-sm text-blue-600 hover:underline disabled:opacity-40"
            >
              ⬇ {t("manual.download", "Scarica")}
            </button>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 text-2xl font-bold leading-none"
            >
              ×
            </button>
          </div>
        </div>

        {/* Contenuto scrollabile */}
        <div className="flex-1 overflow-y-auto px-8 py-6">
          {isLoading && (
            <div className="flex items-center justify-center h-40">
              <span className="text-gray-400">{t("manual.loading", "Caricamento manuale...")}</span>
            </div>
          )}
          {isError && (
            <div className="text-red-500 text-sm p-4 bg-red-50 rounded">
              {t("manual.error", "Errore nel caricamento del manuale.")}
            </div>
          )}
          {data && (
            <div className="prose prose-sm max-w-none
              prose-headings:text-blue-800
              prose-h1:text-xl prose-h2:text-lg prose-h3:text-base
              prose-code:bg-blue-50 prose-code:text-blue-900 prose-code:px-1 prose-code:rounded prose-code:border prose-code:border-blue-200
              prose-pre:bg-white prose-pre:text-gray-800 prose-pre:border prose-pre:border-gray-300 prose-pre:rounded-md
              [&_pre_code]:bg-transparent [&_pre_code]:border-0 [&_pre_code]:text-gray-800
              prose-table:text-xs
              prose-a:text-blue-600">
              <ReactMarkdown>{data}</ReactMarkdown>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-gray-200 bg-gray-50 shrink-0 text-xs text-gray-400 text-center">
          GRC Platform — {label}
        </div>
      </div>
    </>
  )
}
