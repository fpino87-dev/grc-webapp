import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { reportingApi } from "../../api/endpoints/reporting";
import { useAuthStore } from "../../store/auth";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

interface KpiCardProps {
  label: string;
  value: string | number;
  sub?: string;
  highlight?: boolean;
}

function KpiCard({ label, value, sub, highlight }: KpiCardProps) {
  return (
    <div className={`bg-white rounded-lg border p-5 flex flex-col gap-1 ${highlight ? "border-primary-400" : "border-gray-200"}`}>
      <span className="text-xs text-gray-500 font-medium uppercase tracking-wide">{label}</span>
      <span className={`text-3xl font-bold ${highlight ? "text-primary-600" : "text-gray-900"}`}>{value}</span>
      {sub && <span className="text-xs text-gray-400">{sub}</span>}
    </div>
  );
}

const STATUS_COLORS: Record<string, string> = {
  compliant: "bg-green-500",
  parziale: "bg-yellow-400",
  gap: "bg-red-500",
  na: "bg-gray-300",
  non_valutato: "bg-gray-200",
};

const BAR_COLORS: Record<string, string> = {
  compliant: "#22c55e",
  parziale: "#facc15",
  gap: "#ef4444",
  na: "#d1d5db",
  non_valutato: "#e5e7eb",
};

