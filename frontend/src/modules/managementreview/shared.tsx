import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { GrcUser } from "../../api/endpoints/users";
import i18n from "../../i18n";

// ── Utility ──────────────────────────────────────────────────────────────────

export function isOverdue(date: string | null | undefined) {
  if (!date) return false;
  return new Date(date) < new Date(new Date().toDateString());
}

export function fmtDate(iso: string | null | undefined) {
  if (!iso) return "—";
  return new Date(iso.length === 10 ? `${iso}T00:00:00` : iso).toLocaleDateString(i18n.language || "it");
}

export function userLabel(u: GrcUser) {
  return `${u.first_name} ${u.last_name}`.trim() || u.email;
}

// Codici dei punti obbligatori ISO 27001 §9.3.2 → lettera della clausola
export const ISO_CLAUSE: Record<string, string> = {
  azioni_precedenti: "a", contesto: "b", parti_interessate: "c", prestazioni: "d",
  feedback_parti: "e", rischi: "f", miglioramento: "g",
};

// ── Snapshot types ───────────────────────────────────────────────────────────

export type Snap = Record<string, any>;
export type SnapGapControl = { id: string; control__external_id: string; titles?: Record<string, string> };
export type SnapFramework = {
  framework_name: string; total: number; pct_compliant: number; by_status: Record<string, number>;
  expired_evidence_count: number; gap_controls?: SnapGapControl[];
};
export type SnapDoc = { id: string; title: string; owner: string; review_due_date: string | null; approved_at: string | null };
// Documento obbligatorio non ancora approvato (elenco_non_approvati).
export type SnapPendingDoc = {
  id: string; title: string; document_code: string; document_type: string;
  /** Revisione come sul frontespizio ("Rev. 03"), o contatore interno. */
  status: string; version: string | null; created_at: string | null;
};
export type SnapRisk = {
  id: string; name: string; asset: string | null; process: string | null;
  inherent_score: number | null; score: number | null; treatment: string | null; owner: string | null;
  has_plan: boolean; accepted_by: string | null; acceptance_expiry: string | null;
};
export type SnapIncident = { id: string; title: string; detected_at: string | null; severity: string; status: string };
export type SnapTask = { id: string; title: string; priority: string; due_date: string | null; assigned_role: string };
export type SnapPdca = { id: string; title: string; created_at: string | null };
export type SnapPdcaOverdue = { id: string; title: string; action_owner: string; target_date: string | null };
export type SnapPrevAction = {
  id: string; description: string; owner: string | null; due_date: string | null; status: string; overdue: boolean;
  closed_at: string | null; review_title: string; review_date: string; task_status: string | null; pdca_phase: string | null;
};
export type SnapKpi = {
  kpi_code: string; name: string; unit: string; value: number | null; status: string;
  threshold_warning: number | null; threshold_critical: number | null; week_start: string; plant_code: string | null;
};
export type SnapAudit = {
  id: string; title: string; audit_date: string | null; framework: string | null; status: string;
  readiness_score: number | null; findings: number; plant_code: string | null;
  // assenti negli snapshot congelati prima dell'introduzione del tipo di audit
  audit_type?: "interno" | "seconda_parte" | "terza_parte"; requesting_party?: string;
};
export type SnapFinding = {
  id: string; title: string; finding_type: string; status: string; response_deadline: string | null;
  overdue: boolean; audit: string; plant_code: string | null;
};
export type SnapObjective = {
  id: string; code: string; title: string; plant_code: string | null; owner_role: string;
  status: string; baseline_value: number | null; target_value: number; target_date: string | null;
  current_value: number | null; unit: string; progress_pct: number | null; track: string;
};
export type SnapSite = {
  plant_id: string; code: string; name: string; pct_compliant: number | null;
  rischi_critici: number; incidenti_aperti: number; task_scaduti: number;
};

// ── Sub-components ──────────────────────────────────────────────────────────

export function KpiBox({ label, value, color }: { label: string; value: number | string; color?: string }) {
  return (
    <div className="bg-gray-50 rounded p-3 text-center">
      <div className={`text-xl font-bold ${color ?? "text-gray-800"}`}>{value}</div>
      <div className="text-xs text-gray-500 mt-0.5">{label}</div>
    </div>
  );
}

export function KpiGrid({ children }: { children: React.ReactNode }) {
  return <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">{children}</div>;
}

export function SnapSection({ title, children, defaultOpen = true }: { title: string; children: React.ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-gray-200 rounded overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full text-left px-4 py-2 bg-gray-50 text-xs font-semibold text-gray-700 flex justify-between items-center hover:bg-gray-100"
      >
        {title}
        <span className="text-gray-400">{open ? "▲" : "▼"}</span>
      </button>
      {open && <div className="px-4 py-3">{children}</div>}
    </div>
  );
}

/** Elenco sintetico per la direzione: nascosto se vuoto, "altri N" se troncato. */
export function DetailTable({ title, headers, rows, total, empty }: { title?: string; headers: string[]; rows: React.ReactNode[][]; total?: number; empty?: string }) {
  const { t } = useTranslation();
  if (rows.length === 0) {
    // Con `empty` la sezione resta visibile e dichiara che non c'è nulla:
    // per la direzione "nessuno" è un'informazione, non un vuoto.
    if (!empty) return null;
    return (
      <div className="mt-3">
        {title && <p className="text-xs font-semibold text-gray-600 mb-1">{title}</p>}
        <p className="text-xs text-gray-500 italic">{empty}</p>
      </div>
    );
  }
  const rest = (total ?? rows.length) - rows.length;
  return (
    <div className="mt-3">
      {title && <p className="text-xs font-semibold text-gray-600 mb-1">{title}</p>}
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-gray-200">
              {headers.map(h => <th key={h} className="text-left py-1 pr-2 font-medium text-gray-500">{h}</th>)}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className="border-b border-gray-100">
                {r.map((c, j) => <td key={j} className="py-1 pr-2 text-gray-700 align-top">{c}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rest > 0 && <p className="text-xs text-gray-400 mt-1">{t("management_review.snap.more", { count: rest })}</p>}
    </div>
  );
}
