import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

/**
 * Preferenze UI locali al dispositivo (localStorage, nessun backend):
 *
 * - `sidebarCollapsed`: sidebar a rail di sole icone per ampliare il contenuto.
 * - `scaleByScreen`: scala dell'interfaccia memorizzata PER MONITOR. La chiave
 *   è la "firma" dello schermo corrente (risoluzione fisica × pixel ratio):
 *   spostando la finestra dal laptop 14" al 27" la firma cambia e l'app
 *   riapplica da sola la scala scelta per quel monitor — niente più zoom
 *   browser da ritoccare a ogni cambio. La scala agisce sul font-size della
 *   root (tutto il layout è in rem, quindi scala in proporzione).
 *
 * `signature` è la firma dello schermo corrente, tenuta nello store (non
 * persistita) così i componenti che mostrano la scala si aggiornano quando la
 * finestra cambia monitor (UiScaleManager la rinfresca sui resize).
 */

export const SCALE_MIN = 0.8;
export const SCALE_MAX = 1.4;
export const SCALE_STEP = 0.1;
const BASE_FONT_PX = 16;

export function screenSignature(): string {
  if (typeof window === "undefined") return "default";
  const s = window.screen;
  const dpr = window.devicePixelRatio || 1;
  return `${s.width}x${s.height}@${dpr}`;
}

export function applyScale(scale: number): void {
  document.documentElement.style.fontSize = `${BASE_FONT_PX * scale}px`;
}

function clamp(scale: number): number {
  // Evita derive da floating point (0.7999999) arrotondando al decimo
  const rounded = Math.round(scale * 10) / 10;
  return Math.min(SCALE_MAX, Math.max(SCALE_MIN, rounded));
}

interface UiStore {
  sidebarCollapsed: boolean;
  scaleByScreen: Record<string, number>;
  signature: string;
  toggleSidebar: () => void;
  /** Riallinea la firma allo schermo corrente; ritorna la scala da applicare. */
  refreshSignature: () => number;
  /** Scala per il monitor corrente (default 1). */
  currentScale: () => number;
  changeScale: (delta: number) => void;
  resetScale: () => void;
}

export const useUiStore = create<UiStore>()(
  persist(
    (set, get) => ({
      sidebarCollapsed: false,
      scaleByScreen: {},
      signature: screenSignature(),
      toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
      refreshSignature: () => {
        const sig = screenSignature();
        if (sig !== get().signature) set({ signature: sig });
        return get().scaleByScreen[sig] ?? 1;
      },
      currentScale: () => get().scaleByScreen[get().signature] ?? 1,
      changeScale: (delta) =>
        set((s) => {
          const next = clamp((s.scaleByScreen[s.signature] ?? 1) + delta);
          applyScale(next);
          return { scaleByScreen: { ...s.scaleByScreen, [s.signature]: next } };
        }),
      resetScale: () =>
        set((s) => {
          applyScale(1);
          return { scaleByScreen: { ...s.scaleByScreen, [s.signature]: 1 } };
        }),
    }),
    {
      name: "grc-ui",
      storage: createJSONStorage(() => localStorage),
      // signature è effimera: ricalcolata a ogni avvio/resize, mai persistita
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
        scaleByScreen: state.scaleByScreen,
      }),
    },
  ),
);