function TabCompliance() {
  const { t } = useTranslation();

  const STATUS_LABELS: Record<string, string> = {
    compliant: "Compliant",
    parziale: t("reporting.status.parziale"),
    gap: "Gap",
    na: "N/A",
    non_valutato: t("reporting.status.non_valutato"),
  };

  const { data: dash, isLoading: dashLoading } = useQuery({
    queryKey: ["reporting-dashboard"],
    queryFn: () => reportingApi.dashboard(),
    retry: false,
  });

  const { data: comp, isLoading: compLoading } = useQuery({
    queryKey: ["reporting-compliance"],
    queryFn: () => reportingApi.compliance(),
    retry: false,
  });

  const byStatus = comp?.by_status ?? {};
  const total = comp?.total ?? 0;

  const barData = Object.entries(byStatus).map(([status, count]) => ({
    status: STATUS_LABELS[status] ?? status,
    count,
    fill: BAR_COLORS[status] ?? "#9ca3af",
  }));

  return (
    <>
      {dashLoading ? (
        <div className="p-8 text-center text-gray-400">{t("reporting.loading_kpi")}</div>
      ) : dash ? (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
          <KpiCard label={t("reporting.kpi.active_sites")} value={dash.plants_active} />
          <KpiCard label={t("reporting.kpi.open_incidents")} value={dash.incidents_open} highlight={dash.incidents_open > 0} />
          <KpiCard label={t("reporting.kpi.total_controls")} value={dash.controls_total} />
          <KpiCard label={t("reporting.kpi.pct_compliant")} value={`${dash.pct_compliant.toFixed(1)}%`} sub={`${dash.controls_compliant} / ${dash.controls_total}`} highlight />
          <KpiCard label={t("reporting.kpi.gap_controls")} value={dash.controls_gap} highlight={dash.controls_gap > 0} />
        </div>
      ) : null}

      {compLoading ? (
        <div className="p-8 text-center text-gray-400">{t("reporting.loading_compliance")}</div>
      ) : comp && total > 0 ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <h3 className="text-sm font-semibold text-gray-700 mb-4">{t("reporting.compliance.distribution_title", { total })}</h3>
            <div className="flex rounded overflow-hidden h-8 mb-4">
              {Object.entries(byStatus).map(([status, count]) => {
                const pct = total > 0 ? (count / total) * 100 : 0;
                if (pct === 0) return null;
                return (
                  <div
                    key={status}
                    title={`${STATUS_LABELS[status] ?? status}: ${count} (${pct.toFixed(1)}%)`}
                    className={`${STATUS_COLORS[status] ?? "bg-gray-300"} transition-all`}
                    style={{ width: `${pct}%` }}
                  />
                );
              })}
            </div>
            <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2">
              {Object.entries(byStatus).map(([status, count]) => (
                <div key={status} className="flex items-center gap-1.5 text-xs text-gray-600">
                  <span className={`w-3 h-3 rounded-sm inline-block ${STATUS_COLORS[status] ?? "bg-gray-300"}`} />
                  {STATUS_LABELS[status] ?? status}: {count}
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <h3 className="text-sm font-semibold text-gray-700 mb-4">{t("reporting.compliance.by_status_title")}</h3>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={barData} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="status" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="count" name={t("reporting.compliance.bar_label")}>
                  {barData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      ) : (
        !compLoading && (
          <div className="bg-white rounded-lg border border-gray-200 p-8 text-center text-gray-400">
            {t("reporting.no_compliance_data")}
          </div>
        )
      )}
    </>
  );
}

function TabOwner() {
  const { t } = useTranslation();
  const selectedPlant = useAuthStore(s => s.selectedPlant);
  const { data, isLoading } = useQuery({
    queryKey: ["reporting-owner", selectedPlant?.id],
    queryFn: () => reportingApi.ownerReport(selectedPlant?.id),
    retry: false,
  });

  if (isLoading) return <div className="p-8 text-center text-gray-400">{t("reporting.loading")}</div>;

  const risks = data?.risks_by_owner ?? [];
  const tasks = data?.tasks_by_owner ?? [];

  const chartData = risks
    .filter(r => r.totale > 0)
    .map(r => ({
      name: r.owner_name.split(" ").slice(0, 2).join(" ") || "—",
      verdi: r.verdi,
      gialli: r.gialli,
      rossi: r.rossi,
    }));

  return (
    <div className="space-y-6">
      {chartData.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">{t("reporting.owner.risks_chart_title")}</h3>
          <ResponsiveContainer width="100%" height={Math.max(180, chartData.length * 36)}>
            <BarChart
              layout="vertical"
              data={chartData}
              margin={{ top: 4, right: 16, left: 80, bottom: 4 }}
            >
              <CartesianGrid strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 11 }} allowDecimals={false} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={80} />
              <Tooltip />
              <Bar dataKey="verdi" name={t("reporting.owner.bar_green")} stackId="a" fill="#22c55e" />
              <Bar dataKey="gialli" name={t("reporting.owner.bar_yellow")} stackId="a" fill="#eab308" />
              <Bar dataKey="rossi" name={t("reporting.owner.bar_red")} stackId="a" fill="#ef4444" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <h3 className="text-sm font-semibold text-gray-700 px-4 py-3 border-b border-gray-100">{t("reporting.owner.risks_table_title")}</h3>
        {risks.length === 0 ? (
          <p className="p-6 text-center text-gray-400 text-sm">{t("reporting.no_data")}</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-2 font-medium text-gray-600">{t("reporting.owner.col_owner")}</th>
                <th className="text-left px-4 py-2 font-medium text-gray-600">{t("reporting.owner.col_critical_processes")}</th>
                <th className="text-left px-4 py-2 font-medium text-gray-600">{t("reporting.owner.col_total_risks")}</th>
                <th className="text-left px-4 py-2 font-medium text-gray-600 text-red-600">{t("reporting.owner.col_red")}</th>
                <th className="text-left px-4 py-2 font-medium text-gray-600 text-yellow-600">{t("reporting.owner.col_yellow")}</th>
                <th className="text-left px-4 py-2 font-medium text-gray-600 text-green-600">{t("reporting.owner.col_green")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {risks.map((r, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-4 py-2">
                    <div className="font-medium text-gray-800">{r.owner_name || "—"}</div>
                    <div className="text-xs text-gray-400">{r.owner_email}</div>
                  </td>
                  <td className="px-4 py-2 text-gray-700">{r.processes}</td>
                  <td className="px-4 py-2 font-semibold text-gray-800">{r.totale}</td>
                  <td className="px-4 py-2 text-red-600 font-semibold">{r.rossi}</td>
                  <td className="px-4 py-2 text-yellow-600 font-semibold">{r.gialli}</td>
                  <td className="px-4 py-2 text-green-600 font-semibold">{r.verdi}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {tasks.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <h3 className="text-sm font-semibold text-gray-700 px-4 py-3 border-b border-gray-100">{t("reporting.owner.tasks_table_title")}</h3>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-2 font-medium text-gray-600">{t("reporting.owner.col_owner")}</th>
                <th className="text-left px-4 py-2 font-medium text-gray-600">{t("reporting.owner.col_open_tasks")}</th>
                <th className="text-left px-4 py-2 font-medium text-gray-600 text-red-600">{t("reporting.owner.col_overdue")}</th>
                <th className="text-left px-4 py-2 font-medium text-gray-600">{t("reporting.owner.col_completed_30d")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {tasks.map((t_row, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-4 py-2 font-medium text-gray-800">{t_row.owner_name || "—"}</td>
                  <td className="px-4 py-2 text-gray-700">{t_row.aperti}</td>
                  <td className="px-4 py-2 text-red-600 font-semibold">{t_row.scaduti}</td>
                  <td className="px-4 py-2 text-green-600">{t_row.completati_30gg}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export function ReportingPage() {
  const { t } = useTranslation();
  const [tab, setTab] = useState<"compliance" | "owner">("compliance");

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-gray-900">{t("reporting.title")}</h2>
      </div>

      <div className="flex gap-1 mb-6 border-b border-gray-200">
        {(["compliance", "owner"] as const).map(tabKey => (
          <button
            key={tabKey}
            onClick={() => setTab(tabKey)}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              tab === tabKey ? "border-primary-600 text-primary-600" : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t(`reporting.tabs.${tabKey}`)}
          </button>
        ))}
      </div>

      {tab === "compliance" ? <TabCompliance /> : <TabOwner />}
    </div>
  );
}
