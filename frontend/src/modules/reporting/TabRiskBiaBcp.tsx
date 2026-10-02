import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import {
  reportingApi,
  type AssetTypeBreakdown,
  type BiaBcpRow,
  type HeatmapCell,
  type Nis2CategoryBreakdown,
  type RiskBiaBcpData,
  type TopRisk,
} from "../../api/endpoints/reporting";
import { useAuthStore } from "../../store/auth";
import { CLASS_CELL, RISK_CLASSES, classBadge, type RiskClass } from "../risk/riskClasses";

type Variant = "neutral" | "danger" | "warning" | "ok";

function KpiTile({ label, value, sub, variant = "neutral" }: {
  label: string; value: string | number; sub?: string; variant?: Variant;
}) {
  const colors: Record<Variant, string> = {
    neutral: "border-gray-200 text-gray-900",
    danger: "border-red-300 text-red-700",
    warning: "border-yellow-300 text-yellow-700",
    ok: "border-green-300 text-green-700",
  };
  return (
    <div className={`bg-white rounded-lg border p-4 flex flex-col gap-1 ${colors[variant]}`}>
      <span className="text-xs text-gray-500 font-medium uppercase tracking-wide">{label}</span>
      <span className={`text-3xl font-bold ${colors[variant]}`}>{value}</span>
      {sub && <span className="text-xs text-gray-400">{sub}</span>}
    </div>
  );
}

function Panel({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100">
        <h3 className="text-sm font-semibold text-gray-700">{title}</h3>
        {subtitle && <p className="text-xs text-gray-400 mt-0.5">{subtitle}</p>}
      </div>
      {children}
    </div>
  );
}

