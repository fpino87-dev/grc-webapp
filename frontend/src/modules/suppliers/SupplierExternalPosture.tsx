import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { osintApi } from "../../api/endpoints/osint";
import { GradeBadge } from "../osint/shared";

/** Postura esterna del fornitore dal modulo OSINT: voto, problemi critici e
 *  storico delle segnalazioni (evidenza di monitoraggio NIS2 art. 21.2.d).
 *  Solo consultazione: la correzione spetta al fornitore. */
export function SupplierExternalPosture({ supplierId }: { supplierId: string }) {
  const { t } = useTranslation();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["osint-supplier-posture", supplierId],
    queryFn: () => osintApi.supplierPosture(supplierId),
    retry: false,
  });
  if (isLoading) return <p className="p-4 text-sm text-gray-400">{t("common.loading")}</p>;
  if (isError) return <p className="p-4 text-sm text-gray-400">{t("suppliers.external.no_access")}</p>;
  if (!data || data.length === 0) return <p className="p-4 text-sm text-gray-400">{t("suppliers.external.none")}</p>;
  return (
    <div className="p-4 space-y-3">
      <p className="text-xs text-gray-500">{t("suppliers.external.intro")}</p>
      {data.map(d => (
        <div key={d.entity} className="rounded-xl border border-gray-200 bg-white p-4 space-y-3">
          <div className="flex items-center gap-3">
            <GradeBadge grade={d.grade} security={d.security} size="lg" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">{d.domain}</p>
              <p className="text-xs text-gray-500">
                {d.last_scan_at ? t("suppliers.external.last_scan", { date: new Date(d.last_scan_at).toLocaleDateString() }) : t("suppliers.external.never_scanned")}
              </p>
            </div>
            <Link to="/osint" className="text-xs text-primary-700 hover:underline">{t("suppliers.external.open_osint")} →</Link>
          </div>
          {d.critical_open.length === 0 ? (
            <p className="text-xs text-green-700">✓ {t("suppliers.external.no_critical")}</p>
          ) : (
            <ul className="space-y-1">
              {d.critical_open.map(f => (
                <li key={f.id} className="text-xs text-gray-700">
                  🔴 {t(`osint.finding_title.${f.code}`, { defaultValue: f.code })} ·{" "}
                  {f.reported_at
                    ? <span className={f.overdue ? "text-amber-700" : "text-gray-500"}>{t("suppliers.external.reported_on", { date: new Date(f.reported_at).toLocaleDateString() })}</span>
                    : <span className="text-red-700">{t("suppliers.external.not_reported")}</span>}
                </li>
              ))}
            </ul>
          )}
          {d.reports.length > 0 && (
            <details className="text-xs">
              <summary className="cursor-pointer text-gray-500">{t("suppliers.external.history", { count: d.reports.length })}</summary>
              <ul className="mt-1 space-y-0.5">
                {d.reports.map(r => (
                  <li key={r.id} className="text-gray-600" title={r.note || undefined}>
                    {t(`osint.finding_title.${r.code}`, { defaultValue: r.code })} · {new Date(r.reported_at).toLocaleDateString()}
                    {r.resolved_at ? ` → ✓ ${new Date(r.resolved_at).toLocaleDateString()}` : ""}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </div>
      ))}
    </div>
  );
}
