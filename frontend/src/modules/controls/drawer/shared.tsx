import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import i18n from "../../../i18n";

// ─── Tipi condivisi ───────────────────────────────────────────────────────────

export type Tab = "cosa" | "valutazione" | "docevidence" | "storico";

// ─── Helpers ──────────────────────────────────────────────────────────────────

export function evidenceIcon(type: string): string {
  const map: Record<string, string> = {
    screenshot: "📸", log: "📋", report: "📄",
    verbale: "📝", certificato: "🏆", test_result: "🧪", altro: "📎",
  };
  return map[type] ?? "📎";
}

export function docStatusColor(status: string): string {
  const map: Record<string, string> = {
    approvato:   "bg-green-100 text-green-800",
    revisione:   "bg-blue-100 text-blue-700",
    approvazione:"bg-blue-100 text-blue-700",
    bozza:       "bg-gray-100 text-gray-600",
    archiviato:  "bg-gray-200 text-gray-500",
  };
  return map[status] ?? "bg-gray-100 text-gray-500";
}

export function ExpiryBadge({ validUntil }: { validUntil: string | null }) {
  const { t } = useTranslation();
  if (!validUntil) return <span className="text-gray-400 text-xs">{t("controls.drawer.expiry.none")}</span>;
  const date = new Date(validUntil);
  const today = new Date();
  const days = Math.ceil((date.getTime() - today.getTime()) / 86400000);
  if (days < 0) return (
    <span className="text-xs px-1.5 py-0.5 rounded bg-red-100 text-red-700 font-medium">
      {t("controls.drawer.expiry.expired_days_ago", { days: Math.abs(days) })}
    </span>
  );
  if (days <= 30) return (
    <span className="text-xs px-1.5 py-0.5 rounded bg-orange-100 text-orange-700 font-medium">
      {t("controls.drawer.expiry.expires_in_days", { days })}
    </span>
  );
  return (
    <span className="text-xs px-1.5 py-0.5 rounded bg-green-100 text-green-700 font-medium">
      {t("controls.drawer.expiry.valid_until", { date: date.toLocaleDateString(i18n.language || "it") })}
    </span>
  );
}

export const STATUS_GUIDE = [
  { status: "compliant",    icon: "🟢", label: "Compliant",    reqKey: "controls.drawer.evaluation.status_guide.compliant", badge: "bg-green-100 text-green-800" },
  { status: "parziale",     icon: "🟡", label: "Partial",      reqKey: "controls.drawer.evaluation.status_guide.parziale", badge: "bg-yellow-100 text-yellow-800" },
  { status: "gap",          icon: "🔴", label: "Gap",          reqKey: "controls.drawer.evaluation.status_guide.gap", badge: "bg-red-100 text-red-800" },
  { status: "na",           icon: "⚪", label: "N/A",          reqKey: "controls.drawer.evaluation.status_guide.na", badge: "bg-gray-100 text-gray-600" },
  { status: "non_valutato", icon: "⬜", label: "Not assessed", reqKey: "controls.drawer.evaluation.status_guide.non_valutato", badge: "bg-gray-50 text-gray-500" },
];

export function useDebounce(value: string, delay = 300) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}
