import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import i18n from "../../../i18n";
import type { RequirementsCheck } from "../../../api/endpoints/controls";

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

// Etichetta localizzata di un requisito documentale/evidenza. Helper unico per
// tutti i tab del drawer (prima duplicato ×4): `any` → descrizione libera,
// altrimenti la chiave i18n del tipo, con fallback su descrizione/tipo.
export function useRequirementLabel() {
  const { t } = useTranslation();
  return (kind: "document" | "evidence", type: string, description?: string): string => {
    if (type === "any") return description || "";
    const key = kind === "document" ? `documents.type.${type}` : `documents.evidence.types.${type}`;
    return t(key, { defaultValue: description || type });
  };
}

// Banner di stato dei requisiti documentali, condiviso tra TabValutazione e
// TabDocEvidence (prima duplicato identico in entrambi). L'unica differenza è
// l'intestazione del caso "non soddisfatto", parametrizzata da `notSatisfiedKey`.
export function RequirementsBanner({
  requirements,
  noRequirements,
  notSatisfiedKey = "controls.drawer.evaluation.requirements.not_satisfied",
}: {
  requirements: RequirementsCheck;
  noRequirements: boolean;
  notSatisfiedKey?: string;
}) {
  const { t } = useTranslation();
  const requirementLabel = useRequirementLabel();

  if (requirements.not_applicable) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-xs text-gray-500">
        ℹ️ {t("controls.drawer.evaluation.requirements.not_applicable")}
      </div>
    );
  }
  if (noRequirements) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-xs text-gray-500">
        ℹ️ {t("controls.drawer.evaluation.requirements.none")}
      </div>
    );
  }
  if (!requirements.satisfied) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg px-3 py-2 text-xs text-red-800">
        <p className="font-semibold mb-1">⛔ {t(notSatisfiedKey)}</p>
        {requirements.missing_documents.map((m, i) => (
          <p key={i}>• {t("controls.drawer.evaluation.requirements.missing_document")}: {requirementLabel("document", m.type, m.description)}</p>
        ))}
        {requirements.missing_evidences.map((m, i) => (
          <p key={i}>• {t("controls.drawer.evaluation.requirements.missing_evidence")}: {requirementLabel("evidence", m.type, m.description)}</p>
        ))}
        {requirements.expired_evidences.map((e, i) => (
          <p key={i}>• {t("controls.drawer.evaluation.requirements.expired_evidence")}: {e.title} ({e.expired_on})</p>
        ))}
      </div>
    );
  }
  if (requirements.warnings.length > 0) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg px-3 py-2 text-xs text-yellow-800">
        <p className="font-semibold mb-1">⚠️ {t("controls.drawer.evaluation.requirements.warning")}</p>
        {requirements.warnings.map((w, i) => <p key={i}>• {w}</p>)}
      </div>
    );
  }
  return (
    <div className="bg-green-50 border border-green-200 rounded-lg px-3 py-2 text-xs text-green-800">
      ✅ {t("controls.drawer.evaluation.requirements.satisfied")}
    </div>
  );
}

export function useDebounce(value: string, delay = 300) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}
