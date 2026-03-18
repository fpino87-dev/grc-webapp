import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { controlsApi } from "../../api/endpoints/controls";
import { incidentsApi } from "../../api/endpoints/incidents";
import { plantsApi } from "../../api/endpoints/plants";
import { reportingApi } from "../../api/endpoints/reporting";
import { assetsApi } from "../../api/endpoints/assets";
import { scheduleApi } from "../../api/endpoints/schedule";
import { governanceApi } from "../../api/endpoints/governance";
import { useAuthStore } from "../../store/auth";
import { StatusBadge } from "../../components/ui/StatusBadge";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import { useTranslation } from "react-i18next";

function KpiCard({
  label,
  value,
  sub,
  color = "blue",
}: {
  label: string;
  value: string | number;
  sub?: string;
  color?: string;
}) {
  const colors: Record<string, string> = {
    blue: "bg-blue-50 border-blue-200 text-blue-700",
    green: "bg-green-50 border-green-200 text-green-700",
    red: "bg-red-50 border-red-200 text-red-700",
    yellow: "bg-yellow-50 border-yellow-200 text-yellow-700",
  };
  return (
    <div className={`border rounded-lg p-4 ${colors[color]}`}>
      <p className="text-xs font-medium uppercase tracking-wide opacity-70">{label}</p>
      <p className="text-3xl font-bold mt-1">{value}</p>
      {sub && <p className="text-xs mt-1 opacity-60">{sub}</p>}
    </div>
  );
}

const WEEK_OPTIONS = [
  { label: "3 mesi", weeks: 12 },
  { label: "6 mesi", weeks: 24 },
  { label: "12 mesi", weeks: 52 },
];

const FRAMEWORK_LABELS: Record<string, string> = {
  ISO27001: "ISO 27001",
  NIS2:     "NIS2",
  TISAX_L2: "TISAX L2",
  TISAX_L3: "TISAX L3",
};

