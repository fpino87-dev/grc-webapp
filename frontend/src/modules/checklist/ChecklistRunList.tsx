import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { checklistsApi, type ChecklistRun } from "../../api/endpoints/checklists";
import { plantsApi } from "../../api/endpoints/plants";
import { useAuthStore } from "../../store/auth";
import { StatusBadge } from "../../components/ui/StatusBadge";
import i18n from "../../i18n";

type StatusFilter = "" | "pending" | "in_progress" | "completed" | "overdue";

export function ChecklistRunList() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const selectedPlant = useAuthStore((s) => s.selectedPlant);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("");
  const [plantFilter, setPlantFilter] = useState("");

  const { data: plants } = useQuery({
    queryKey: ["plants"],
    queryFn: () => plantsApi.list(),
    retry: false,
  });

  const params: Record<string, string> = {};
  if (statusFilter) params.status = statusFilter;
  const effectivePlant = plantFilter || selectedPlant?.id || "";
  if (effectivePlant) params.plant = effectivePlant;

  const { data, isLoading } = useQuery({
    queryKey: ["checklist-runs", statusFilter, effectivePlant],
    queryFn: () => checklistsApi.listRuns(params),
    retry: false,
  });

  const runs: ChecklistRun[] = data?.results ?? [];

  const STATUS_FILTERS: { label: string; value: StatusFilter }[] = [
    { label: t("checklists.runs.filters.all"), value: "" },
    { label: t("checklists.status.pending"), value: "pending" },
    { label: t("checklists.status.in_progress"), value: "in_progress" },
    { label: t("checklists.status.completed"), value: "completed" },
    { label: t("checklists.status.overdue"), value: "overdue" },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">{t("checklists.runs.title")}</h2>
      </div>

      <div className="mb-4 flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-1">
          {STATUS_FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setStatusFilter(f.value)}
              className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                statusFilter === f.value
                  ? "bg-primary-600 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
        <select
          value={plantFilter}
          onChange={(e) => setPlantFilter(e.target.value)}
          className="border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
        >
          <option value="">{t("checklists.runs.all_plants")}</option>
          {(plants ?? []).map((p) => (
            <option key={p.id} value={p.id}>{p.code} — {p.name}</option>
          ))}
        </select>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">{t("common.loading")}</div>
        ) : runs.length === 0 ? (
          <div className="p-8 text-center text-gray-400">{t("checklists.runs.empty")}</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("checklists.runs.table.template")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("checklists.runs.table.plant")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("checklists.runs.table.due_date")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("checklists.runs.table.progress")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("checklists.runs.table.status")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {runs.map((run) => (
                <tr
                  key={run.id}
                  onClick={() => navigate(`/checklists/runs/${run.id}`)}
                  className={`cursor-pointer transition-colors ${
                    run.status === "overdue" ? "bg-red-50 hover:bg-red-100" : "hover:bg-gray-50"
                  }`}
                >
                  <td className="px-4 py-3 font-medium text-primary-700">{run.template_name}</td>
                  <td className="px-4 py-3 text-gray-600">{run.plant_name ?? "—"}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">
                    {new Date(run.due_date).toLocaleDateString(i18n.language || "it")}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">
                    {run.progress_done}/{run.progress_total}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={run.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
