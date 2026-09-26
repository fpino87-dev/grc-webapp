import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { reportingApi, type AccessMatrixRow } from "../../api/endpoints/reporting";
import { useAuthStore } from "../../store/auth";
import { useSearchParams } from "react-router-dom";
import { TabObjectives } from "./TabObjectives";
import { TabCompliance } from "./TabCompliance";
import { TabRiskBiaBcp } from "./TabRiskBiaBcp";
import { TabProcessKpi } from "./TabProcessKpi";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

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
      name: r.owner_name || "—",
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
              margin={{ top: 4, right: 16, left: 8, bottom: 4 }}
            >
              <CartesianGrid strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 11 }} allowDecimals={false} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={170} />
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

const ACCESS_REVIEW_ROLES = ["super_admin", "compliance_officer", "internal_auditor", "external_auditor"];

function AccessRow({ r, t }: { r: AccessMatrixRow; t: (k: string) => string }) {
  return (
    <tr className={`border-t border-gray-100 ${!r.is_active ? "bg-gray-50/60" : ""}`}>
      <td className="px-3 py-2">
        <div className="font-medium text-gray-800">{r.user_name}</div>
        <div className="text-xs text-gray-400">{r.user_email}</div>
      </td>
      <td className="px-3 py-2 text-gray-700">{r.role_label}</td>
      <td className="px-3 py-2 text-gray-600 text-xs">
        {r.covers_all ? t("reporting.access_matrix.all_sites") : (r.plant_codes.join(", ") || r.scope_label)}
        {r.valid_until && <span className="text-gray-400"> · {t("reporting.access_matrix.until")} {r.valid_until}</span>}
      </td>
      <td className="px-3 py-2">
        {r.flags.map(f => (
          <span key={f} className="inline-block text-xs px-1.5 py-0.5 rounded bg-red-100 text-red-700 mr-1 mb-0.5">
            {t(`reporting.access_matrix.flag.${f}`)}
          </span>
        ))}
      </td>
    </tr>
  );
}

