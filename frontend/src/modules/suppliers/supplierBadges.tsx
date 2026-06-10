import type { SupplierNdaEntry } from "../../api/endpoints/reporting";
import { useTranslation } from "react-i18next";
import i18n from "../../i18n";

// ─── Shared badge components ─────────────────────────────────────────────────

export type SupplierAssessment = {
  id: string;
  assessment_date: string | null;
  status: string;
  score_overall: number | null;
  score_governance: number | null;
  score_security: number | null;
  score_bcp: number | null;
  computed_risk_level: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_notes: string;
};

const ASSESSMENT_STATUS_CLASSES: Record<string, string> = {
  pianificato: "bg-gray-100 text-gray-700",
  in_corso: "bg-blue-100 text-blue-700",
  completato: "bg-amber-100 text-amber-800",
  approvato: "bg-green-100 text-green-800",
  rifiutato: "bg-red-100 text-red-800",
};

export function AssessmentStatusBadge({ status }: { status: string }) {
  const { t } = useTranslation();
  const classes = ASSESSMENT_STATUS_CLASSES[status] ?? "bg-gray-100 text-gray-700";
  const label = ASSESSMENT_STATUS_CLASSES[status] ? t(`suppliers.assessment_status.${status}`) : status;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${classes}`}>
      {label}
    </span>
  );
}

// Mappa livello (interno o "semaforo") → chiave i18n + classi
const RISK_KEY_MAP: Record<string, string> = {
  verde: "basso", giallo: "medio", rosso: "alto",
  basso: "basso", medio: "medio", alto: "alto", critico: "critico",
};
const RISK_CLASSES: Record<string, string> = {
  basso:   "bg-green-100 text-green-800",
  medio:   "bg-amber-100 text-amber-800",
  alto:    "bg-red-100 text-red-800",
  critico: "bg-red-200 text-red-900 font-bold",
};

export function RiskBadge({ level }: { level: string }) {
  const { t } = useTranslation();
  const key = RISK_KEY_MAP[level];
  const label = key ? t(`suppliers.risk.${key}`) : t("suppliers.risk.nd");
  const classes = key ? RISK_CLASSES[key] : "bg-gray-100 text-gray-600";
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${classes}`}>
      {label}
    </span>
  );
}

export function QStatus({ status, sendCount }: { status: string; sendCount: number }) {
  const { t } = useTranslation();
  if (status === "risposto") return <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">&#10003; {t("suppliers.qstatus.responded")}</span>;
  if (status === "scaduto")  return <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">{t("suppliers.qstatus.expired")}</span>;
  if (sendCount >= 3) return <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-200 text-red-900">{t("suppliers.qstatus.third_send")}</span>;
  if (sendCount === 2) return <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800">{t("suppliers.qstatus.second_send")}</span>;
  return <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700">{t("suppliers.qstatus.waiting")}</span>;
}

// ─── ACN / NIS2 badge helpers ────────────────────────────────────────────────

export function Nis2Badge({ relevant }: { relevant: boolean }) {
  if (!relevant) return <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-500">—</span>;
  return <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">NIS2</span>;
}

const CONCENTRATION_CLASSES: Record<string, string> = {
  bassa:   "bg-green-100 text-green-700",
  media:   "bg-amber-100 text-amber-800",
  critica: "bg-red-200 text-red-900 font-bold",
};

export function ConcentrationBadge({ threshold }: { threshold: string }) {
  const { t } = useTranslation();
  const known = !!CONCENTRATION_CLASSES[threshold];
  const classes = known ? CONCENTRATION_CLASSES[threshold] : "bg-gray-100 text-gray-500";
  const label = known ? t(`suppliers.concentration.${threshold}`) : t("suppliers.concentration.nd");
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${classes}`}>
      {label}
    </span>
  );
}

// ─── NDA badges ──────────────────────────────────────────────────────────────

const NDA_DOC_STATUS_CLASSES: Record<string, string> = {
  bozza:        "bg-gray-100 text-gray-700",
  revisione:    "bg-blue-100 text-blue-700",
  approvazione: "bg-amber-100 text-amber-800",
  approvato:    "bg-green-100 text-green-800",
  archiviato:   "bg-gray-200 text-gray-600",
};

export function NdaDocStatusBadge({ status }: { status: string }) {
  const { t } = useTranslation();
  const known = !!NDA_DOC_STATUS_CLASSES[status];
  const classes = known ? NDA_DOC_STATUS_CLASSES[status] : "bg-gray-100 text-gray-600";
  const label = known ? t(`suppliers.doc_status.${status}`) : status;
  return <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${classes}`}>{label}</span>;
}

const NDA_STATUS_CLASSES: Record<string, string> = {
  ok:       "bg-green-100 text-green-800",
  expiring: "bg-yellow-100 text-yellow-800",
  expired:  "bg-red-100 text-red-800",
  draft:    "bg-gray-100 text-gray-700",
  missing:  "bg-red-50 text-red-600 border border-red-200",
};

export function NdaStatusBadge({ status }: { status: SupplierNdaEntry["nda_status"] }) {
  const { t } = useTranslation();
  const known = !!NDA_STATUS_CLASSES[status];
  const classes = known ? NDA_STATUS_CLASSES[status] : NDA_STATUS_CLASSES.missing;
  const label = t(`suppliers.nda.status_${known ? status : "missing"}`);
  return <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${classes}`}>{label}</span>;
}

// ─── Celle data valutazione / scadenza ───────────────────────────────────────

export function EvalDateCell({ date }: { date: string | null }) {
  if (!date) return <span className="text-gray-400">—</span>;
  return (
    <span className="text-gray-600">
      {new Date(date).toLocaleDateString(i18n.language || "it")}
    </span>
  );
}

export function ExpiryDateCell({ evaluationDate }: { evaluationDate: string | null }) {
  if (!evaluationDate) return <span className="text-gray-400">—</span>;
  const expiry = new Date(evaluationDate);
  expiry.setFullYear(expiry.getFullYear() + 1);
  const daysLeft = Math.ceil((expiry.getTime() - Date.now()) / (1000 * 60 * 60 * 24));
  let colorClass = "text-green-600";
  if (daysLeft <= 30) colorClass = "text-red-600 font-medium";
  else if (daysLeft <= 90) colorClass = "text-orange-500 font-medium";
  return (
    <span className={colorClass}>
      {expiry.toLocaleDateString(i18n.language || "it")}
      {daysLeft <= 90 && <span className="ml-1 text-xs">({daysLeft}gg)</span>}
    </span>
  );
}
