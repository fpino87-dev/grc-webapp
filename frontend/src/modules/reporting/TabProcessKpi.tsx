import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { reportingApi, type SupplierNdaEntry } from "../../api/endpoints/reporting";
import { useAuthStore } from "../../store/auth";
import { TrainingKpiSection } from "./TrainingKpiSection";

// Tab "Indicatori di processo": copertura dei documenti obbligatori, tempi medi
// di risoluzione, NDA dei fornitori e formazione. Segue il sito scelto in alto
// come gli altri tab del Reporting.

function CoverageBar({ pct, colorClass }: { pct: number; colorClass: string }) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-gray-100 rounded-full h-2 overflow-hidden">
        <div className={`h-2 rounded-full ${colorClass}`} style={{ width: `${Math.min(pct, 100)}%` }} />
      </div>
      <span className="text-xs font-semibold w-10 text-right">{pct}%</span>
    </div>
  );
}

function MttrBadge({ days }: { days: number | null }) {
  const { t } = useTranslation();
  if (days === null) return <span className="text-xs text-gray-400">—</span>;
  const color = days <= 14 ? "text-green-600" : days <= 30 ? "text-yellow-600" : "text-red-600";
  return <span className={`text-sm font-semibold ${color}`}>{t("reporting.kpi.days", { n: days })}</span>;
}

const NDA_STATUS_CLASSES: Record<SupplierNdaEntry["nda_status"], string> = {
  ok: "bg-green-100 text-green-800",
  expiring: "bg-yellow-100 text-yellow-800",
  expired: "bg-red-100 text-red-800",
  draft: "bg-gray-100 text-gray-700",
  missing: "bg-red-50 text-red-600 border border-red-200",
};

const RISK_CLASSES: Record<string, string> = {
  basso: "bg-green-100 text-green-800",
  medio: "bg-amber-100 text-amber-800",
  alto: "bg-red-100 text-red-800",
  critico: "bg-red-200 text-red-900 font-bold",
};

// Ordine dei fornitori da sistemare: prima i più urgenti, poi per rischio.
const NDA_ORDER: Record<string, number> = { expired: 0, missing: 1, expiring: 2, draft: 3, ok: 4 };
const RISK_ORDER: Record<string, number> = { critico: 0, alto: 1, medio: 2, basso: 3 };

function SectionTitle({ title, hint }: { title: string; hint?: string }) {
  return (
    <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">
      {title}
      {hint && <span className="ml-2 text-xs text-gray-400 normal-case font-normal">{hint}</span>}
    </h3>
  );
}

