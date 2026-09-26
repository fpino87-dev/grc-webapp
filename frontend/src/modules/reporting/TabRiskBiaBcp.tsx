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
  type BiaBcpRow,
  type HeatmapCell,
  type Nis2CategoryBreakdown,
  type RiskBiaBcpData,
  type ThreatBreakdown,
  type TopRisk,
  type TreatmentRosi,
  type TreatmentRosiTotals,
} from "../../api/endpoints/reporting";
import { useAuthStore } from "../../store/auth";

// Formattazione valuta (€) locale-aware. Compatta per le tile (es. "1,2 Mln €"),
// estesa per le righe di tabella.
function formatEur(value: number, locale: string, compact = false): string {
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency: "EUR",
    notation: compact ? "compact" : "standard",
    maximumFractionDigits: compact ? 1 : 0,
  }).format(value || 0);
}

// Fasce di colore della heatmap e dei punteggi (convenzione 5×5: ≤7 basso,
// 8–14 medio, >14 alto). La soglia di accettabilità della direzione è a parte.
function scoreColor(score: number): string {
  if (score > 14) return "text-red-600";
  if (score > 7) return "text-yellow-600";
  return "text-green-600";
}

function heatmapColor(score: number, count: number): string {
  if (count === 0) return "bg-gray-50 text-gray-300";
  if (score > 14) return "bg-red-500 text-white";
  if (score > 7) return "bg-yellow-400 text-gray-800";
  return "bg-green-400 text-white";
}

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

// ── Rischi ────────────────────────────────────────────────────────────────────

function RiskHeatmap({ cells, threshold }: { cells: HeatmapCell[]; threshold: number }) {
  const { t } = useTranslation();
  const cellMap = new Map(cells.map(c => [`${c.prob}-${c.impact}`, c.count]));
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
                const count = cellMap.get(`${prob}-${imp}`) ?? 0;
                const score = prob * imp;
                const overAppetite = score > threshold;
                return (
                  <div
                    key={imp}
                    className={`w-11 h-11 rounded flex items-center justify-center text-sm font-bold ${heatmapColor(score, count)} ${overAppetite ? "ring-2 ring-offset-1 ring-gray-800" : ""}`}
                    title={t("reporting.risk_bia_bcp.heatmap_cell", { prob, imp, score, count })}
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
          <div className="flex items-center gap-1.5"><span className="w-4 h-4 rounded bg-red-500 inline-block" /> &gt;14 {t("reporting.risk_bia_bcp.legend_red")}</div>
          <div className="flex items-center gap-1.5"><span className="w-4 h-4 rounded bg-yellow-400 inline-block" /> 8–14 {t("reporting.risk_bia_bcp.legend_yellow")}</div>
          <div className="flex items-center gap-1.5"><span className="w-4 h-4 rounded bg-green-400 inline-block" /> ≤7 {t("reporting.risk_bia_bcp.legend_green")}</div>
          <div className="flex items-center gap-1.5 mt-1">
            <span className="w-4 h-4 rounded ring-2 ring-offset-1 ring-gray-800 inline-block" />
            {t("reporting.risk_bia_bcp.legend_appetite", { threshold })}
          </div>
        </div>
      </div>
    </div>
  );
}

function TreatmentBadge({ r }: { r: TopRisk }) {
  const { t } = useTranslation();
  if (r.formally_accepted) {
    return <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-blue-100 text-blue-700">{t("reporting.risk_bia_bcp.accepted")}</span>;
  }
  if (r.needs_revaluation) {
    return <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-orange-100 text-orange-700">{t("reporting.risk_bia_bcp.revaluate")}</span>;
  }
  if (!r.treatment) return <span className="text-gray-300">—</span>;
  return <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-gray-100 text-gray-600">{t(`risk.treatment_${r.treatment}`)}</span>;
}