function KpiTrendChart() {
  const { t } = useTranslation();
  const [weeks, setWeeks] = useState(12);
  const [framework, setFramework] = useState("ISO27001");
  const selectedPlant = useAuthStore(s => s.selectedPlant);

  // Carica framework attivi per il plant selezionato
  const { data: activeFrameworks } = useQuery({
    queryKey: ["frameworks", selectedPlant?.id],
    queryFn: () => controlsApi.frameworks(selectedPlant?.id),
    retry: false,
  });

  // Quando cambiano i framework attivi, seleziona automaticamente il primo disponibile
  useEffect(() => {
    if (activeFrameworks && activeFrameworks.length > 0) {
      const codes = activeFrameworks.map(f => f.code);
      if (!codes.includes(framework)) {
        setFramework(codes[0]);
      }
    }
  }, [activeFrameworks]);

  const { data, isLoading } = useQuery({
    queryKey: ["kpi-trend", framework, weeks, selectedPlant?.id],
    queryFn: () => reportingApi.kpiTrend({ framework, weeks }),
    retry: false,
  });

  const snapshots = data?.results ?? [];

  const chartData = snapshots.map(s => ({
    week: s.week_start,
    compliant: s.pct_compliant,
    maturity: s.overall_maturity != null ? parseFloat(s.overall_maturity.toFixed(2)) : null,
    highRisks: s.high_risks,
    incidents: s.open_incidents,
  }));

  const fwLabel = FRAMEWORK_LABELS[framework] ?? framework;

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-700">{t("dashboard.trend.title", { framework: fwLabel })}</h3>
        <div className="flex gap-1 flex-wrap">
          {/* Selector framework attivi */}
          {activeFrameworks && activeFrameworks.length > 1 && (
            <div className="flex gap-1 mr-2">
              {activeFrameworks.map(f => (
                <button
                  key={f.code}
                  onClick={() => setFramework(f.code)}
                  className={`px-2 py-1 text-xs rounded border ${
                    framework === f.code
                      ? "bg-gray-700 text-white border-gray-700"
                      : "text-gray-500 border-gray-300 hover:bg-gray-50"
                  }`}
                >
                  {FRAMEWORK_LABELS[f.code] ?? f.code}
                </button>
              ))}
            </div>
          )}
          {WEEK_OPTIONS.map(opt => (
            <button
              key={opt.weeks}
              onClick={() => setWeeks(opt.weeks)}
              className={`px-2 py-1 text-xs rounded border ${
                weeks === opt.weeks
                  ? "bg-primary-600 text-white border-primary-600"
                  : "text-gray-600 border-gray-300 hover:bg-gray-50"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="h-48 flex items-center justify-center text-gray-400 text-sm">{t("common.loading")}</div>
      ) : snapshots.length === 0 ? (
        <div className="h-48 flex items-center justify-center text-gray-400 text-sm italic">
          {t("dashboard.trend.empty")}
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis
              dataKey="week"
              tick={{ fontSize: 10 }}
              tickFormatter={v => v.slice(5)} // show MM-DD only
            />
            <YAxis yAxisId="pct" domain={[0, 100]} tick={{ fontSize: 10 }} unit="%" width={36} />
            <YAxis yAxisId="count" orientation="right" tick={{ fontSize: 10 }} width={28} />
            <Tooltip
              formatter={(value, name) => {
                if (name === "% Compliant") return [`${value}%`, name];
                return [value, name];
              }}
            />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Line
              yAxisId="pct"
              type="monotone"
              dataKey="compliant"
              name="% Compliant"
              stroke="#16a34a"
              strokeWidth={2}
              dot={false}
            />
            <Line
              yAxisId="count"
              type="monotone"
              dataKey="highRisks"
              name="Rischi alti"
              stroke="#dc2626"
              strokeWidth={2}
              dot={false}
            />
            <Line
              yAxisId="count"
              type="monotone"
              dataKey="incidents"
              name="Incidenti aperti"
              stroke="#f59e0b"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

const URGENCY_DOT: Record<string, string> = {
  green: "bg-green-500", yellow: "bg-yellow-500", red: "bg-red-500",
};

function UpcomingDeadlinesWidget() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data } = useQuery({
    queryKey: ["activity-schedule-widget"],
    queryFn: () => scheduleApi.getActivitySchedule({ months: 3 }),
    retry: false,
  });

  const items = (data?.results ?? []).slice(0, 6);
  if (items.length === 0) return null;

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-700">{t("dashboard.deadlines.title")}</h3>
        <button
          onClick={() => navigate("/schedule/activity")}
          className="text-xs text-blue-600 hover:underline"
        >
          {t("dashboard.see_all")} →
        </button>
      </div>
      <div className="space-y-2">
        {items.map((item, idx) => (
          <div key={idx} className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2 flex-1 min-w-0">
              <span className={`inline-block w-2 h-2 rounded-full flex-shrink-0 ${URGENCY_DOT[item.urgency]}`} />
              <span className="text-gray-700 truncate">{item.label}</span>
            </div>
            <span className="text-xs text-gray-500 flex-shrink-0 ml-2">{item.due_date}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function CriticalRolesWidget() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const { data: vacantData } = useQuery({
    queryKey: ["governance-vacanti"],
    queryFn: () => governanceApi.vacanti(),
    retry: false,
  });
  const { data: expiringData } = useQuery({
    queryKey: ["governance-in-scadenza"],
    queryFn: () => governanceApi.inScadenza(30),
    retry: false,
  });

  const hasVacant   = (vacantData?.count ?? 0) > 0;
  const hasExpiring = (expiringData?.expiring?.length ?? 0) > 0;
  if (!hasVacant && !hasExpiring) return null;

  return (
    <div className="space-y-3 mb-6">
      {hasVacant && (
        <div className="border border-red-300 bg-red-50 rounded-lg p-4">
          <p className="font-semibold text-red-700 text-sm">
            🚨 {t("dashboard.governance.vacant_roles", { count: vacantData!.count })}
          </p>
          <button
            onClick={() => navigate("/governance")}
            className="text-xs text-red-600 underline mt-1"
          >
            {t("dashboard.governance.go_to")} →
          </button>
        </div>
      )}
      {hasExpiring && (
        <div className="border border-amber-300 bg-amber-50 rounded-lg p-4">
          <p className="font-semibold text-amber-700 text-sm">
            ⚠ {t("dashboard.governance.expiring_roles", { count: expiringData!.expiring.length })}
          </p>
          <button
            onClick={() => navigate("/governance")}
            className="text-xs text-amber-600 underline mt-1"
          >
            {t("dashboard.governance.go_to")} →
          </button>
        </div>
      )}
    </div>
  );
}

function RevaluationAlert() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data: assetsToReview } = useQuery({
    queryKey: ["assets-needs-revaluation"],
    queryFn: () => assetsApi.needsRevaluationIT(),
    retry: false,
  });
  const count = assetsToReview?.length ?? 0;
  if (!count) return null;
  return (
    <div className="border border-amber-300 bg-amber-50 rounded-lg p-4 mb-6">
      <p className="font-semibold text-amber-800">
        {t("dashboard.assets.needs_revaluation", { count })}
      </p>
      <p className="text-sm text-amber-700">{t("dashboard.assets.needs_revaluation_sub")}</p>
      <button
        onClick={() => navigate("/assets")}
        className="text-sm text-blue-600 hover:underline mt-1"
      >
        {t("dashboard.assets.see_list")} →
      </button>
    </div>
  );
}

export function Dashboard() {
  const { t } = useTranslation();
  const { data: controlsData } = useQuery({
    queryKey: ["controls-summary"],
    queryFn: () => controlsApi.instances(),
    retry: false,
  });
  const { data: incidentsData } = useQuery({
    queryKey: ["incidents-summary"],
    queryFn: () => incidentsApi.list({ status: "aperto" }),
    retry: false,
  });
  const { data: plants } = useQuery({
    queryKey: ["plants"],
    queryFn: () => plantsApi.list(),
    retry: false,
  });

  const controls = controlsData?.results ?? [];
  const compliant = controls.filter((c) => c.status === "compliant").length;
  const gap = controls.filter((c) => c.status === "gap").length;
  const openIncidents = incidentsData?.count ?? 0;

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-900 mb-6">{t("dashboard.title")}</h2>

      <CriticalRolesWidget />
      <RevaluationAlert />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <KpiCard label={t("dashboard.kpi.active_sites")} value={plants?.length ?? "—"} color="blue" />
        <KpiCard
          label={t("dashboard.kpi.compliant_controls")}
          value={controls.length ? `${Math.round((compliant / controls.length) * 100)}%` : "—"}
          sub={`${compliant} / ${controls.length}`}
          color="green"
        />
        <KpiCard
          label={t("dashboard.kpi.gap_controls")}
          value={gap}
          sub={t("dashboard.kpi.gap_controls_sub")}
          color={gap > 0 ? "red" : "green"}
        />
        <KpiCard
          label={t("dashboard.kpi.open_incidents")}
          value={openIncidents}
          color={openIncidents > 0 ? "yellow" : "green"}
        />
      </div>

      <div className="mb-6">
        <KpiTrendChart />
      </div>

      <div className="mb-6">
        <UpcomingDeadlinesWidget />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">{t("dashboard.latest_gaps.title")}</h3>
          {gap === 0 ? (
            <p className="text-sm text-gray-400 italic">{t("dashboard.latest_gaps.empty")}</p>
          ) : (
            <div className="space-y-2">
              {controls
                .filter((c) => c.status === "gap")
                .slice(0, 5)
                .map((c) => (
                  <div key={c.id} className="flex items-center justify-between text-sm">
                    <span className="text-gray-700 truncate flex-1">
                      {c.control_external_id} — {c.control_title || c.control}
                    </span>
                    <StatusBadge status={c.status} />
                  </div>
                ))}
            </div>
          )}
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">{t("dashboard.sites.title")}</h3>
          {!plants?.length ? (
            <p className="text-sm text-gray-400 italic">{t("dashboard.sites.empty")}</p>
          ) : (
            <div className="space-y-2">
              {plants.slice(0, 6).map((p) => (
                <div key={p.id} className="flex items-center justify-between text-sm">
                  <span className="font-medium text-gray-700">
                    [{p.code}] {p.name}
                  </span>
                  <div className="flex gap-1">
                    <StatusBadge status={p.status} />
                    {p.nis2_scope !== "non_soggetto" && <StatusBadge status={p.nis2_scope} />}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
