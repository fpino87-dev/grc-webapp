import { useQuery } from "@tanstack/react-query";
import { reportingApi } from "../../api/endpoints/reporting";
import { RiskBadge, NdaStatusBadge } from "./supplierBadges";
import { useTranslation } from "react-i18next";

export function NdaTab() {
  const { t } = useTranslation();
  const { data, isLoading } = useQuery({
    queryKey: ["kpi-overview", ""],
    queryFn: () => reportingApi.kpiOverview(),
    retry: false,
  });

  const nda = data?.supplier_nda;

  return (
    <div>
      {isLoading && <div className="py-8 text-center text-gray-400 text-sm">{t("common.loading")}</div>}
      {nda && (
        <>
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="bg-white border border-green-300 rounded-lg p-4">
              <p className="text-xs text-gray-500 uppercase tracking-wide">{t("suppliers.nda.kpi_covered")}</p>
              <p className="text-3xl font-bold text-green-600 mt-1">{nda.covered}</p>
            </div>
            <div className="bg-white border border-yellow-300 rounded-lg p-4">
              <p className="text-xs text-gray-500 uppercase tracking-wide">{t("suppliers.nda.kpi_expiring")}</p>
              <p className="text-3xl font-bold text-yellow-600 mt-1">{nda.expiring_soon}</p>
            </div>
            <div className="bg-white border border-red-300 rounded-lg p-4">
              <p className="text-xs text-gray-500 uppercase tracking-wide">{t("suppliers.nda.kpi_expired")} / {t("suppliers.nda.kpi_missing")}</p>
              <p className="text-3xl font-bold text-red-600 mt-1">{nda.expired + nda.without_nda}</p>
              <p className="text-xs text-gray-400 mt-1">{nda.expired} {t("suppliers.nda.status_expired").toLowerCase()} · {nda.without_nda} {t("suppliers.nda.status_missing").toLowerCase()}</p>
            </div>
          </div>

          {nda.suppliers.length === 0 ? (
            <div className="text-center text-gray-400 py-8">{t("suppliers.nda.no_suppliers")}</div>
          ) : (
            <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">{t("suppliers.nda.col_supplier")}</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">{t("suppliers.nda.col_risk")}</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">{t("suppliers.nda.col_status")}</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">{t("suppliers.nda.col_expiry")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {nda.suppliers.map(s => (
                    <tr key={s.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-medium text-gray-800">{s.name}</td>
                      <td className="px-4 py-3"><RiskBadge level={s.risk_level} /></td>
                      <td className="px-4 py-3"><NdaStatusBadge status={s.nda_status} /></td>
                      <td className="px-4 py-3 text-sm text-gray-500">
                        {s.expiry_date
                          ? <>{s.expiry_date}{s.days_to_expiry !== null && s.days_to_expiry <= 90 && <span className="ml-1 text-orange-500 text-xs">({s.days_to_expiry}gg)</span>}</>
                          : "—"
                        }
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