function TopRisksTable({ risks }: { risks: TopRisk[] }) {
  const { t, i18n } = useTranslation();
  if (risks.length === 0) return null;
  return (
    <Panel title={t("reporting.risk_bia_bcp.top_risks_title")}>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-2 font-medium text-gray-600">{t("reporting.risk_bia_bcp.col_risk")}</th>
              <th className="text-left px-4 py-2 font-medium text-gray-600">{t("reporting.risk_bia_bcp.col_owner")}</th>
              <th className="text-center px-3 py-2 font-medium text-gray-600">{t("reporting.risk_bia_bcp.col_score_residual")}</th>
              <th className="text-center px-3 py-2 font-medium text-gray-600">{t("reporting.risk_bia_bcp.col_score_inherent")}</th>
              <th className="text-right px-3 py-2 font-medium text-gray-600">{t("reporting.risk_bia_bcp.col_ale_residual")}</th>
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
                  <div className="text-xs text-gray-400">{r.threat_category ? t(`risk.threat_cat.${r.threat_category}`) : "—"}</div>
                </td>
                <td className="px-4 py-2 text-gray-600 text-xs">{r.owner_name}</td>
                <td className="px-3 py-2 text-center">
                  <span className={`font-bold text-base ${scoreColor(r.score)}`}>{r.score}</span>
                  {r.over_appetite && (
                    <span className="ml-1 text-xs text-gray-800" title={t("reporting.risk_bia_bcp.over_appetite_hint")}>▲</span>
                  )}
                </td>
                <td className="px-3 py-2 text-center text-gray-400 text-sm">{r.inherent_score ?? "—"}</td>
                <td className="px-3 py-2 text-right text-sm tabular-nums whitespace-nowrap">
                  {r.ale > 0 ? <span className="font-medium text-gray-700">{formatEur(r.ale, i18n.language)}</span> : <span className="text-gray-300">—</span>}
                </td>
                <td className="px-3 py-2">
                  {r.nis2_art21_category ? (
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full font-medium whitespace-nowrap ${
                        r.nis2_relevance === "significativo" ? "bg-red-100 text-red-700" :
                        r.nis2_relevance === "potenzialmente_significativo" ? "bg-yellow-100 text-yellow-700" :
                        "bg-gray-100 text-gray-600"
                      }`}
                      title={[
                        t(`risk.nis2_art21.${r.nis2_art21_category}`),
                        r.nis2_relevance ? t(`risk.nis2_relevance.${r.nis2_relevance}`) : "",
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

function ThreatBreakdownChart({ data }: { data: ThreatBreakdown[] }) {
  const { t } = useTranslation();
  if (data.length === 0) return null;
  const chartData = data.slice(0, 8).map(d => {
    const label = t(`risk.threat_cat.${d.category}`, { defaultValue: d.label });
    return {
      name: label.length > 22 ? label.slice(0, 20) + "…" : label,
      fullLabel: label,
      residuo: d.residual_avg,
      inerente: d.inherent_avg,
    };
  });
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">{t("reporting.risk_bia_bcp.threat_chart_title")}</h3>
      <ResponsiveContainer width="100%" height={Math.max(200, chartData.length * 42)}>
        <BarChart layout="vertical" data={chartData} margin={{ top: 4, right: 24, left: 8, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 11 }} domain={[0, 25]} />
          <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={150} />
          <Tooltip labelFormatter={(label) => chartData.find(d => d.name === label)?.fullLabel ?? label} />
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
          <Bar dataKey="significativo" name={t("reporting.risk_bia_bcp.nis2_sig")} stackId="a" fill="#ef4444" />
          <Bar dataKey="potenzialmente" name={t("reporting.risk_bia_bcp.nis2_pot")} stackId="a" fill="#f59e0b" />
          <Bar dataKey="non_significativo" name={t("reporting.risk_bia_bcp.nis2_non")} stackId="a" fill="#86efac" radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function RisksView({ data }: { data: RiskBiaBcpData }) {
  const { t } = useTranslation();
  const { kpis, appetite } = data;
  const maxRed = appetite.max_red_risks_count;
  const overTolerance = maxRed !== null && kpis.risks_over_appetite > maxRed;
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        <KpiTile
          label={t("reporting.risk_bia_bcp.kpi_over_appetite")}
          value={kpis.risks_over_appetite}
          variant={overTolerance ? "danger" : kpis.risks_over_appetite > 0 ? "warning" : "ok"}
          sub={maxRed !== null
            ? t("reporting.risk_bia_bcp.kpi_over_appetite_sub", { threshold: appetite.max_acceptable_score, max: maxRed })
            : t("reporting.risk_bia_bcp.kpi_over_appetite_sub_nomax", { threshold: appetite.max_acceptable_score })}
        />
        <KpiTile label={t("reporting.risk_bia_bcp.kpi_total")} value={kpis.risks_total} />
        <KpiTile label={t("reporting.risk_bia_bcp.kpi_yellow")} value={kpis.risks_yellow} variant={kpis.risks_yellow > 0 ? "warning" : "ok"} />
        <KpiTile label={t("reporting.risk_bia_bcp.kpi_revaluation")} value={kpis.risks_needs_revaluation} variant={kpis.risks_needs_revaluation > 0 ? "warning" : "ok"} sub={t("reporting.risk_bia_bcp.kpi_revaluation_sub")} />
        <KpiTile label={t("reporting.risk_bia_bcp.kpi_accepted")} value={kpis.risks_formally_accepted} variant="ok" sub={`/ ${kpis.risks_total}`} />
      </div>
      <p className="text-xs text-gray-400 -mt-3">
        {!appetite.defined
          ? t("reporting.risk_bia_bcp.appetite_missing", { threshold: appetite.max_acceptable_score })
          : appetite.per_plant
            ? t("reporting.risk_bia_bcp.appetite_per_plant")
            : t("reporting.risk_bia_bcp.appetite_defined")}
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RiskHeatmap cells={data.heatmap} threshold={appetite.max_acceptable_score} />
        <Nis2Chart data={data.nis2_breakdown} />
      </div>
      <TopRisksTable risks={data.top_risks} />
      <ThreatBreakdownChart data={data.by_threat} />
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
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <KpiTile label={t("reporting.risk_bia_bcp.kpi_processes")} value={data.bia_bcp_table.length} />
        <KpiTile label={t("reporting.risk_bia_bcp.kpi_bia_no_bcp")} value={kpis.bia_critical_no_bcp} variant={kpis.bia_critical_no_bcp > 0 ? "danger" : "ok"} sub={t("reporting.risk_bia_bcp.kpi_bia_no_bcp_sub")} />
        <KpiTile label={t("reporting.risk_bia_bcp.kpi_bcp_overdue")} value={kpis.bcp_test_overdue} variant={kpis.bcp_test_overdue > 0 ? "warning" : "ok"} sub={t("reporting.risk_bia_bcp.kpi_bcp_overdue_sub")} />
      </div>
      <BiaBcpTable rows={data.bia_bcp_table} />
    </div>
  );
}

// ── Valore economico ──────────────────────────────────────────────────────────

function TreatmentRosiTable({ treatments, totals }: { treatments: TreatmentRosi[]; totals: TreatmentRosiTotals }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  if (treatments.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-5">
        <h3 className="text-sm font-semibold text-gray-700 mb-1">{t("reporting.risk_bia_bcp.rosi_title")}</h3>
        <p className="text-sm text-gray-400">{t("reporting.risk_bia_bcp.rosi_empty")}</p>
      </div>
    );
  }
  return (
    <Panel title={t("reporting.risk_bia_bcp.rosi_title")} subtitle={t("reporting.risk_bia_bcp.rosi_subtitle", { years: totals.amort_years })}>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-2 font-medium text-gray-600">{t("reporting.risk_bia_bcp.rosi_col_treatment")}</th>
              <th className="text-left px-3 py-2 font-medium text-gray-600">{t("reporting.risk_bia_bcp.rosi_col_process")}</th>
              <th className="text-right px-3 py-2 font-medium text-gray-600">{t("reporting.risk_bia_bcp.rosi_col_reduction")}</th>
              <th className="text-right px-3 py-2 font-medium text-gray-600">{t("reporting.risk_bia_bcp.rosi_col_avoided")}</th>
              <th className="text-right px-3 py-2 font-medium text-gray-600">{t("reporting.risk_bia_bcp.rosi_col_cost")}</th>
              <th className="text-right px-3 py-2 font-medium text-gray-600">{t("reporting.risk_bia_bcp.rosi_col_net")}</th>
              <th className="text-right px-3 py-2 font-medium text-gray-600">{t("reporting.risk_bia_bcp.rosi_col_rosi")}</th>
              <th className="text-right px-3 py-2 font-medium text-gray-600">{t("reporting.risk_bia_bcp.rosi_col_payback")}</th>
              <th className="text-center px-3 py-2 font-medium text-gray-600">{t("reporting.risk_bia_bcp.rosi_col_verdict")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {treatments.map(tr => (
              <tr key={tr.id} className="hover:bg-gray-50">
                <td className="px-4 py-2 font-medium text-gray-800 max-w-xs truncate" title={tr.title}>{tr.title}</td>
                <td className="px-3 py-2 text-gray-500 text-xs">{tr.process_name}</td>
                <td className="px-3 py-2 text-right tabular-nums text-gray-600">{tr.ale_reduction_pct}%</td>
                <td className="px-3 py-2 text-right tabular-nums whitespace-nowrap text-gray-700">{tr.ale_avoided > 0 ? formatEur(tr.ale_avoided, lang) : "—"}</td>
                <td className="px-3 py-2 text-right tabular-nums whitespace-nowrap text-gray-500">{formatEur(tr.annual_cost, lang)}</td>
                <td className={`px-3 py-2 text-right tabular-nums whitespace-nowrap font-medium ${tr.net_annual >= 0 ? "text-green-700" : "text-red-600"}`}>{formatEur(tr.net_annual, lang)}</td>
                <td className={`px-3 py-2 text-right tabular-nums font-bold ${tr.rosi_pct === null ? "text-gray-400" : tr.rosi_pct > 0 ? "text-green-700" : "text-red-600"}`}>{tr.rosi_pct === null ? "—" : `${tr.rosi_pct}%`}</td>
                <td className="px-3 py-2 text-right tabular-nums whitespace-nowrap text-gray-500">{tr.payback_months === null ? "—" : t("reporting.risk_bia_bcp.rosi_months", { n: tr.payback_months })}</td>
                <td className="px-3 py-2 text-center">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${tr.worth_it ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600"}`}>
                    {tr.worth_it ? t("reporting.risk_bia_bcp.rosi_worth") : t("reporting.risk_bia_bcp.rosi_not_worth")}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot className="bg-gray-50 border-t border-gray-200 font-medium text-gray-700">
            <tr>
              <td className="px-4 py-2" colSpan={3}>{t("reporting.risk_bia_bcp.rosi_total", { count: totals.count })}</td>
              <td className="px-3 py-2 text-right tabular-nums whitespace-nowrap">{formatEur(totals.ale_avoided, lang)}</td>
              <td className="px-3 py-2 text-right tabular-nums whitespace-nowrap">{formatEur(totals.annual_cost, lang)}</td>
              <td className={`px-3 py-2 text-right tabular-nums whitespace-nowrap ${totals.net_annual >= 0 ? "text-green-700" : "text-red-600"}`}>{formatEur(totals.net_annual, lang)}</td>
              <td className={`px-3 py-2 text-right tabular-nums font-bold ${totals.rosi_pct === null ? "text-gray-400" : totals.rosi_pct > 0 ? "text-green-700" : "text-red-600"}`}>{totals.rosi_pct === null ? "—" : `${totals.rosi_pct}%`}</td>
              <td colSpan={2} />
            </tr>
          </tfoot>
        </table>
      </div>
    </Panel>
  );
}

function EconomicView({ data }: { data: RiskBiaBcpData }) {
  const { t, i18n } = useTranslation();
  const { kpis } = data;
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <KpiTile label={t("reporting.risk_bia_bcp.kpi_ale_inherent")} value={formatEur(kpis.ale_total_inherent, i18n.language, true)} />
        <KpiTile
          label={t("reporting.risk_bia_bcp.kpi_ale_residual")}
          value={formatEur(kpis.ale_total, i18n.language, true)}
          variant={kpis.ale_total > 0 ? "warning" : "neutral"}
          sub={t("reporting.risk_bia_bcp.kpi_ale_coverage", { valued: kpis.ale_valued_count, total: kpis.risks_total, pct: kpis.ale_coverage_pct })}
        />
        <KpiTile
          label={t("reporting.risk_bia_bcp.kpi_ale_saved")}
          value={formatEur(kpis.ale_saved, i18n.language, true)}
          variant={kpis.ale_saved > 0 ? "ok" : "neutral"}
          sub={t("reporting.risk_bia_bcp.kpi_ale_saved_sub", { pct: kpis.ale_saved_pct })}
        />
      </div>
      <p className="text-xs text-gray-400 -mt-3">{t("reporting.risk_bia_bcp.ale_hint")}</p>
      <TreatmentRosiTable treatments={data.treatments} totals={data.treatments_totals} />
    </div>
  );
}

const VIEWS = ["risks", "continuity", "economic"] as const;
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
      {view === "economic" && <EconomicView data={data} />}
    </div>
  );
}
