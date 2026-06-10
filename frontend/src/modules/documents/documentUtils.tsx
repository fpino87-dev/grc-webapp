import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { documentsApi, type Document, type Evidence } from "../../api/endpoints/documents";
import { useTranslation } from "react-i18next";
import i18n from "../../i18n";

// ─── Helpers evidenze ────────────────────────────────────────────────────────

export function evidenceIcon(type: string): string {
  const map: Record<string, string> = {
    screenshot: "📸", log: "📋", report: "📄",
    verbale: "📝", certificato: "🏆", test_result: "🧪", altro: "📎",
  };
  return map[type] ?? "📎";
}

export function ExpiryBadge({ validUntil }: { validUntil: string | null }) {
  const { t } = useTranslation();
  if (!validUntil) return <span className="text-xs text-gray-400">—</span>;
  const date = new Date(validUntil);
  const today = new Date();
  const days = Math.ceil((date.getTime() - today.getTime()) / 86400000);
  if (days < 0) return (
    <div className="text-center">
      <span className="block text-xs px-2 py-0.5 rounded bg-red-100 text-red-700 font-medium">{t("documents.evidence.expiry.expired")}</span>
      <span className="text-xs text-red-500">{t("documents.evidence.expiry.days_ago", { days: Math.abs(days) })}</span>
    </div>
  );
  if (days <= 30) return (
    <div className="text-center">
      <span className="block text-xs px-2 py-0.5 rounded bg-orange-100 text-orange-700 font-medium">{t("documents.evidence.expiry.expiring")}</span>
      <span className="text-xs text-orange-600">{t("documents.evidence.expiry.in_days", { days })}</span>
    </div>
  );
  return (
    <div className="text-center">
      <span className="block text-xs px-2 py-0.5 rounded bg-green-100 text-green-700 font-medium">{t("documents.evidence.expiry.valid")}</span>
      <span className="text-xs text-green-600">{date.toLocaleDateString(i18n.language || "it")}</span>
    </div>
  );
}

export const EVIDENCE_TYPES = ["screenshot", "log", "report", "verbale", "certificato", "test_result", "altro"] as const;

export function expirySort(a: Evidence, b: Evidence): number {
  if (!a.valid_until && !b.valid_until) return 0;
  if (!a.valid_until) return 1;
  if (!b.valid_until) return -1;
  const today = new Date();
  const da = new Date(a.valid_until);
  const db = new Date(b.valid_until);
  const daysA = Math.ceil((da.getTime() - today.getTime()) / 86400000);
  const daysB = Math.ceil((db.getTime() - today.getTime()) / 86400000);
  // in scadenza prima, poi valide, poi scadute
  if (daysA >= 0 && daysA <= 30 && !(daysB >= 0 && daysB <= 30)) return -1;
  if (daysB >= 0 && daysB <= 30 && !(daysA >= 0 && daysA <= 30)) return 1;
  return daysA - daysB;
}

// ─── Grouped view helpers ────────────────────────────────────────────────────

export type ControlGroup = {
  groupKey: string;
  control_external_id: string;
  control_title: string;
  framework_code: string;
  evidences: Evidence[];
};

export function buildEvidenceGroups(evidences: Evidence[], unassignedLabel: string): ControlGroup[] {
  const groups = new Map<string, ControlGroup>();
  const unassigned: Evidence[] = [];

  for (const ev of evidences) {
    if (!ev.linked_controls || ev.linked_controls.length === 0) {
      unassigned.push(ev);
    } else {
      for (const ctrl of ev.linked_controls) {
        if (!groups.has(ctrl.id)) {
          groups.set(ctrl.id, {
            groupKey: ctrl.id,
            control_external_id: ctrl.control_external_id,
            control_title: ctrl.control_title,
            framework_code: ctrl.framework_code,
            evidences: [],
          });
        }
        groups.get(ctrl.id)!.evidences.push(ev);
      }
    }
  }

  const sorted = Array.from(groups.values()).sort((a, b) => {
    const fw = a.framework_code.localeCompare(b.framework_code);
    if (fw !== 0) return fw;
    return a.control_external_id.localeCompare(b.control_external_id, undefined, { numeric: true, sensitivity: "base" });
  });

  if (unassigned.length > 0) {
    sorted.push({
      groupKey: "__unassigned__",
      control_external_id: "",
      control_title: unassignedLabel,
      framework_code: "",
      evidences: unassigned,
    });
  }

  return sorted;
}

// ─── Inline edit tipo documento ──────────────────────────────────────────────

export const DOC_TYPES = ["policy", "procedura", "manuale", "contratto", "registro", "altro"] as const;

export function InlineTypeEdit({ doc }: { doc: Document }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);

  const mutation = useMutation({
    mutationFn: (document_type: string) => documentsApi.update(doc.id, { document_type }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["documents"] }); setEditing(false); },
  });

  if (editing) {
    return (
      <select
        autoFocus
        defaultValue={doc.document_type ?? ""}
        onChange={e => mutation.mutate(e.target.value)}
        onBlur={() => setEditing(false)}
        className="border rounded px-1 py-0.5 text-xs"
        disabled={mutation.isPending}
      >
        {DOC_TYPES.map(v => (
          <option key={v} value={v}>{t(`documents.type.${v}`)}</option>
        ))}
      </select>
    );
  }

  return (
    <button
      onClick={() => setEditing(true)}
      className="group flex items-center gap-1 text-left"
      title={t("documents.actions.change_type")}
    >
      <span className="capitalize text-xs">
        {doc.document_type
          ? t(`documents.type.${doc.document_type}`, { defaultValue: doc.document_type })
          : doc.category
          ? t(`documents.category.${doc.category}`, { defaultValue: doc.category })
          : "—"}
      </span>
      <span className="text-gray-300 group-hover:text-gray-500 text-xs">✎</span>
    </button>
  );
}
