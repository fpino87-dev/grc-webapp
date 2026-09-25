import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import i18n from "../../i18n";
import { osintApi, type Grade, type OsintFinding } from "../../api/endpoints/osint";

export const GRADE_TONE: Record<Grade, string> = {
  A: "bg-emerald-600 text-white",
  B: "bg-green-500 text-white",
  C: "bg-yellow-400 text-gray-900",
  D: "bg-orange-500 text-white",
  F: "bg-red-600 text-white",
};

/** Voto A–F con il punteggio di sicurezza (più alto = meglio). */
export function GradeBadge({ grade, security, size = "md" }: { grade?: Grade | null; security?: number | null; size?: "md" | "lg" | "xl" }) {
  const { t } = useTranslation();
  if (!grade) return <span className="text-xs text-gray-400">{t("osint.grade.none")}</span>;
  const dim = size === "xl" ? "w-16 h-16 text-3xl" : size === "lg" ? "w-11 h-11 text-xl" : "w-8 h-8 text-sm";
  return (
    <span className="inline-flex items-center gap-2" title={t("osint.grade.tooltip", { security })}>
      <span className={`inline-flex items-center justify-center rounded-lg font-bold ${dim} ${GRADE_TONE[grade]}`}>{grade}</span>
      {security != null && <span className={`${size === "xl" ? "text-2xl" : "text-sm"} font-semibold text-gray-700 tabular-nums`}>{security}</span>}
    </span>
  );
}

/** Sparkline SVG della sicurezza (0–100). */
export function Sparkline({ values, width = 80, height = 24 }: { values: (number | null)[]; width?: number; height?: number }) {
  const pts = values.filter((v): v is number => v != null);
  if (pts.length < 2) return <span className="text-xs text-gray-300">—</span>;
  const step = width / (pts.length - 1);
  const y = (v: number) => height - 2 - (v / 100) * (height - 4);
  const d = pts.map((v, i) => `${i === 0 ? "M" : "L"}${(i * step).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const up = pts[pts.length - 1] >= pts[0];
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-hidden className="overflow-visible">
      <path d={d} fill="none" strokeWidth={1.8} className={up ? "stroke-emerald-500" : "stroke-red-500"} />
      <circle cx={(pts.length - 1) * step} cy={y(pts[pts.length - 1])} r={2.2} className={up ? "fill-emerald-500" : "fill-red-500"} />
    </svg>
  );
}

export const findingTitle = (t: (k: string, o?: Record<string, unknown>) => string, f: Pick<OsintFinding, "code"> & { playbook?: OsintFinding["playbook"] }) =>
  t(`osint.finding_title.${f.code}`, { defaultValue: f.playbook?.title ?? f.code });

const REPORT_LANGS = ["it", "en", "fr", "pl", "tr"] as const;

/** "Segnala al fornitore": testo pronto nella lingua scelta, da copiare o
 *  aprire nel client di posta; la piattaforma registra solo la segnalazione
 *  (le informazioni di esposizione non partono da qui verso l'esterno). */
export function ReportToSupplierDialog({ finding, onClose }: { finding: OsintFinding; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [lang, setLang] = useState<string>(i18n.language?.slice(0, 2) || "it");
  const [note, setNote] = useState("");
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");
  const tl = i18n.getFixedT(lang);
  const subject = tl("osint.report.subject", { domain: finding.entity_domain });
  const body = tl("osint.report.body", {
    domain: finding.entity_domain,
    problem: tl(`osint.finding_title.${finding.code}`, { defaultValue: finding.code }),
    explanation: tl(`osint.finding_explain.${finding.code}`, { defaultValue: "" }),
    since: new Date(finding.first_seen).toLocaleDateString(lang),
  });
  const mark = useMutation({
    mutationFn: () => osintApi.reportFinding(finding.id, note),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["osint-entity"] });
      qc.invalidateQueries({ queryKey: ["osint-supplier-queue"] });
      qc.invalidateQueries({ queryKey: ["osint-posture"] });
      onClose();
    },
    onError: (e: unknown) => setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || t("common.error")),
  });
  return (
    <div className="fixed inset-0 z-[60] bg-black/40 flex items-center justify-center p-4" role="dialog" aria-modal="true">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-xl p-6 space-y-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">{t("osint.report.title")}</h3>
          <p className="text-sm text-gray-500">{t("osint.report.intro")}</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-600">{t("osint.report.language")}</span>
          {REPORT_LANGS.map(l => (
            <button key={l} type="button" onClick={() => setLang(l)} aria-pressed={lang === l}
              className={`text-xs px-2 py-0.5 rounded border uppercase ${lang === l ? "bg-gray-900 text-white border-gray-900" : "border-gray-300 text-gray-600"}`}>{l}</button>
          ))}
        </div>
        {t(`osint.finding_action.${finding.code}`, { defaultValue: "" }) && (
          <p className="text-xs text-indigo-800 bg-indigo-50 rounded-lg px-3 py-2">
            <span className="font-medium">{t("osint.chain.your_action")}</span> {t(`osint.finding_action.${finding.code}`)}
          </p>
        )}
        <div className="rounded-xl border border-gray-200 bg-gray-50 p-3 text-sm space-y-2">
          <p className="font-medium text-gray-800">{subject}</p>
          <p className="whitespace-pre-line text-gray-700">{body}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={() => { navigator.clipboard?.writeText(`${subject}\n\n${body}`); setCopied(true); }}
            className="px-3 py-1.5 text-sm border rounded-lg text-gray-700 hover:bg-gray-50">
            {copied ? `✓ ${t("osint.report.copied")}` : t("osint.report.copy")}
          </button>
          <a href={`mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`}
            className="px-3 py-1.5 text-sm border rounded-lg text-gray-700 hover:bg-gray-50">✉ {t("osint.report.open_mail")}</a>
        </div>
        <label className="block">
          <span className="block text-xs font-medium text-gray-600 mb-1">{t("osint.report.note_label")}</span>
          <input value={note} onChange={e => setNote(e.target.value)} placeholder={t("osint.report.note_placeholder")}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </label>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-4 py-2 text-sm border rounded-lg text-gray-600">{t("actions.cancel")}</button>
          <button onClick={() => mark.mutate()} disabled={mark.isPending}
            className="px-4 py-2 text-sm rounded-lg bg-primary-600 text-white disabled:opacity-50">
            {finding.status === "reported" ? t("osint.report.mark_again") : t("osint.report.mark")}
          </button>
        </div>
      </div>
    </div>
  );
}