function ClassBadge({ cls }: { cls: RiskClass | "" }) {
  const { t } = useTranslation();
  if (!cls) return <span className="text-gray-300">—</span>;
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full border font-medium whitespace-nowrap ${classBadge(cls)}`}>
      {t(`risk.classes.${cls}`)}
    </span>
  );
}

// ── Rischi ────────────────────────────────────────────────────────────────────

function RiskHeatmap({ cells }: { cells: HeatmapCell[] }) {
  const { t } = useTranslation();
  const cellMap = new Map(cells.map(c => [`${c.prob}-${c.impact}`, c]));
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">{t("reporting.risk_bia_bcp.heatmap_title")}</h3>
      <div className="flex gap-3 items-start flex-wrap">
        <div>
          <p className="text-xs text-gray-400 mb-1">{t("reporting.risk_bia_bcp.probability")} ↑</p>
          {[5, 4, 3, 2, 1].map(prob => (
            <div key={prob} className="flex gap-1 mb-1 items-center">
              <span className="text-xs text-gray-400 w-4 text-right">{prob}</span>
              {[1, 2, 3, 4, 5].map(imp => {
                const cell = cellMap.get(`${prob}-${imp}`);
                const count = cell?.count ?? 0;
                const cls = cell?.class;
                return (
                  <div
                    key={imp}
                    className={`w-11 h-11 rounded flex items-center justify-center text-sm font-bold ${
                      cls ? CLASS_CELL[cls] : "bg-gray-50"
                    } ${count === 0 ? "opacity-30" : ""}`}
                    title={t("reporting.risk_bia_bcp.heatmap_cell", {
                      prob, imp, cls: cls ? t(`risk.classes.${cls}`) : "—", count,
                    })}
                  >
                    {count > 0 ? count : ""}
                  </div>
                );
              })}
            </div>
          ))}
          <div className="flex gap-1 mt-1 ml-5">
            {[1, 2, 3, 4, 5].map(imp => (
              <div key={imp} className="w-11 text-center text-xs text-gray-400">{imp}</div>
            ))}
          </div>
          <p className="ml-5 mt-1 text-xs text-gray-400">{t("reporting.risk_bia_bcp.impact")} →</p>
        </div>
        <div className="flex flex-col gap-2 text-xs text-gray-600">
          {[...RISK_CLASSES].reverse().map(cls => (
            <div key={cls} className="flex items-center gap-1.5">
              <span className={`w-4 h-4 rounded inline-block ${CLASS_CELL[cls]}`} /> {t(`risk.classes.${cls}`)}
            </div>
          ))}
          <p className="text-gray-400 max-w-[12rem] mt-1">{t("reporting.risk_bia_bcp.heatmap_note")}</p>
        </div>
      </div>
    </div>
  );
}

function TreatmentBadge({ r }: { r: TopRisk }) {
  const { t } = useTranslation();
  if (r.accepted) {
    return <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-blue-100 text-blue-700">{t("reporting.risk_bia_bcp.accepted")}</span>;
  }
  if (!r.treatment) return <span className="text-gray-300">—</span>;
  return <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-gray-100 text-gray-600">{t(`risk.treatment_${r.treatment}`)}</span>;
}

function TopRisksTable({ risks }: { risks: TopRisk[] }) {
  const { t } = useTranslation();
  if (risks.length === 0) return null;
  return (
    <Panel title={t("reporting.risk_bia_bcp.top_risks_title")}>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-2 font-medium text-gray-600">{t("reporting.risk_bia_bcp.col_risk")}</th>
              <th className="text-left px-4 py-2 font-medium text-gray-600">{t("reporting.risk_bia_bcp.col_owner")}</th>
              <th className="text-left px-3 py-2 font-medium text-gray-600">{t("reporting.risk_bia_bcp.col_class")}</th>
              <th className="text-left px-3 py-2 font-medium text-gray-600">NIS2</th>
              <th className="text-left px-3 py-2 font-medium text-gray-600">{t("reporting.risk_bia_bcp.col_treatment")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {risks.map(r => (
              <tr key={r.id} className="hover:bg-gray-50">
                <td className="px-4 py-2">
                  <Link to="/risk" state={{ openRiskId: r.id }} className="font-medium text-gray-800 hover:text-primary-600 hover:underline max-w-xs truncate block" title={r.name}>
                    {r.name}
                  </Link>
                  <div className="text-xs text-gray-400">
                    {[r.threat_code, r.asset_type, r.plant_name ?? t("reporting.risk_bia_bcp.group_register")].filter(Boolean).join(" · ")}
                  </div>
                </td>
                <td className="px-4 py-2 text-gray-600 text-xs">{r.owner_name}</td>
                <td className="px-3 py-2 whitespace-nowrap">
                  <ClassBadge cls={r.current_class} />
                  {r.expected_class && r.expected_class !== r.current_class && (
                    <span className="text-xs text-gray-400"> → <ClassBadge cls={r.expected_class} /></span>
                  )}
                </td>
                <td className="px-3 py-2">
                  {r.nis2_art21_category ? (
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full font-medium whitespace-nowrap ${
                        r.significant_incident_potential ? "bg-red-100 text-red-700" : "bg-gray-100 text-gray-600"
                      }`}
                      title={[
                        t(`risk.nis2_art21.${r.nis2_art21_category}`),
                        r.significant_incident_potential ? t("reporting.risk_bia_bcp.nis2_significant") : "",
                      ].filter(Boolean).join(" · ")}
                    >
                      {r.nis2_art21_category.replace("art21_", "Art.21(2)(")})
                    </span>
                  ) : <span className="text-gray-300">—</span>}
                </td>
                <td className="px-3 py-2"><TreatmentBadge r={r} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}