function TabAccessMatrix() {
  const { t } = useTranslation();
  const selectedPlant = useAuthStore(s => s.selectedPlant);
  const [onlyIssues, setOnlyIssues] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["reporting-access-matrix", selectedPlant?.id],
    queryFn: () => reportingApi.accessMatrix(selectedPlant?.id),
  });

  if (isLoading) return <div className="text-gray-400 py-8 text-center">{t("common.loading")}</div>;
  if (!data) return null;

  const byKind = (k: "access" | "responsibility") =>
    data.rows.filter(r => r.kind === k && (!onlyIssues || r.flags.length > 0));

  const tiles: [string, number, string][] = [
    ["users", data.summary.users, "text-gray-900"],
    ["access", data.summary.access, "text-blue-700"],
    ["responsibilities", data.summary.responsibilities, "text-indigo-700"],
    ["committees", data.summary.committees, "text-emerald-700"],
    // Le segnalazioni sugli organi (account disattivato, carica in scadenza,
    // presidente mancante) sono incoerenze della stessa review.
    ["issues", data.summary.issues + data.summary.committee_issues,
     data.summary.issues + data.summary.committee_issues > 0 ? "text-red-600" : "text-green-600"],
  ];

  const renderTable = (k: "access" | "responsibility", titleKey: string, accent: string) => {
    const rows = byKind(k);
    return (
      <div>
        <p className={`text-sm font-semibold ${accent} mb-1.5`}>{t(titleKey)} <span className="text-gray-400 font-normal">({rows.length})</span></p>
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                <th className="px-3 py-2 text-left">{t("reporting.access_matrix.col.user")}</th>
                <th className="px-3 py-2 text-left">{t("reporting.access_matrix.col.role")}</th>
                <th className="px-3 py-2 text-left">{t("reporting.access_matrix.col.scope")}</th>
                <th className="px-3 py-2 text-left">{t("reporting.access_matrix.col.flags")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => <AccessRow key={i} r={r} t={t} />)}
              {rows.length === 0 && (
                <tr><td colSpan={4} className="px-3 py-6 text-center text-gray-400">{t("reporting.access_matrix.empty")}</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <p className="text-sm text-gray-500">{t("reporting.access_matrix.subtitle")}</p>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-1.5 text-xs text-gray-600">
            <input type="checkbox" checked={onlyIssues} onChange={e => setOnlyIssues(e.target.checked)} />
            {t("reporting.access_matrix.only_issues")}
          </label>
          <button
            onClick={() => reportingApi.exportAccessMatrixCsv(selectedPlant?.id)}
            className="text-xs font-medium text-gray-600 border border-gray-300 rounded px-3 py-1.5 hover:bg-gray-50"
          >
            ⬇ {t("reporting.access_matrix.export_csv")}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {tiles.map(([key, val, cls]) => (
          <div key={key} className="border border-gray-200 rounded-lg p-3 bg-white">
            <p className="text-xs text-gray-500 uppercase tracking-wide">{t(`reporting.access_matrix.summary.${key}`)}</p>
            <p className={`text-2xl font-semibold ${cls}`}>{val}</p>
          </div>
        ))}
      </div>

      {data.vacant_mandatory_roles.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg px-3 py-2 text-xs text-red-800">
          ⛔ {t("reporting.access_matrix.vacant_roles")}: {data.vacant_mandatory_roles.join(", ")}
        </div>
      )}

      {/* Due tabelle separate: gli utenti non si ripetono mischiati */}
      {renderTable("access", "reporting.access_matrix.section_access", "text-blue-700")}
      {renderTable("responsibility", "reporting.access_matrix.section_resp", "text-indigo-700")}

      {/* Organi di governo: chi tiene e approva il riesame (CdA, comitato, direzione) */}
      <div>
        <p className="text-sm font-semibold text-emerald-700 mb-1.5">{t("reporting.access_matrix.committees_title")} <span className="text-gray-400 font-normal">({data.committees.length})</span></p>
        {data.committees.length === 0 ? (
          <div className="bg-gray-50 border border-gray-200 rounded-lg px-3 py-3 text-xs text-gray-500">
            ℹ️ {t("reporting.access_matrix.committees_empty")}
          </div>
        ) : (
          <div className="space-y-2">
            {data.committees
              .filter(c => !onlyIssues || c.flags.length > 0 || c.members.some(m => m.flags.length > 0))
              .map(c => (
              <div key={c.id} className="bg-white border border-gray-200 rounded-lg px-3 py-2">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <span className="font-medium text-gray-800">
                    {c.name}
                    {c.is_management_body && (
                      <span className="ml-2 text-xs font-normal bg-indigo-50 text-indigo-700 border border-indigo-200 px-1.5 py-0.5 rounded">
                        {t("governance.bodies.nis2_badge")}
                      </span>
                    )}
                  </span>
                  <span className="text-xs text-gray-500">
                    {c.committee_type_label} · {c.covers_all ? t("reporting.access_matrix.all_sites") : c.plant_codes.join(", ")}
                  </span>
                </div>
                {c.flags.map(f => (
                  <p key={f} className="text-xs text-amber-700 mt-1">⚠ {t(`reporting.access_matrix.body_flag.${f}`)}</p>
                ))}
                {c.members.length > 0 && (
                  <table className="w-full text-xs mt-1.5">
                    <tbody>
                      {c.members.filter(m => !onlyIssues || m.flags.length > 0).map(m => (
                        <tr key={m.id} className="border-t border-gray-100">
                          <td className="py-1 pr-3">
                            <span className="text-gray-800">{m.name}</span>
                            {m.position && <span className="text-gray-500"> — {m.position}</span>}
                          </td>
                          <td className="py-1 pr-3 text-gray-600 whitespace-nowrap">{m.body_role_label}</td>
                          <td className="py-1 pr-3 text-gray-500 whitespace-nowrap">
                            {m.has_account ? t("reporting.access_matrix.member_account") : t("reporting.access_matrix.member_no_account")}
                          </td>
                          <td className="py-1 whitespace-nowrap">
                            {m.flags.map(f => (
                              <span key={f} className="inline-block mr-1 px-1.5 py-0.5 rounded bg-red-50 text-red-700 border border-red-200">
                                {t(`reporting.access_matrix.flag.${f}`)}
                              </span>
                            ))}
                            {m.valid_until && (
                              <span className="text-gray-400"> {t("reporting.access_matrix.until")} {m.valid_until}</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export function ReportingPage() {
  const { t } = useTranslation();
  const role = useAuthStore(s => s.user?.role) ?? "";
  const showAccessMatrix = ACCESS_REVIEW_ROLES.includes(role);
  const tabKeys = ["compliance", "owner", "risk_bia_bcp", "kpi", "objectives", ...(showAccessMatrix ? ["access_matrix"] : [])] as const;
  type TabKey = typeof tabKeys[number];
  // ?tab=access_matrix: link diretto (es. da Gestione utenti)
  // Il tab aperto resta nell'indirizzo (?tab=), così un link porta allo stesso tab.
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedTab = searchParams.get("tab");
  const tab: TabKey = (tabKeys as readonly string[]).includes(requestedTab ?? "")
    ? (requestedTab as TabKey)
    : "compliance";
  const setTab = (next: TabKey) => {
    const params = new URLSearchParams(searchParams);
    params.set("tab", next);
    setSearchParams(params, { replace: true });
  };

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-gray-900">{t("reporting.title")}</h2>
      </div>

      <div className="flex gap-1 mb-6 border-b border-gray-200">
        {tabKeys.map(tabKey => (
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
      {tab === "kpi" && <TabProcessKpi />}
      {tab === "objectives" && <TabObjectives />}
      {tab === "access_matrix" && <TabAccessMatrix />}
    </div>
  );
}
