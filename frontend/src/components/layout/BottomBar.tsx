import { useState } from "react"
import { ManualDrawer } from "../ui/ManualDrawer"

export function BottomBar() {
  const [openManual, setOpenManual] = useState<"utente" | "tecnico" | null>(null)

  return (
    <>
      {/* Bottom bar fissa */}
      <div className="fixed bottom-0 left-0 right-0 h-10 bg-white border-t border-gray-200 flex items-center justify-end px-4 gap-4 z-30 shadow-sm">

        {/* Versione app */}
        <span className="text-xs text-gray-300 mr-auto">GRC Platform v0.4.0</span>

        {/* Manuale Utente */}
        <button
          onClick={() => setOpenManual("utente")}
          className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-blue-600 transition-colors px-2 py-1 rounded hover:bg-blue-50"
          title="Manuale Utente"
        >
          <span className="text-base">📖</span>
          <span className="hidden sm:inline">Manuale Utente</span>
        </button>

        {/* Manuale Tecnico */}
        <button
          onClick={() => setOpenManual("tecnico")}
          className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-blue-600 transition-colors px-2 py-1 rounded hover:bg-blue-50"
          title="Manuale Tecnico"
        >
          <span className="text-base">🔧</span>
          <span className="hidden sm:inline">Manuale Tecnico</span>
        </button>

        {/* Donazione */}
        <a
          href="https://buymeacoffee.com/fpino87"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 text-xs text-amber-600 hover:text-amber-700 transition-colors px-2 py-1 rounded hover:bg-amber-50 border border-amber-200 hover:border-amber-300"
          title="Supporta il progetto open source"
        >
          <span className="text-base">☕</span>
          <span className="hidden sm:inline font-medium">Supporta il progetto</span>
        </a>
      </div>

      {/* Drawer manuale */}
      {openManual && (
        <ManualDrawer
          type={openManual}
          onClose={() => setOpenManual(null)}
        />
      )}
    </>
  )
}
