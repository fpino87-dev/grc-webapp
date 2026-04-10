import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { reportingApi, type BiaBcpRow, type TopRisk, type ThreatBreakdown, type Nis2CategoryBreakdown, type HeatmapCell, type RequiredDocsCoverage } from "../../api/endpoints/reporting";
import { plantsApi } from "../../api/endpoints/plants";
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
  const selectedPlant = useAuthStore(s => s.selectedPlant);

  const STATUS_LABELS: Record<string, string> = {
    compliant: "Compliant",
    parziale: t("reporting.status.parziale"),
    gap: "Gap",
    na: "N/A",
    non_valutato: t("reporting.status.non_valutato"),
  };

  const { data: dash, isLoading: dashLoading } = useQuery({
    queryKey: ["reporting-dashboard", selectedPlant?.id],
    queryFn: () => reportingApi.dashboard(selectedPlant?.id),
    retry: false,
  });

  const { data: comp, isLoading: compLoading } = useQuery({
    queryKey: ["reporting-compliance", selectedPlant?.id],
    queryFn: () => reportingApi.compliance(selectedPlant?.id ? { plant: selectedPlant.id } : undefined),
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
          <KpiCard label={t("reporting.kpi.pct_compliant")} value={`${(dash.pct_compliant ?? 0).toFixed(1)}%`} sub={`${dash.controls_compliant ?? 0} / ${dash.controls_total ?? 0}`} highlight />
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

// ─────────────────────────────────────────────────────────────────────────────
// Risk / BIA / BCP tab
// ─────────────────────────────────────────────────────────────────────────────

function scoreColor(score: number): string {
  if (score > 14) return "text-red-600";
  if (score > 7) return "text-yellow-600";
  return "text-green-600";
}

function scoreBg(score: number): string {
  if (score > 14) return "bg-red-100 text-red-700";
  if (score > 7) return "bg-yellow-100 text-yellow-700";
  return "bg-green-100 text-green-700";
}

function heatmapColor(score: number, count: number): string {
  if (count === 0) return "bg-gray-50 text-gray-300";
  if (score > 14) return "bg-red-500 text-white";
  if (score > 7) return "bg-yellow-400 text-gray-800";
  return "bg-green-400 text-white";
}

function KpiTile({
  label, value, sub, variant = "neutral",
}: {
  label: string; value: string | number; sub?: string; variant?: "neutral" | "danger" | "warning" | "ok";
}) {
  const colors = {
    neutral: "border-gray-200 text-gray-900",
    danger:  "border-red-300 text-red-700",
    warning: "border-yellow-300 text-yellow-700",
    ok:      "border-green-300 text-green-700",
  };
  return (
    <div className={`bg-white rounded-lg border p-4 flex flex-col gap-1 ${colors[variant]}`}>
      <span className="text-xs text-gray-500 font-medium uppercase tracking-wide">{label}</span>
      <span className={`text-3xl font-bold ${colors[variant]}`}>{value}</span>
      {sub && <span className="text-xs text-gray-400">{sub}</span>}
    </div>
  );
}

function RiskHeatmap({ cells }: { cells: HeatmapCell[] }) {
  const { t } = useTranslation();
  const cellMap = new Map(cells.map(c => [`${c.prob}-${c.impact}`, c.count]));
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">{t("reporting.risk_bia_bcp.heatmap_title")}</h3>
      <div className="flex gap-2 items-end">
        {/* Y axis label */}
        <div className="flex flex-col items-center justify-center h-full">
          <span className="text-xs text-gray-400 writing-mode-vertical -rotate-90 whitespace-nowrap mb-2">{t("reporting.risk_bia_bcp.probability")}</span>
        </div>
        <div>
          {/* Grid: prob on Y (5 top → 1 bottom), impact on X (1→5) */}
          {[5, 4, 3, 2, 1].map(prob => (
            <div key={prob} className="flex gap-1 mb-1 items-center">
              <span className="text-xs text-gray-400 w-4 text-right">{prob}</span>
              {[1, 2, 3, 4, 5].map(imp => {
                const count = cellMap.get(`${prob}-${imp}`) ?? 0;
                const score = prob * imp;
                return (
                  <div
                    key={imp}
                    className={`w-12 h-12 rounded flex items-center justify-center text-sm font-bold transition-all ${heatmapColor(score, count)}`}
                    title={`P${prob}×I${imp} = ${score} | ${count} ${t("reporting.risk_bia_bcp.risks")}`}
                  >
                    {count > 0 ? count : ""}
                  </div>
                );
              })}
            </div>
          ))}
          {/* X axis */}
          <div className="flex gap-1 mt-1 ml-5">
            {[1, 2, 3, 4, 5].map(imp => (
              <div key={imp} className="w-12 text-center text-xs text-gray-400">{imp}</div>
            ))}
          </div>
          <div className="ml-5 mt-1 text-center text-xs text-gray-400">{t("reporting.risk_bia_bcp.impact")}</div>
        </div>
        {/* Legend */}
        <div className="ml-4 flex flex-col gap-2 text-xs text-gray-600">
          <div className="flex items-center gap-1"><span className="w-4 h-4 rounded bg-red-500 inline-block"></span> &gt;14 {t("reporting.risk_bia_bcp.legend_red")}</div>
          <div className="flex items-center gap-1"><span className="w-4 h-4 rounded bg-yellow-400 inline-block"></span> 8–14 {t("reporting.risk_bia_bcp.legend_yellow")}</div>
          <div className="flex items-center gap-1"><span className="w-4 h-4 rounded bg-green-400 inline-block"></span> ≤7 {t("reporting.risk_bia_bcp.legend_green")}</div>
        </div>
      </div>
    </div>
  );
}

function TopRisksTable({ risks }: { risks: TopRisk[] }) {
  const { t } = useTranslation();
  if (risks.length === 0) return null;
  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <h3 className="text-sm font-semibold text-gray-700 px-4 py-3 border-b border-gray-100">
        {t("reporting.risk_bia_bcp.top_risks_title")}
      </h3>
      <table className="w-full text-sm">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            <th className="text-left px-4 py-2 font-medium text-gray-600">{t("reporting.risk_bia_bcp.col_risk")}</th>
            <th className="text-left px-4 py-2 font-medium text-gray-600">{t("reporting.risk_bia_bcp.col_owner")}</th>
            <th className="text-center px-3 py-2 font-medium text-gray-600">{t("reporting.risk_bia_bcp.col_score_residual")}</th>
            <th className="text-center px-3 py-2 font-medium text-gray-600">{t("reporting.risk_bia_bcp.col_score_inherent")}</th>
            <th className="text-left px-3 py-2 font-medium text-gray-600">NIS2</th>
            <th className="text-left px-3 py-2 font-medium text-gray-600">{t("reporting.risk_bia_bcp.col_treatment")}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {risks.map(r => (
            <tr key={r.id} className="hover:bg-gray-50">
              <td className="px-4 py-2">
                <div className="font-medium text-gray-800 max-w-xs truncate">{r.name}</div>
                <div className="text-xs text-gray-400">{r.threat_label}</div>
              </td>
              <td className="px-4 py-2 text-gray-600 text-xs">{r.owner_name}</td>
              <td className="px-3 py-2 text-center">
                <span className={`font-bold text-base ${scoreColor(r.score)}`}>{r.score}</span>
              </td>
              <td className="px-3 py-2 text-center text-gray-400 text-sm">
                {r.inherent_score ?? "—"}
              </td>
              <td className="px-3 py-2">
                {r.nis2_relevance ? (
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    r.nis2_relevance === "significativo" ? "bg-red-100 text-red-700" :
                    r.nis2_relevance === "potenzialmente_significativo" ? "bg-yellow-100 text-yellow-700" :
                    "bg-gray-100 text-gray-600"
                  }`}>
                    {r.nis2_art21_category.replace("art21_", "Art.21(2)(").concat(")")}
                  </span>
                ) : <span className="text-gray-300">—</span>}
              </td>
              <td className="px-3 py-2">
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                  r.formally_accepted ? "bg-blue-100 text-blue-700" :
                  r.needs_revaluation ? "bg-orange-100 text-orange-700" :
                  "bg-gray-100 text-gray-600"
                }`}>
                  {r.formally_accepted ? "✓ Accettato" : r.needs_revaluation ? "⚠ Rivalutare" : r.treatment}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ThreatBreakdownChart({ data }: { data: ThreatBreakdown[] }) {
  const { t } = useTranslation();
  if (data.length === 0) return null;
  const chartData = data.slice(0, 8).map(d => ({
    name: d.label.length > 22 ? d.label.slice(0, 20) + "…" : d.label,
    residuo: d.residual_avg,
    inerente: d.inherent_avg,
  }));
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">{t("reporting.risk_bia_bcp.threat_chart_title")}</h3>
      <ResponsiveContainer width="100%" height={Math.max(200, chartData.length * 42)}>
        <BarChart layout="vertical" data={chartData} margin={{ top: 4, right: 24, left: 120, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 11 }} domain={[0, 25]} />
          <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={120} />
          <Tooltip />
          <Bar dataKey="inerente" name={t("reporting.risk_bia_bcp.bar_inherent")} fill="#f87171" radius={[0, 3, 3, 0]} />
          <Bar dataKey="residuo" name={t("reporting.risk_bia_bcp.bar_residual")} fill="#60a5fa" radius={[0, 3, 3, 0]} />
        </BarChart>
      </ResponsiveContainer>
      <p className="text-xs text-gray-400 mt-2">{t("reporting.risk_bia_bcp.threat_chart_note")}</p>
    </div>
  );
}

function Nis2Chart({ data }: { data: Nis2CategoryBreakdown[] }) {
  const { t } = useTranslation();
  if (data.length === 0) return null;
  const chartData = data.map(d => ({
    name: d.category.replace("art21_", "").toUpperCase(),
    significativo: d.significativo,
    potenzialmente: d.potenzialmente_significativo,
    non_significativo: d.non_significativo,
    fullLabel: d.label,
  }));
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">{t("reporting.risk_bia_bcp.nis2_chart_title")}</h3>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={chartData} margin={{ top: 4, right: 16, left: 4, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="name" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
          <Tooltip
            formatter={(value, name) => [value, name]}
            labelFormatter={label => {
              const item = chartData.find(d => d.name === label);
              return item?.fullLabel ?? label;
            }}
          />
          <Bar dataKey="significativo" name={t("reporting.risk_bia_bcp.nis2_sig")} stackId="a" fill="#ef4444" />
          <Bar dataKey="potenzialmente" name={t("reporting.risk_bia_bcp.nis2_pot")} stackId="a" fill="#f59e0b" />
          <Bar dataKey="non_significativo" name={t("reporting.risk_bia_bcp.nis2_non")} stackId="a" fill="#86efac" radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function BiaBcpTable({ rows }: { rows: BiaBcpRow[] }) {
  const { t } = useTranslation();
  if (rows.length === 0) return (
    <div className="bg-white rounded-lg border border-gray-200 p-8 text-center text-gray-400 text-sm">
      {t("reporting.no_data")}
    </div>
  );

  const critLabel = (c: number | null) => {
    if (!c) return <span className="text-gray-300">—</span>;
    const colors = ["", "bg-green-100 text-green-700", "bg-green-100 text-green-700", "bg-yellow-100 text-yellow-700", "bg-orange-100 text-orange-700", "bg-red-100 text-red-700"];
    return <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${colors[c] ?? "bg-gray-100"}`}>{c}</span>;
  };

  const bcpStatusLabel = (s: string | null) => {
    if (!s) return <span className="text-xs text-gray-300">Nessuno</span>;
    const map: Record<string, string> = { approvato: "bg-green-100 text-green-700", in_revisione: "bg-yellow-100 text-yellow-700", bozza: "bg-gray-100 text-gray-600" };
    return <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${map[s] ?? "bg-gray-100"}`}>{s}</span>;
  };

  const testResult = (result: string | null, overdue: boolean) => {
    if (!result && overdue) return <span className="text-xs text-orange-600 font-medium">⚠ Scaduto</span>;
    if (!result) return <span className="text-gray-300 text-xs">—</span>;
    return <span className={`text-xs font-medium ${result === "pass" ? "text-green-600" : "text-red-600"}`}>{result === "pass" ? "✓ Pass" : "✗ Fail"}</span>;
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <h3 className="text-sm font-semibold text-gray-700 px-4 py-3 border-b border-gray-100">
        {t("reporting.risk_bia_bcp.bia_bcp_table_title")}
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-2 font-medium text-gray-600 min-w-[180px]">{t("reporting.risk_bia_bcp.col_process")}</th>
              <th className="text-center px-3 py-2 font-medium text-gray-600">{t("reporting.risk_bia_bcp.col_criticality")}</th>
              <th className="text-center px-3 py-2 font-medium text-gray-600">RTO</th>
              <th className="text-center px-3 py-2 font-medium text-gray-600">RPO</th>
              <th className="text-center px-3 py-2 font-medium text-red-600">🔴</th>
              <th className="text-center px-3 py-2 font-medium text-yellow-600">🟡</th>
              <th className="text-center px-3 py-2 font-medium text-green-600">🟢</th>
              <th className="text-left px-3 py-2 font-medium text-gray-600">BCP</th>
              <th className="text-left px-3 py-2 font-medium text-gray-600">{t("reporting.risk_bia_bcp.col_last_test")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {rows.map(row => (
              <tr key={row.process_id} className={`hover:bg-gray-50 ${row.test_overdue && row.bcp_plans_count > 0 ? "bg-orange-50" : ""}`}>
                <td className="px-4 py-2">
                  <div className="font-medium text-gray-800">{row.process_name}</div>
                  <div className="text-xs text-gray-400">{row.bia_status}</div>
                </td>
                <td className="px-3 py-2 text-center">{critLabel(row.criticality)}</td>
                <td className="px-3 py-2 text-center text-xs text-gray-600">
                  {row.rto_target_hours != null ? `${row.rto_target_hours}h` : "—"}
                </td>
                <td className="px-3 py-2 text-center text-xs text-gray-600">
                  {row.rpo_target_hours != null ? `${row.rpo_target_hours}h` : "—"}
                </td>
                <td className="px-3 py-2 text-center font-semibold text-red-600">{row.risks_red || "—"}</td>
                <td className="px-3 py-2 text-center font-semibold text-yellow-600">{row.risks_yellow || "—"}</td>
                <td className="px-3 py-2 text-center font-semibold text-green-600">{row.risks_green || "—"}</td>
                <td className="px-3 py-2">
                  <div>{bcpStatusLabel(row.bcp_status)}</div>
                  {row.next_test_date && (
                    <div className={`text-xs mt-0.5 ${row.test_overdue ? "text-orange-600" : "text-gray-400"}`}>
                      {t("reporting.risk_bia_bcp.next_test")}: {row.next_test_date}
                    </div>
                  )}
                </td>
                <td className="px-3 py-2">
                  {testResult(row.last_test_result, row.test_overdue)}
                  {row.last_test_date && (
                    <div className="text-xs text-gray-400">{row.last_test_date}</div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function TabRiskBiaBcp() {
  const { t } = useTranslation();
  const selectedPlant = useAuthStore(s => s.selectedPlant);
  const { data, isLoading } = useQuery({
    queryKey: ["reporting-risk-bia-bcp", selectedPlant?.id],
    queryFn: () => reportingApi.riskBiaBcp(selectedPlant?.id),
    retry: false,
  });

  if (isLoading) return <div className="p-8 text-center text-gray-400">{t("reporting.loading")}</div>;
  if (!data) return <div className="p-8 text-center text-gray-400">{t("reporting.no_data")}</div>;

  const { kpis, heatmap, top_risks, by_threat, nis2_breakdown, bia_bcp_table } = data;

  return (
    <div className="space-y-6">
      {/* KPI header */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3">
        <KpiTile label={t("reporting.risk_bia_bcp.kpi_total")} value={kpis.risks_total} />
        <KpiTile label={t("reporting.risk_bia_bcp.kpi_red")} value={kpis.risks_red} variant={kpis.risks_red > 0 ? "danger" : "ok"} />
        <KpiTile label={t("reporting.risk_bia_bcp.kpi_yellow")} value={kpis.risks_yellow} variant={kpis.risks_yellow > 0 ? "warning" : "ok"} />
        <KpiTile label={t("reporting.risk_bia_bcp.kpi_revaluation")} value={kpis.risks_needs_revaluation} variant={kpis.risks_needs_revaluation > 0 ? "warning" : "ok"} sub={t("reporting.risk_bia_bcp.kpi_revaluation_sub")} />
        <KpiTile label={t("reporting.risk_bia_bcp.kpi_accepted")} value={kpis.risks_formally_accepted} variant="ok" sub={`/ ${kpis.risks_total}`} />
        <KpiTile label={t("reporting.risk_bia_bcp.kpi_bia_no_bcp")} value={kpis.bia_critical_no_bcp} variant={kpis.bia_critical_no_bcp > 0 ? "danger" : "ok"} sub={t("reporting.risk_bia_bcp.kpi_bia_no_bcp_sub")} />
        <KpiTile label={t("reporting.risk_bia_bcp.kpi_bcp_overdue")} value={kpis.bcp_test_overdue} variant={kpis.bcp_test_overdue > 0 ? "warning" : "ok"} sub={t("reporting.risk_bia_bcp.kpi_bcp_overdue_sub")} />
      </div>

      {/* Heatmap + NIS2 chart side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RiskHeatmap cells={heatmap} />
        <Nis2Chart data={nis2_breakdown} />
      </div>

      {/* Threat breakdown */}
      <ThreatBreakdownChart data={by_threat} />

      {/* Top 10 risks */}
      <TopRisksTable risks={top_risks} />

      {/* BIA-BCP correlation table */}
      <BiaBcpTable rows={bia_bcp_table} />
    </div>
  );
}

// ── KPI Overview tab ──────────────────────────────────────────────────────────

const FW_LABELS: Record<string, string> = {
  ISO27001: "ISO 27001", NIS2: "NIS2", TISAX_L2: "TISAX L2", TISAX_L3: "TISAX L3",
};

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
  if (days === null) return <span className="text-xs text-gray-400">—</span>;
  const color = days <= 14 ? "text-green-600" : days <= 30 ? "text-yellow-600" : "text-red-600";
  return <span className={`text-sm font-semibold ${color}`}>{days}gg</span>;
}

function TabKpi() {
  const { t } = useTranslation();
  const [plantId, setPlantId] = useState<string>("");

  const { data: plants } = useQuery({ queryKey: ["plants"], queryFn: () => plantsApi.list(), retry: false });

  const { data, isLoading } = useQuery({
    queryKey: ["kpi-overview", plantId],
    queryFn: () => reportingApi.kpiOverview(plantId || undefined),
    retry: false,
  });

  return (
    <div className="space-y-8">
      {/* Plant filter */}
      <div className="flex items-center gap-3">
        <label className="text-xs font-medium text-gray-600">{t("reporting.kpi.plant_label")}</label>
        <select
          value={plantId}
          onChange={e => setPlantId(e.target.value)}
          className="border border-gray-300 rounded px-2 py-1.5 text-sm"
        >
          <option value="">{t("reporting.kpi.all_plants")}</option>
          {plants?.map(p => <option key={p.id} value={p.id}>[{p.code}] {p.name}</option>)}
        </select>
      </div>

      {isLoading && <div className="text-sm text-gray-400 py-8 text-center">{t("notification_settings.loading")}</div>}

      {data && (
        <>
          {/* ── 1. Required docs coverage ── */}
          <section>
            <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">
              {t("reporting.kpi.section_docs")}
            </h3>
            {data.required_docs.length === 0 ? (
              <p className="text-sm text-gray-400 italic">{t("reporting.kpi.no_frameworks")}</p>
            ) : (
              <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-200 text-xs font-semibold text-gray-600 uppercase tracking-wide">
                      <th className="px-4 py-3 text-left">{t("reporting.kpi.col_framework")}</th>
                      <th className="px-4 py-3 text-right">{t("reporting.kpi.col_total")}</th>
                      <th className="px-4 py-3 text-right">
                        <span className="inline-block w-2 h-2 rounded-full bg-green-500 mr-1" />
                        {t("reporting.kpi.col_approved")}
                      </th>
                      <th className="px-4 py-3 text-right">
                        <span className="inline-block w-2 h-2 rounded-full bg-yellow-400 mr-1" />
                        {t("reporting.kpi.col_draft")}
                      </th>
                      <th className="px-4 py-3 text-right">
                        <span className="inline-block w-2 h-2 rounded-full bg-red-500 mr-1" />
                        {t("reporting.kpi.col_missing")}
                      </th>
                      <th className="px-4 py-3 text-left w-48">{t("reporting.kpi.col_coverage")}</th>
                      <th className="px-4 py-3 text-left w-48">{t("reporting.kpi.col_mandatory")}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {data.required_docs.map((row: RequiredDocsCoverage) => (
                      <tr key={row.framework} className="hover:bg-gray-50">
                        <td className="px-4 py-3 font-medium text-gray-900">{FW_LABELS[row.framework] ?? row.framework}</td>
                        <td className="px-4 py-3 text-right text-gray-600">{row.total}</td>
                        <td className="px-4 py-3 text-right text-green-700 font-medium">{row.green}</td>
                        <td className="px-4 py-3 text-right text-yellow-600 font-medium">{row.yellow}</td>
                        <td className="px-4 py-3 text-right text-red-600 font-medium">{row.red}</td>
                        <td className="px-4 py-3"><CoverageBar pct={row.pct_coverage} colorClass="bg-blue-500" /></td>
                        <td className="px-4 py-3"><CoverageBar pct={row.pct_mandatory} colorClass={row.pct_mandatory >= 100 ? "bg-green-500" : row.pct_mandatory >= 70 ? "bg-yellow-400" : "bg-red-500"} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {/* ── 2. MTTR ── */}
          <section>
            <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">
              {t("reporting.kpi.section_mttr")}
              <span className="ml-2 text-xs text-gray-400 normal-case font-normal">{t("reporting.kpi.mttr_hint")}</span>
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Findings */}
              <div className="bg-white border border-gray-200 rounded-lg p-4">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">{t("reporting.kpi.mttr_findings")}</p>
                <div className="space-y-2">
                  {(["major", "minor", "observation"] as const).map(type => (
                    <div key={type} className="flex justify-between items-center">
                      <span className="text-xs text-gray-600 capitalize">{t(`reporting.kpi.finding_${type}`)}</span>
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

              {/* Incidents */}
              <div className="bg-white border border-gray-200 rounded-lg p-4">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">{t("reporting.kpi.mttr_incidents")}</p>
                <div className="space-y-2">
                  {(["critica", "alta", "media", "bassa"] as const).map(sev => {
                    const entry = data.mttr.incidents.by_severity[sev];
                    if (!entry) return null;
                    return (
                      <div key={sev} className="flex justify-between items-center">
                        <span className="text-xs text-gray-600 capitalize">{t(`reporting.kpi.severity_${sev}`)}</span>
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

              {/* Tasks */}
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

          {/* ── 3. Training ── */}
          <section>
            <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">
              {t("reporting.kpi.section_training")}
            </h3>
            {/* Summary card */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
              <div className="bg-white border border-gray-200 rounded-lg p-4">
                <p className="text-xs text-gray-500 uppercase tracking-wide">{t("reporting.kpi.training_users")}</p>
                <p className="text-3xl font-bold text-gray-900 mt-1">{data.training.total_users}</p>
                <p className="text-xs text-gray-400 mt-1">{t("reporting.kpi.training_grc_perimeter")}</p>
              </div>
              <div className="bg-white border border-gray-200 rounded-lg p-4">
                <p className="text-xs text-gray-500 uppercase tracking-wide">{t("reporting.kpi.training_mandatory_courses")}</p>
                <p className="text-3xl font-bold text-gray-900 mt-1">{data.training.mandatory_courses_count}</p>
              </div>
              <div className={`bg-white border rounded-lg p-4 ${data.training.pct_all_mandatory >= 80 ? "border-green-300" : data.training.pct_all_mandatory >= 50 ? "border-yellow-300" : "border-red-300"}`}>
                <p className="text-xs text-gray-500 uppercase tracking-wide">{t("reporting.kpi.training_all_done")}</p>
                <p className={`text-3xl font-bold mt-1 ${data.training.pct_all_mandatory >= 80 ? "text-green-600" : data.training.pct_all_mandatory >= 50 ? "text-yellow-600" : "text-red-600"}`}>
                  {data.training.pct_all_mandatory}%
                </p>
                <p className="text-xs text-gray-400 mt-1">{data.training.users_all_mandatory_completed}/{data.training.total_users} {t("reporting.kpi.training_users_suffix")}</p>
              </div>
            </div>

            {/* Per-course table */}
            {data.training.courses.length === 0 ? (
              <p className="text-sm text-gray-400 italic">{t("reporting.kpi.no_mandatory_courses")}</p>
            ) : (
              <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-200 text-xs font-semibold text-gray-600 uppercase tracking-wide">
                      <th className="px-4 py-3 text-left">{t("reporting.kpi.col_course")}</th>
                      <th className="px-4 py-3 text-center">{t("reporting.kpi.col_source")}</th>
                      <th className="px-4 py-3 text-right">{t("reporting.kpi.col_enrolled")}</th>
                      <th className="px-4 py-3 text-right">{t("reporting.kpi.col_completed")}</th>
                      <th className="px-4 py-3 text-right">{t("reporting.kpi.col_not_enrolled")}</th>
                      <th className="px-4 py-3 text-left w-40">{t("reporting.kpi.col_completion")}</th>
                      <th className="px-4 py-3 text-right">{t("reporting.kpi.col_deadline")}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {data.training.courses.map(c => (
                      <tr key={c.id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 font-medium text-gray-900">{c.title}</td>
                        <td className="px-4 py-3 text-center">
                          <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">{c.source}</span>
                        </td>
                        <td className="px-4 py-3 text-right text-gray-600">{c.enrolled}</td>
                        <td className="px-4 py-3 text-right text-green-700 font-medium">{c.completed}</td>
                        <td className="px-4 py-3 text-right text-red-600">{c.not_enrolled}</td>
                        <td className="px-4 py-3">
                          <CoverageBar
                            pct={c.pct_completed}
                            colorClass={c.pct_completed >= 80 ? "bg-green-500" : c.pct_completed >= 50 ? "bg-yellow-400" : "bg-red-500"}
                          />
                        </td>
                        <td className="px-4 py-3 text-right text-xs text-gray-500">{c.deadline ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}

export function ReportingPage() {
  const { t } = useTranslation();
  const [tab, setTab] = useState<"compliance" | "owner" | "risk_bia_bcp" | "kpi">("compliance");

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-gray-900">{t("reporting.title")}</h2>
      </div>

      <div className="flex gap-1 mb-6 border-b border-gray-200">
        {(["compliance", "owner", "risk_bia_bcp", "kpi"] as const).map(tabKey => (
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

      {tab === "compliance" && <TabCompliance />}
      {tab === "owner" && <TabOwner />}
      {tab === "risk_bia_bcp" && <TabRiskBiaBcp />}
      {tab === "kpi" && <TabKpi />}
    </div>
  );
}
