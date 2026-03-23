import { useQuery } from "@tanstack/react-query"
import ReactMarkdown from "react-markdown"
import { apiClient } from "../../api/client"

interface ManualDrawerProps {
  type: "utente" | "tecnico"
  onClose: () => void
}

export function ManualDrawer({ type, onClose }: ManualDrawerProps) {
  const label = type === "utente" ? "Manuale Utente" : "Manuale Tecnico"
  const icon  = type === "utente" ? "📖" : "🔧"

  const { data, isLoading, isError } = useQuery({
    queryKey: ["manual", type],
    queryFn: async () => {
      const res = await apiClient.get(`/manual/${type}/`)
      return res.data.content as string
    },
    staleTime: Infinity,
  })

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
          </div>
          <div className="flex items-center gap-3">
            <a
              href={`/api/manual/${type}/`}
              download={`${label}.md`}
              className="text-sm text-blue-600 hover:underline"
            >
              ⬇ Scarica
            </a>
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
              <span className="text-gray-400">Caricamento manuale...</span>
            </div>
          )}
          {isError && (
            <div className="text-red-500 text-sm p-4 bg-red-50 rounded">
              Errore nel caricamento del manuale.
            </div>
          )}
          {data && (
            <div className="prose prose-sm max-w-none
              prose-headings:text-blue-800
              prose-h1:text-xl prose-h2:text-lg prose-h3:text-base
              prose-code:bg-gray-100 prose-code:px-1 prose-code:rounded
              prose-pre:bg-gray-900 prose-pre:text-gray-100
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