function AssetTypeChart({ data }: { data: AssetTypeBreakdown[] }) {
  const { t } = useTranslation();
  if (data.length === 0) return null;
  const chartData = data.map(d => ({
    name: t(`risk.asset_types.${d.asset_type}`, { defaultValue: d.asset_type }),
    rossi: d.rossi,
    gialli: d.gialli,
    verdi: d.verdi,
  }));
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">{t("reporting.risk_bia_bcp.asset_type_chart_title")}</h3>
      <ResponsiveContainer width="100%" height={Math.max(180, chartData.length * 40)}>
        <BarChart layout="vertical" data={chartData} margin={{ top: 4, right: 24, left: 8, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 11 }} allowDecimals={false} />
          <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={110} />
          <Tooltip />
          <Bar dataKey="rossi" name={t("reporting.risk_bia_bcp.legend_red")} stackId="a" fill="#ea580c" />
          <Bar dataKey="gialli" name={t("reporting.risk_bia_bcp.legend_yellow")} stackId="a" fill="#facc15" />
          <Bar dataKey="verdi" name={t("reporting.risk_bia_bcp.legend_green")} stackId="a" fill="#22c55e" radius={[0, 3, 3, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function Nis2Chart({ data }: { data: Nis2CategoryBreakdown[] }) {
  const { t } = useTranslation();
  if (data.length === 0) return null;
  const chartData = data.map(d => ({
    name: d.category.replace("art21_", "").toUpperCase(),
    in_scope: d.in_scope,
    significant: d.significant_incident_potential,
    fullLabel: t(`risk.nis2_art21.${d.category}`, { defaultValue: d.label }),
  }));
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">{t("reporting.risk_bia_bcp.nis2_chart_title")}</h3>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={chartData} margin={{ top: 4, right: 16, left: 4, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="name" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
          <Tooltip labelFormatter={label => chartData.find(d => d.name === label)?.fullLabel ?? label} />
          <Bar dataKey="in_scope" name={t("reporting.risk_bia_bcp.nis2_in_scope")} fill="#60a5fa" />
          <Bar dataKey="significant" name={t("reporting.risk_bia_bcp.nis2_significant")} fill="#ef4444" radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function RisksView({ data }: { data: RiskBiaBcpData }) {
  const { t } = useTranslation();
  const { kpis } = data;
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        <KpiTile
          label={t("reporting.risk_bia_bcp.kpi_untreated_high")}
          value={kpis.risks_untreated_high}
          variant={kpis.risks_untreated_high > 0 ? "danger" : "ok"}
          sub={t("reporting.risk_bia_bcp.kpi_untreated_high_sub")}
        />
        {kpis.risks_inherited != null && (
          <KpiTile label={t("reporting.risk_bia_bcp.kpi_inherited")} value={kpis.risks_inherited}
                   variant={(kpis.risks_inherited_untreated_high ?? 0) > 0 ? "warning" : "ok"}
                   sub={t("reporting.risk_bia_bcp.kpi_inherited_sub", { high: kpis.risks_inherited_untreated_high ?? 0 })} />
        )}
        <KpiTile label={t("reporting.risk_bia_bcp.kpi_total")} value={kpis.risks_total} />
        <KpiTile label={t("reporting.risk_bia_bcp.kpi_red")} value={kpis.risks_red} variant={kpis.risks_red > 0 ? "warning" : "ok"}
                 sub={t("reporting.risk_bia_bcp.kpi_red_sub", { critical: kpis.risks_by_class.critical, high: kpis.risks_by_class.high })} />
        <KpiTile label={t("reporting.risk_bia_bcp.kpi_yellow")} value={kpis.risks_yellow} variant={kpis.risks_yellow > 0 ? "warning" : "ok"} />
        <KpiTile label={t("reporting.risk_bia_bcp.kpi_accepted")} value={kpis.risks_accepted} variant="ok" sub={`/ ${kpis.risks_total}`} />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RiskHeatmap cells={data.heatmap} />
        <Nis2Chart data={data.nis2_breakdown} />
      </div>
      <TopRisksTable risks={data.top_risks} />
      <AssetTypeChart data={data.by_asset_type} />
    </div>
  );
}

// ── Continuità ────────────────────────────────────────────────────────────────

function BiaBcpTable({ rows }: { rows: BiaBcpRow[] }) {
  const { t } = useTranslation();
  if (rows.length === 0) {
    return <div className="bg-white rounded-lg border border-gray-200 p-8 text-center text-gray-400 text-sm">{t("reporting.no_data")}</div>;
  }

  const critBadge = (c: number | null) => {
    if (!c) return <span className="text-gray-300">—</span>;
    const colors = ["", "bg-green-100 text-green-700", "bg-green-100 text-green-700", "bg-yellow-100 text-yellow-700", "bg-orange-100 text-orange-700", "bg-red-100 text-red-700"];
    return <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${colors[c] ?? "bg-gray-100"}`}>{c}</span>;
  };

  const bcpBadge = (s: string | null) => {
    if (!s) return <span className="text-xs text-red-600 font-medium">{t("reporting.risk_bia_bcp.no_bcp")}</span>;
    const cls = s === "approvato" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600";
    return <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${cls}`}>{t(`reporting.risk_bia_bcp.bcp_status.${s}`, { defaultValue: s })}</span>;
  };

  const testResult = (result: string | null, overdue: boolean) => {
    if (!result && overdue) return <span className="text-xs text-orange-600 font-medium">{t("reporting.risk_bia_bcp.test_overdue")}</span>;
    if (!result) return <span className="text-gray-300 text-xs">—</span>;
    if (result === "superato") return <span className="text-xs font-medium text-green-600">{t("reporting.risk_bia_bcp.test_pass")}</span>;
    if (result === "parziale") return <span className="text-xs font-medium text-yellow-600">{t("reporting.risk_bia_bcp.test_partial")}</span>;
    return <span className="text-xs font-medium text-red-600">{t("reporting.risk_bia_bcp.test_fail")}</span>;
  };

  return (
    <Panel title={t("reporting.risk_bia_bcp.bia_bcp_table_title")} subtitle={t("reporting.risk_bia_bcp.bia_bcp_table_hint")}>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-2 font-medium text-gray-600 min-w-[180px]">{t("reporting.risk_bia_bcp.col_process")}</th>
              <th className="text-center px-3 py-2 font-medium text-gray-600">{t("reporting.risk_bia_bcp.col_criticality")}</th>
              <th className="text-center px-3 py-2 font-medium text-gray-600">RTO</th>
              <th className="text-center px-3 py-2 font-medium text-gray-600">RPO</th>
              <th className="text-center px-3 py-2 font-medium text-gray-600" colSpan={3}>{t("reporting.risk_bia_bcp.col_risks")}</th>
              <th className="text-left px-3 py-2 font-medium text-gray-600">BCP</th>
              <th className="text-left px-3 py-2 font-medium text-gray-600">{t("reporting.risk_bia_bcp.col_last_test")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {rows.map(row => (
              <tr key={row.process_id} className={`hover:bg-gray-50 ${row.test_overdue ? "bg-orange-50" : ""}`}>
                <td className="px-4 py-2">
                  <Link to="/bia" className="font-medium text-gray-800 hover:text-primary-600 hover:underline">{row.process_name}</Link>
                  <div className="text-xs text-gray-400">{t(`reporting.risk_bia_bcp.bia_status.${row.bia_status}`, { defaultValue: row.bia_status })}</div>
                </td>
                <td className="px-3 py-2 text-center">{critBadge(row.criticality)}</td>
                <td className="px-3 py-2 text-center text-xs text-gray-600">{row.rto_target_hours != null ? `${row.rto_target_hours}h` : "—"}</td>
                <td className="px-3 py-2 text-center text-xs text-gray-600">{row.rpo_target_hours != null ? `${row.rpo_target_hours}h` : "—"}</td>
                <td className="px-2 py-2 text-center font-semibold text-red-600" title={t("reporting.risk_bia_bcp.legend_red")}>{row.risks_red || "—"}</td>
                <td className="px-2 py-2 text-center font-semibold text-yellow-600" title={t("reporting.risk_bia_bcp.legend_yellow")}>{row.risks_yellow || "—"}</td>
                <td className="px-2 py-2 text-center font-semibold text-green-600" title={t("reporting.risk_bia_bcp.legend_green")}>{row.risks_green || "—"}</td>
                <td className="px-3 py-2">
                  <div>{bcpBadge(row.bcp_status)}</div>
                  {row.next_test_date && (
                    <div className={`text-xs mt-0.5 ${row.test_overdue ? "text-orange-600" : "text-gray-400"}`}>
                      {t("reporting.risk_bia_bcp.next_test")}: {row.next_test_date}
                    </div>
                  )}
                </td>
                <td className="px-3 py-2">
                  {testResult(row.last_test_result, row.test_overdue)}
                  {row.last_test_date && <div className="text-xs text-gray-400">{row.last_test_date}</div>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}

function ContinuityView({ data }: { data: RiskBiaBcpData }) {
  const { t } = useTranslation();
  const { kpis } = data;
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <KpiTile label={t("reporting.risk_bia_bcp.kpi_processes")} value={data.bia_bcp_table.length} />
        <KpiTile label={t("reporting.risk_bia_bcp.kpi_bia_no_bcp")} value={kpis.bia_critical_no_bcp} variant={kpis.bia_critical_no_bcp > 0 ? "danger" : "ok"} sub={t("reporting.risk_bia_bcp.kpi_bia_no_bcp_sub")} />
        <KpiTile label={t("reporting.risk_bia_bcp.kpi_bia_test_expired")} value={kpis.bia_critical_test_expired ?? 0} variant={(kpis.bia_critical_test_expired ?? 0) > 0 ? "warning" : "ok"} sub={t("reporting.risk_bia_bcp.kpi_bia_test_expired_sub")} />
        <KpiTile label={t("reporting.risk_bia_bcp.kpi_bcp_overdue")} value={kpis.bcp_test_overdue} variant={kpis.bcp_test_overdue > 0 ? "warning" : "ok"} sub={t("reporting.risk_bia_bcp.kpi_bcp_overdue_sub")} />
      </div>
      <BiaBcpTable rows={data.bia_bcp_table} />
    </div>
  );
}

const VIEWS = ["risks", "continuity"] as const;
type View = typeof VIEWS[number];

export function TabRiskBiaBcp() {
  const { t } = useTranslation();
  const selectedPlant = useAuthStore(s => s.selectedPlant);
  // Sotto-sezione nell'indirizzo (?view=), accanto a ?tab=.
  const [searchParams, setSearchParams] = useSearchParams();
  const requested = searchParams.get("view");
  const view: View = (VIEWS as readonly string[]).includes(requested ?? "") ? (requested as View) : "risks";
  const setView = (v: View) => {
    const params = new URLSearchParams(searchParams);
    params.set("view", v);
    setSearchParams(params, { replace: true });
  };

  const { data, isLoading } = useQuery({
    queryKey: ["reporting-risk-bia-bcp", selectedPlant?.id],
    queryFn: () => reportingApi.riskBiaBcp(selectedPlant?.id),
    retry: false,
  });

  if (isLoading) return <div className="p-8 text-center text-gray-400">{t("reporting.loading")}</div>;
  if (!data) return <div className="p-8 text-center text-gray-400">{t("reporting.no_data")}</div>;

  return (
    <div className="space-y-6">
      <div className="inline-flex rounded-lg border border-gray-200 bg-white p-1 gap-1">
        {VIEWS.map(v => (
          <button
            key={v}
            onClick={() => setView(v)}
            className={`px-3 py-1.5 text-sm rounded-md font-medium transition-colors ${
              view === v ? "bg-primary-600 text-white" : "text-gray-600 hover:bg-gray-50"
            }`}
          >
            {t(`reporting.risk_bia_bcp.views.${v}`)}
          </button>
        ))}
      </div>
      {view === "risks" && <RisksView data={data} />}
      {view === "continuity" && <ContinuityView data={data} />}
    </div>
  );
}
