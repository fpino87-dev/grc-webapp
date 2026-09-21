import { useTranslation } from "react-i18next";
import type { TrainingKpi } from "../../api/endpoints/reporting";

// Formazione a evidenze: copertura del personale (conteggi per gruppo),
// avanzamento del piano, ultime simulazioni di phishing, prove da rinnovare.
// Nessun nominativo: la prova nominativa è il file allegato all'erogazione.

function pctColor(pct: number | null, good: number, warn: number, higherIsBetter = true) {
  if (pct === null) return "text-gray-400";
  const ok = higherIsBetter ? pct >= good : pct <= good;
  const mid = higherIsBetter ? pct >= warn : pct <= warn;
  return ok ? "text-green-600" : mid ? "text-yellow-600" : "text-red-600";
}

function Bar({ pct }: { pct: number | null }) {
  if (pct === null) return <span className="text-xs text-gray-400">—</span>;
  const color = pct >= 95 ? "bg-green-500" : pct >= 80 ? "bg-yellow-400" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-gray-100 rounded-full h-2 overflow-hidden">
        <div className={`h-2 rounded-full ${color}`} style={{ width: `${Math.min(pct, 100)}%` }} />
      </div>
      <span className="text-xs font-semibold w-12 text-right">{pct}%</span>
    </div>
  );
}

function Card({ label, value, valueClass, hint }: {
  label: string; value: string; valueClass: string; hint?: string;
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className={`text-3xl font-bold mt-1 ${valueClass}`}>{value}</p>
      {hint && <p className="text-xs text-gray-400 mt-1">{hint}</p>}
    </div>
  );
}

const TH = "px-4 py-3 text-left";
const THEAD = "bg-gray-50 border-b border-gray-200 text-xs font-semibold text-gray-600 uppercase tracking-wide";

export function TrainingKpiSection({ data }: { data: TrainingKpi }) {
  const { t } = useTranslation();
  const { coverage, plan, phishing } = data;
  const fmt = (v: number | null) => (v === null ? "—" : `${v}%`);

  return (
    <section>
      <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">
        {t("reporting.kpi.section_training")}
      </h3>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <Card
          label={t("reporting.kpi.training.coverage")}
          value={fmt(coverage.pct)}
          valueClass={pctColor(coverage.pct, 95, 80)}
          hint={coverage.target
            ? t("reporting.kpi.training.coverage_hint", { covered: coverage.covered, target: coverage.target, year: coverage.year })
            : t("reporting.kpi.training.no_coverage")}
        />
        <Card
          label={t("reporting.kpi.training.plan_progress")}
          value={fmt(plan.pct)}
          valueClass={pctColor(plan.pct, 90, 70)}
          hint={plan.due
            ? t("reporting.kpi.training.plan_progress_hint", { done: plan.done, due: plan.due, year: plan.year })
            : t("reporting.kpi.training.no_items_due")}
        />
        <Card
          label={t("reporting.kpi.training.overdue")}
          value={String(plan.overdue)}
          valueClass={plan.overdue === 0 ? "text-green-600" : plan.overdue < 3 ? "text-yellow-600" : "text-red-600"}
          hint={t("reporting.kpi.training.due_soon", { count: plan.due_soon })}
        />
        <Card
          label={t("reporting.kpi.training.phishing_click")}
          value={fmt(phishing.click_pct)}
          valueClass={pctColor(phishing.click_pct, 5, 15, false)}
          hint={phishing.sent
            ? t("reporting.kpi.training.phishing_report_hint", { pct: phishing.report_pct ?? 0, sent: phishing.sent })
            : t("reporting.kpi.training.no_phishing")}
        />
      </div>

      {data.stale_audiences > 0 && (
        <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2 mb-4">
          {t("reporting.kpi.training.stale_audiences", { count: data.stale_audiences })}
        </p>
      )}

      {coverage.rows.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg overflow-x-auto mb-4">
          <table className="w-full text-sm">
            <thead>
              <tr className={THEAD}>
                <th className={TH}>{t("reporting.kpi.col_course")}</th>
                <th className={TH}>{t("reporting.kpi.training.col_site")}</th>
                <th className="px-4 py-3 text-right">{t("reporting.kpi.training.col_target")}</th>
                <th className="px-4 py-3 text-right">{t("reporting.kpi.training.col_trained")}</th>
                <th className="px-4 py-3 text-left w-44">{t("reporting.kpi.training.coverage")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {coverage.rows.map(r => (
                <tr key={`${r.course_id}-${r.plant_id}`} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{r.course_title}</td>
                  <td className="px-4 py-3 text-gray-600">{r.plant_code}</td>
                  <td className="px-4 py-3 text-right text-gray-600">{r.target}</td>
                  <td className="px-4 py-3 text-right text-gray-900">{r.trained}</td>
                  <td className="px-4 py-3"><Bar pct={r.pct} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {phishing.campaigns.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg overflow-x-auto mb-4">
          <p className="px-4 pt-3 text-xs font-semibold text-gray-600 uppercase tracking-wide">
            {t("reporting.kpi.training.phishing_title")}
          </p>
          <table className="w-full text-sm">
            <thead>
              <tr className={THEAD}>
                <th className={TH}>{t("reporting.kpi.training.col_date")}</th>
                <th className={TH}>{t("reporting.kpi.training.col_site")}</th>
                <th className={TH}>{t("reporting.kpi.training.col_campaign")}</th>
                <th className="px-4 py-3 text-right">{t("reporting.kpi.training.col_sent")}</th>
                <th className="px-4 py-3 text-right">{t("reporting.kpi.training.col_clicked")}</th>
                <th className="px-4 py-3 text-right">{t("reporting.kpi.training.col_reported")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {phishing.campaigns.map(c => (
                <tr key={c.session_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-xs text-gray-500">{c.held_on}</td>
                  <td className="px-4 py-3 text-gray-600">{c.plant_code ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-900">
                    {c.course_title}
                    {c.legacy && (
                      <span className="ml-2 text-xs bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">
                        {t("reporting.kpi.training.legacy")}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-600">{c.sent}</td>
                  <td className="px-4 py-3 text-right text-red-600">{c.clicked}</td>
                  <td className="px-4 py-3 text-right text-green-700">{c.reported}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {data.expiring_evidence.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg overflow-x-auto">
          <p className="px-4 pt-3 text-xs font-semibold text-gray-600 uppercase tracking-wide">
            {t("reporting.kpi.training.expiring_title")}
          </p>
          <table className="w-full text-sm">
            <thead>
              <tr className={THEAD}>
                <th className={TH}>{t("reporting.kpi.col_course")}</th>
                <th className={TH}>{t("reporting.kpi.training.col_site")}</th>
                <th className={TH}>{t("reporting.kpi.training.col_date")}</th>
                <th className={TH}>{t("reporting.kpi.training.col_valid_until")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.expiring_evidence.map(e => (
                <tr key={e.session_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{e.course_title}</td>
                  <td className="px-4 py-3 text-gray-600">{e.plant_code ?? "—"}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">{e.held_on}</td>
                  <td className={`px-4 py-3 text-xs ${e.expired ? "text-red-600 font-semibold" : "text-orange-600"}`}>
                    {e.valid_until}{e.expired && ` · ${t("reporting.kpi.training.expired")}`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