export function TabProcessKpi() {
  const { t } = useTranslation();
  const selectedPlant = useAuthStore(s => s.selectedPlant);

  const { data, isLoading } = useQuery({
    queryKey: ["kpi-overview", selectedPlant?.id],
    queryFn: () => reportingApi.kpiOverview(selectedPlant?.id),
    retry: false,
  });

  if (isLoading) return <div className="text-sm text-gray-400 py-8 text-center">{t("reporting.loading")}</div>;
  if (!data) return <div className="p-8 text-center text-gray-400">{t("reporting.no_data")}</div>;

  const ndaToFix = (data.supplier_nda?.suppliers ?? [])
    .filter(s => s.nda_status !== "ok")
    .sort((a, b) =>
      (NDA_ORDER[a.nda_status] - NDA_ORDER[b.nda_status])
      || ((RISK_ORDER[a.risk_level] ?? 9) - (RISK_ORDER[b.risk_level] ?? 9))
      || a.name.localeCompare(b.name),
    );

  return (
    <div className="space-y-8">
      {/* ── Documenti obbligatori ── */}
      <section>
        <SectionTitle title={t("reporting.kpi.section_docs")} />
        {data.required_docs === null ? (
          <p className="text-sm text-gray-500 bg-gray-50 border border-gray-200 rounded-lg px-4 py-3">
            {t("reporting.kpi.docs_select_plant")}
          </p>
        ) : data.required_docs.length === 0 ? (
          <p className="text-sm text-gray-400 italic">{t("reporting.kpi.no_frameworks")}</p>
        ) : (
          <div className="bg-white border border-gray-200 rounded-lg overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200 text-xs font-semibold text-gray-600 uppercase tracking-wide">
                  <th className="px-4 py-3 text-left">{t("reporting.kpi.col_framework")}</th>
                  <th className="px-4 py-3 text-right">{t("reporting.kpi.col_total")}</th>
                  <th className="px-4 py-3 text-right"><span className="inline-block w-2 h-2 rounded-full bg-green-500 mr-1" />{t("reporting.kpi.col_approved")}</th>
                  <th className="px-4 py-3 text-right"><span className="inline-block w-2 h-2 rounded-full bg-yellow-400 mr-1" />{t("reporting.kpi.col_draft")}</th>
                  <th className="px-4 py-3 text-right"><span className="inline-block w-2 h-2 rounded-full bg-red-500 mr-1" />{t("reporting.kpi.col_missing")}</th>
                  <th className="px-4 py-3 text-left w-48">{t("reporting.kpi.col_coverage")}</th>
                  <th className="px-4 py-3 text-left w-48">{t("reporting.kpi.col_mandatory")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.required_docs.map(row => (
                  <tr key={row.framework} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-900">{row.framework_name}</td>
                    {row.no_required_docs ? (
                      <td colSpan={6} className="px-4 py-3 text-xs text-gray-400 italic">
                        {t("reporting.kpi.no_required_docs_configured")}
                      </td>
                    ) : (
                      <>
                        <td className="px-4 py-3 text-right text-gray-600">{row.total}</td>
                        <td className="px-4 py-3 text-right text-green-700 font-medium">{row.green}</td>
                        <td className="px-4 py-3 text-right text-yellow-600 font-medium">{row.yellow}</td>
                        <td className="px-4 py-3 text-right text-red-600 font-medium">{row.red}</td>
                        <td className="px-4 py-3"><CoverageBar pct={row.pct_coverage} colorClass="bg-blue-500" /></td>
                        <td className="px-4 py-3">
                          {row.mandatory_total === 0
                            ? <span className="text-xs text-gray-400">—</span>
                            : <CoverageBar pct={row.pct_mandatory} colorClass={row.pct_mandatory >= 100 ? "bg-green-500" : row.pct_mandatory >= 70 ? "bg-yellow-400" : "bg-red-500"} />}
                        </td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* ── Tempi medi di risoluzione ── */}
      <section>
        <SectionTitle title={t("reporting.kpi.section_mttr")} hint={t("reporting.kpi.mttr_hint")} />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">{t("reporting.kpi.mttr_findings")}</p>
            <div className="space-y-2">
              {(["major", "minor", "observation"] as const).map(type => (
                <div key={type} className="flex justify-between items-center">
                  <span className="text-xs text-gray-600">{t(`reporting.kpi.finding_${type}`)}</span>
                  <div className="text-right">
                    <MttrBadge days={data.mttr.findings[type].avg_days} />
                    <span className="block text-xs text-gray-400">({data.mttr.findings[type].count} {t("reporting.kpi.closed")})</span>
                  </div>
                </div>
              ))}
              <div className="border-t border-gray-100 pt-2 flex justify-between items-center">
                <span className="text-xs font-semibold text-gray-700">{t("reporting.kpi.total")}</span>
                <div className="text-right">
                  <MttrBadge days={data.mttr.findings.all.avg_days} />
                  <span className="block text-xs text-gray-400">({data.mttr.findings.all.count})</span>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">{t("reporting.kpi.mttr_incidents")}</p>
            <div className="space-y-2">
              {(["critica", "alta", "media", "bassa"] as const).map(sev => {
                const entry = data.mttr.incidents.by_severity[sev];
                if (!entry) return null;
                return (
                  <div key={sev} className="flex justify-between items-center">
                    <span className="text-xs text-gray-600">{t(`reporting.kpi.severity_${sev}`)}</span>
                    <div className="text-right">
                      <MttrBadge days={entry.avg_days} />
                      <span className="block text-xs text-gray-400">({entry.count})</span>
                    </div>
                  </div>
                );
              })}
              <div className="border-t border-gray-100 pt-2 flex justify-between items-center">
                <span className="text-xs font-semibold text-gray-700">{t("reporting.kpi.total")}</span>
                <div className="text-right">
                  <MttrBadge days={data.mttr.incidents.all.avg_days} />
                  <span className="block text-xs text-gray-400">({data.mttr.incidents.all.count})</span>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">{t("reporting.kpi.mttr_tasks")}</p>
            <div className="flex justify-between items-center mt-2">
              <span className="text-xs text-gray-600">{t("reporting.kpi.tasks_completed")}</span>
              <div className="text-right">
                <MttrBadge days={data.mttr.tasks.all.avg_days} />
                <span className="block text-xs text-gray-400">({data.mttr.tasks.all.count})</span>
              </div>
            </div>
            <p className="text-xs text-gray-400 mt-4">{t("reporting.kpi.mttr_tasks_note")}</p>
          </div>
        </div>
      </section>

      {/* ── NDA fornitori ── */}
      {data.supplier_nda && (
        <section>
          <div className="flex items-baseline justify-between gap-3 flex-wrap">
            <SectionTitle title={t("reporting.kpi.section_nda")} hint={t("reporting.kpi.nda_hint")} />
            <Link to="/suppliers" className="text-xs text-primary-600 hover:underline mb-3">{t("reporting.kpi.nda_go_suppliers")} →</Link>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div className="bg-white border border-green-300 rounded-lg p-4">
              <p className="text-xs text-gray-500 uppercase tracking-wide">{t("suppliers.nda.kpi_covered")}</p>
              <p className="text-3xl font-bold text-green-600 mt-1">{data.supplier_nda.covered}</p>
            </div>
            <div className="bg-white border border-yellow-300 rounded-lg p-4">
              <p className="text-xs text-gray-500 uppercase tracking-wide">{t("suppliers.nda.kpi_expiring")}</p>
              <p className="text-3xl font-bold text-yellow-600 mt-1">{data.supplier_nda.expiring_soon}</p>
            </div>
            <div className="bg-white border border-red-300 rounded-lg p-4">
              <p className="text-xs text-gray-500 uppercase tracking-wide">{t("suppliers.nda.kpi_expired")}</p>
              <p className="text-3xl font-bold text-red-600 mt-1">{data.supplier_nda.expired}</p>
            </div>
            <div className="bg-white border border-gray-200 rounded-lg p-4">
              <p className="text-xs text-gray-500 uppercase tracking-wide">{t("suppliers.nda.kpi_missing")}</p>
              <p className="text-3xl font-bold text-gray-600 mt-1">{data.supplier_nda.without_nda}</p>
            </div>
          </div>
          {ndaToFix.length === 0 ? (
            <p className="text-sm text-gray-400 italic">{t("reporting.kpi.nda_all_ok")}</p>
          ) : (
            <div className="bg-white border border-gray-200 rounded-lg overflow-x-auto">
              <p className="px-4 py-2 text-xs text-gray-500 border-b border-gray-100">{t("reporting.kpi.nda_to_fix", { count: ndaToFix.length })}</p>
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200 text-xs font-semibold text-gray-600 uppercase tracking-wide">
                    <th className="px-4 py-3 text-left">{t("suppliers.nda.col_supplier")}</th>
                    <th className="px-4 py-3 text-left">{t("suppliers.nda.col_risk")}</th>
                    <th className="px-4 py-3 text-left">{t("suppliers.nda.col_status")}</th>
                    <th className="px-4 py-3 text-left">{t("suppliers.nda.col_expiry")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {ndaToFix.map(s => (
                    <tr key={s.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-medium text-gray-900">{s.name}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${RISK_CLASSES[s.risk_level] ?? "bg-gray-100 text-gray-600"}`}>
                          {t(`suppliers.risk.${s.risk_level}`, { defaultValue: s.risk_level })}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${NDA_STATUS_CLASSES[s.nda_status] ?? NDA_STATUS_CLASSES.missing}`}>
                          {t(`suppliers.nda.status_${s.nda_status}`)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-500">
                        {s.expiry_date
                          ? <>{s.expiry_date}{s.days_to_expiry !== null && s.days_to_expiry <= 90 && s.days_to_expiry >= 0 && <span className="ml-1 text-orange-600">({t("reporting.kpi.days", { n: s.days_to_expiry })})</span>}</>
                          : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {/* ── Formazione ── */}
      <TrainingKpiSection data={data.training} />
    </div>
  );
}
