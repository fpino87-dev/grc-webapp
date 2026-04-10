import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { scheduleApi, ActivityItem } from "../../api/endpoints/schedule";
import { plantsApi } from "../../api/endpoints/plants";
import { ModuleHelp } from "../../components/ui/ModuleHelp";
import { useTranslation } from "react-i18next";

const URGENCY_COLOR: Record<string, string> = {
  green:  "bg-green-100 text-green-800 border-green-200",
  yellow: "bg-yellow-100 text-yellow-800 border-yellow-200",
  red:    "bg-red-100 text-red-800 border-red-200",
};

const URGENCY_DOT: Record<string, string> = {
  green:  "bg-green-500",
  yellow: "bg-yellow-500",
  red:    "bg-red-500",
};

function ActivityRow({ item }: { item: ActivityItem }) {
  const { t } = useTranslation();
  return (
    <tr className="hover:bg-gray-50">
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <span className={`inline-block w-2 h-2 rounded-full ${URGENCY_DOT[item.urgency]}`} />
          <span className="text-sm font-medium text-gray-900">{item.label}</span>
        </div>
      </td>
      <td className="px-4 py-3 text-sm text-gray-600">{item.category_label}</td>
      <td className="px-4 py-3 text-sm text-gray-700">{item.due_date}</td>
      <td className="px-4 py-3">
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${URGENCY_COLOR[item.urgency]}`}>
          {item.days_left === 0
            ? t("schedule.activity.days.today")
            : item.days_left < 0
            ? t("schedule.activity.days.overdue")
            : t("schedule.activity.days.in_days", { days: item.days_left })}
        </span>
      </td>
      <td className="px-4 py-3 text-sm text-gray-500">{item.status}</td>
    </tr>
  );
}

export function ActivitySchedulePage() {
  const { t } = useTranslation();
  const [plantId, setPlantId] = useState<string>("");
  const [months, setMonths] = useState(6);
  const [urgencyFilter, setUrgencyFilter] = useState<string>("all");

  const { data: plants } = useQuery({
    queryKey: ["plants"],
    queryFn: () => plantsApi.list(),
    retry: false,
  });

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["activity-schedule", plantId, months],
    queryFn: () => scheduleApi.getActivitySchedule({
      plant: plantId || undefined,
      months,
    }),
    retry: false,
  });

  const activities = data?.results ?? [];
  const filtered = urgencyFilter === "all" ? activities : activities.filter(a => a.urgency === urgencyFilter);

  const red = activities.filter(a => a.urgency === "red").length;
  const yellow = activities.filter(a => a.urgency === "yellow").length;
  const green = activities.filter(a => a.urgency === "green").length;

  const monthOptions = [
    { label: t("schedule.filters.months.3"), value: 3 },
    { label: t("schedule.filters.months.6"), value: 6 },
    { label: t("schedule.filters.months.12"), value: 12 },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-gray-900 flex items-center">
          {t("schedule.activity.title")}
          <ModuleHelp
            title={t("schedule.activity.help.title")}
            description={t("schedule.activity.help.description")}
            steps={[
              t("schedule.activity.help.steps.1"),
              t("schedule.activity.help.steps.2"),
              t("schedule.activity.help.steps.3"),
              t("schedule.activity.help.steps.4"),
            ]}
            connections={[
              { module: t("schedule.activity.help.connections.policy.module"), relation: t("schedule.activity.help.connections.policy.relation") },
              { module: t("schedule.activity.help.connections.required_docs.module"), relation: t("schedule.activity.help.connections.required_docs.relation") },
            ]}
            configNeeded={[
              t("schedule.activity.help.config_needed.1"),
              t("schedule.activity.help.config_needed.2"),
            ]}
          />
        </h2>
        <button
          onClick={() => refetch()}
          className="text-sm text-blue-600 hover:underline"
        >
          {t("actions.refresh")}
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white border border-gray-200 rounded-lg p-4 mb-6">
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">{t("schedule.filters.plant")}</label>
            <select
              value={plantId}
              onChange={e => setPlantId(e.target.value)}
              className="border border-gray-300 rounded px-2 py-1.5 text-sm"
            >
              <option value="">{t("schedule.filters.all_plants")}</option>
              {plants?.map(p => (
                <option key={p.id} value={p.id}>[{p.code}] {p.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">{t("schedule.filters.horizon")}</label>
            <div className="flex gap-1">
              {monthOptions.map(opt => (
                <button
                  key={opt.value}
                  onClick={() => setMonths(opt.value)}
                  className={`px-2 py-1 text-xs rounded border ${
                    months === opt.value
                      ? "bg-blue-600 text-white border-blue-600"
                      : "text-gray-600 border-gray-300 hover:bg-gray-50"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">{t("schedule.filters.urgency")}</label>
            <div className="flex gap-1">
              {[
                { value: "all",    label: t("schedule.filters.urgency_values.all") },
                { value: "red",    label: t("schedule.filters.urgency_values.red") },
                { value: "yellow", label: t("schedule.filters.urgency_values.yellow") },
                { value: "green",  label: t("schedule.filters.urgency_values.green") },
              ].map(opt => (
                <button
                  key={opt.value}
                  onClick={() => setUrgencyFilter(opt.value)}
                  className={`px-2 py-1 text-xs rounded border ${
                    urgencyFilter === opt.value
                      ? "bg-gray-700 text-white border-gray-700"
                      : "text-gray-600 border-gray-300 hover:bg-gray-50"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Summary KPIs */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-xs font-medium text-red-700 uppercase tracking-wide">{t("schedule.kpi.critical")}</p>
          <p className="text-3xl font-bold text-red-700 mt-1">{red}</p>
        </div>
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-xs font-medium text-yellow-700 uppercase tracking-wide">{t("schedule.kpi.warning")}</p>
          <p className="text-3xl font-bold text-yellow-700 mt-1">{yellow}</p>
        </div>
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <p className="text-xs font-medium text-green-700 uppercase tracking-wide">{t("schedule.kpi.on_track")}</p>
          <p className="text-3xl font-bold text-green-700 mt-1">{green}</p>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400 text-sm">{t("common.loading")}</div>
        ) : filtered.length === 0 ? (
          <div className="p-8 text-center text-gray-400 text-sm italic">
            {activities.length === 0
              ? t("schedule.empty.no_deadlines", { months })
              : t("schedule.empty.no_deadlines_for_filter")}
          </div>
        ) : (
          <table className="w-full text-left">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="px-4 py-3 text-xs font-semibold text-gray-600 uppercase tracking-wide">{t("schedule.table.activity")}</th>
                <th className="px-4 py-3 text-xs font-semibold text-gray-600 uppercase tracking-wide">{t("schedule.table.category")}</th>
                <th className="px-4 py-3 text-xs font-semibold text-gray-600 uppercase tracking-wide">{t("schedule.table.due_date")}</th>
                <th className="px-4 py-3 text-xs font-semibold text-gray-600 uppercase tracking-wide">{t("schedule.table.days")}</th>
                <th className="px-4 py-3 text-xs font-semibold text-gray-600 uppercase tracking-wide">{t("schedule.table.status")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.map((item, idx) => (
                <ActivityRow key={`${item.category}-${item.ref_id}-${idx}`} item={item} />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
