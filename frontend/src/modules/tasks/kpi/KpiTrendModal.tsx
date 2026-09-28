import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  CartesianGrid,
} from "recharts";
import { kpiApi } from "../../../api/endpoints/kpi";
import i18n from "../../../i18n";

interface Props {
  kpiCode: string;
  kpiName: string;
  plantId?: string;
  onClose: () => void;
}

export function KpiTrendModal({ kpiCode, kpiName, plantId, onClose }: Props) {
  const { t } = useTranslation();

  const { data, isLoading } = useQuery({
    queryKey: ["kpi-trend", kpiCode, plantId],
    queryFn: () => kpiApi.getKpiTrend(kpiCode, plantId, 12),
    retry: false,
  });

  // Vista «Tutti i siti»: il grafico è il valore di organizzazione, sotto
  // l'ultimo valore di ogni sito.
  const { data: bySite } = useQuery({
    queryKey: ["kpi-by-site", kpiCode],
    queryFn: () => kpiApi.getKpiBySite(kpiCode),
    enabled: !plantId,
    retry: false,
  });
  const siteRows = bySite?.results ?? [];

  const chartData = (data?.results ?? []).map((s) => ({
    week: new Date(s.week_start).toLocaleDateString(i18n.language || "it", {
      day: "2-digit",
      month: "2-digit",
    }),
    value: s.value,
    status: s.status,
  }));

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div
        className="bg-white rounded-lg shadow-xl w-full max-w-2xl p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">{kpiName}</h3>
            <p className="text-xs text-gray-500">
              {t("kpi.trend.subtitle")} {data?.unit ? `(${data.unit})` : ""}
            </p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-700 text-xl leading-none">
            ✕
          </button>
        </div>

        {isLoading ? (
          <div className="p-8 text-center text-gray-400">{t("common.loading")}</div>
        ) : chartData.length === 0 ? (
          <div className="p-8 text-center text-gray-400">{t("kpi.trend.empty")}</div>
        ) : (
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
              <XAxis dataKey="week" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              {data?.threshold_warning != null && (
                <ReferenceLine
                  y={data.threshold_warning}
                  stroke="#f59e0b"
                  strokeDasharray="4 4"
                  label={{ value: t("kpi.trend.warning"), fontSize: 10, fill: "#f59e0b", position: "insideTopRight" }}
                />
              )}
              {data?.threshold_critical != null && (
                <ReferenceLine
                  y={data.threshold_critical}
                  stroke="#dc2626"
                  strokeDasharray="4 4"
                  label={{ value: t("kpi.trend.critical"), fontSize: 10, fill: "#dc2626", position: "insideBottomRight" }}
                />
              )}
              <Line
                type="monotone"
                dataKey="value"
                stroke="#2563eb"
                strokeWidth={2}
                dot={{ r: 3 }}
                connectNulls
              />
            </LineChart>
          </ResponsiveContainer>
        )}

        {!plantId && siteRows.length > 0 && (
          <div className="mt-4">
            <p className="text-xs font-medium text-gray-600 mb-1">{t("kpi.trend.by_site")}</p>
            <table className="w-full text-sm">
              <tbody className="divide-y divide-gray-100">
                {siteRows.map((s) => (
                  <tr key={s.id}>
                    <td className="py-1.5 text-gray-800">{s.plant_code}</td>
                    <td className="py-1.5 text-right font-medium text-gray-900">
                      {s.value != null ? `${s.value}${data?.unit ? ` ${data.unit}` : ""}` : "—"}
                    </td>
                    <td className="py-1.5 pl-3 w-28">
                      <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${STATUS_STYLE[s.status]}`}>
                        {t(`kpi.status.${s.status}`)}
                      </span>
                    </td>
                    <td className="py-1.5 pl-2 text-xs text-gray-400 truncate max-w-[14rem]" title={s.note || undefined}>
                      {s.note}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

const STATUS_STYLE: Record<string, string> = {
  ok: "bg-green-100 text-green-700",
  warning: "bg-yellow-100 text-yellow-700",
  critical: "bg-red-100 text-red-700",
  no_data: "bg-gray-100 text-gray-500",
};
