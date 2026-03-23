import { useState } from "react"
import { ManualDrawer } from "../ui/ManualDrawer"

export function BottomBar() {
  const [openManual, setOpenManual] = useState<"utente" | "tecnico" | null>(null)

  return (
    <>
      {/* Bottom bar fissa */}
      <div className="fixed bottom-0 left-0 right-0 h-10 bg-white border-t border-gray-200 flex items-center justify-end px-4 gap-4 z-30 shadow-sm">

        {/* Versione app */}
        <span className="text-xs text-gray-300 mr-auto">GRC Platform v1.0</span>

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
