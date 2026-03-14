import { useQuery } from "@tanstack/react-query";
import { reportingApi } from "../../api/endpoints/reporting";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface KpiCardProps {
  label: string;
  value: string | number;
  sub?: string;
  highlight?: boolean;
}

function KpiCard({ label, value, sub, highlight }: KpiCardProps) {
  return (
    <div
      className={`bg-white rounded-lg border p-5 flex flex-col gap-1 ${
        highlight ? "border-primary-400" : "border-gray-200"
      }`}
    >
      <span className="text-xs text-gray-500 font-medium uppercase tracking-wide">{label}</span>
      <span
        className={`text-3xl font-bold ${highlight ? "text-primary-600" : "text-gray-900"}`}
      >
        {value}
      </span>
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

const STATUS_LABELS: Record<string, string> = {
  compliant: "Compliant",
  parziale: "Parziale",
  gap: "Gap",
  na: "N/A",
  non_valutato: "Non valutato",
};

const BAR_COLORS: Record<string, string> = {
  compliant: "#22c55e",
  parziale: "#facc15",
  gap: "#ef4444",
  na: "#d1d5db",
  non_valutato: "#e5e7eb",
};

export function ReportingPage() {
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
    <div>
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-gray-900">Reporting & Dashboard</h2>
      </div>

      {/* KPI cards */}
      {dashLoading ? (
        <div className="p-8 text-center text-gray-400">Caricamento KPI...</div>
      ) : dash ? (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
          <KpiCard label="Siti attivi" value={dash.plants_active} />
          <KpiCard label="Incidenti aperti" value={dash.incidents_open} highlight={dash.incidents_open > 0} />
          <KpiCard label="Controlli totali" value={dash.controls_total} />
          <KpiCard
            label="% Compliant"
            value={`${dash.pct_compliant.toFixed(1)}%`}
            sub={`${dash.controls_compliant} / ${dash.controls_total}`}
            highlight
          />
          <KpiCard label="Controlli in gap" value={dash.controls_gap} highlight={dash.controls_gap > 0} />
        </div>
      ) : null}

      {/* Compliance breakdown */}
      {compLoading ? (
        <div className="p-8 text-center text-gray-400">Caricamento compliance...</div>
      ) : comp && total > 0 ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Visual bar */}
          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <h3 className="text-sm font-semibold text-gray-700 mb-4">
              Distribuzione compliance ({total} controlli)
            </h3>
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
                  <span
                    className={`w-3 h-3 rounded-sm inline-block ${
                      STATUS_COLORS[status] ?? "bg-gray-300"
                    }`}
                  />
                  {STATUS_LABELS[status] ?? status}: {count}
                </div>
              ))}
            </div>
          </div>

          {/* Recharts bar chart */}
          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <h3 className="text-sm font-semibold text-gray-700 mb-4">
              Controlli per stato
            </h3>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={barData} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="status" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="count" name="Controlli">
                  {barData.map((entry, index) => (
                    <rect key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      ) : (
        !compLoading && (
          <div className="bg-white rounded-lg border border-gray-200 p-8 text-center text-gray-400">
            Nessun dato di compliance disponibile
          </div>
        )
      )}
    </div>
  );
}
