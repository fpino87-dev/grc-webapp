import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import type { ItemState } from "../../api/endpoints/training";

/** Primo messaggio leggibile di un errore DRF (`detail`, `error` o per campo). */
export function apiErrorMessage(e: unknown, fallback: string): string {
  const data = (e as { response?: { data?: unknown } })?.response?.data;
  if (!data) return fallback;
  if (typeof data === "string") return fallback;
  if (Array.isArray(data)) return String(data[0] ?? fallback);
  const obj = data as Record<string, unknown>;
  for (const key of ["detail", "error", "non_field_errors"]) {
    const v = obj[key];
    if (v) return Array.isArray(v) ? String(v[0]) : String(v);
  }
  const first = Object.values(obj)[0];
  if (first) return Array.isArray(first) ? String(first[0]) : String(first);
  return fallback;
}

export function Modal({ title, onClose, children, wide = false }: {
  title: string; onClose: () => void; children: ReactNode; wide?: boolean;
}) {
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className={`bg-white rounded-lg shadow-xl w-full ${wide ? "max-w-2xl" : "max-w-lg"} max-h-[90vh] overflow-y-auto`}>
        <div className="flex items-center justify-between px-6 pt-5 pb-3 border-b border-gray-100">
          <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none" aria-label="×">×</button>
        </div>
        <div className="px-6 py-4">{children}</div>
      </div>
    </div>
  );
}

export const inputCls = "w-full border border-gray-300 rounded px-3 py-2 text-sm";
export const labelCls = "block text-sm font-medium text-gray-700 mb-1";
export const btnPrimary = "px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50";
export const btnSecondary = "px-4 py-2 border border-gray-300 rounded text-sm text-gray-600 hover:bg-gray-50";
export const th = "text-left px-4 py-3 font-medium text-gray-600";
export const td = "px-4 py-3 align-middle";

const STATE_CLS: Record<ItemState, string> = {
  fatto: "bg-green-100 text-green-800",
  in_ritardo: "bg-red-100 text-red-700",
  in_scadenza: "bg-amber-100 text-amber-800",
  pianificato: "bg-gray-100 text-gray-600",
};

export function ItemStateBadge({ state }: { state: ItemState }) {
  const { t } = useTranslation();
  return (
    <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${STATE_CLS[state]}`}>
      {t(`training.item_states.${state}`)}
    </span>
  );
}

export function CoverageBar({ pct }: { pct: number | null }) {
  if (pct === null) return <span className="text-xs text-gray-400">—</span>;
  const color = pct >= 95 ? "bg-green-500" : pct >= 80 ? "bg-yellow-400" : "bg-red-500";
  return (
    <div className="flex items-center gap-2 min-w-[8rem]">
      <div className="flex-1 bg-gray-100 rounded-full h-2 overflow-hidden">
        <div className={`h-2 rounded-full ${color}`} style={{ width: `${Math.min(pct, 100)}%` }} />
      </div>
      <span className="text-xs font-semibold w-12 text-right">{pct}%</span>
    </div>
  );
}

/** Mesi trascorsi da una data ISO (per il segnale «headcount da riverificare»). */
export function monthsSince(iso: string): number {
  const d = new Date(iso);
  const now = new Date();
  return (now.getFullYear() - d.getFullYear()) * 12 + (now.getMonth() - d.getMonth());
}

export const HEADCOUNT_STALE_MONTHS = 6;
