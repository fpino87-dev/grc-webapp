import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { checklistsApi, type ChecklistRun } from "../../api/endpoints/checklists";
import { plantsApi } from "../../api/endpoints/plants";
import { useAuthStore } from "../../store/auth";
import { StatusBadge } from "../../components/ui/StatusBadge";
import i18n from "../../i18n";

type StatusFilter = "" | "pending" | "in_progress" | "completed" | "overdue";

// Allineato a ChecklistRunDeletePermission (backend): chi configura le
// checklist può cancellarne un run, chi le esegue no.
const RUN_DELETE_ROLES = ["super_admin", "compliance_officer", "risk_manager"];
const REASON_MIN_LENGTH = 10;

function DeleteRunModal({ run, onClose }: { run: ChecklistRun; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");

  const deleteMutation = useMutation({
    mutationFn: () => checklistsApi.deleteRun(run.id, reason.trim()),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["checklist-runs"] });
      onClose();
    },
    onError: (e: unknown) => {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        || t("checklists.runs.delete.error_generic");
      setError(String(msg));
    },
  });

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <h3 className="text-lg font-semibold mb-2">{t("checklists.runs.delete.modal_title")}</h3>
        <p className="text-sm text-gray-600 mb-3">
          {t("checklists.runs.delete.modal_intro", {
            name: run.template_name,
            date: new Date(run.due_date).toLocaleDateString(i18n.language || "it"),
          })}
        </p>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {t("checklists.runs.delete.reason_label")}
        </label>
        <textarea
          className="w-full border rounded px-3 py-2 text-sm min-h-[80px] focus:outline-none focus:ring-2 focus:ring-primary-400"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder={t("checklists.runs.delete.reason_placeholder")}
        />
        {error && (
          <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded mt-2">{error}</p>
        )}
        <div className="flex justify-end gap-2 mt-4">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50"
          >
            {t("actions.cancel")}
          </button>
          <button
            type="button"
            onClick={() => deleteMutation.mutate()}
            disabled={reason.trim().length < REASON_MIN_LENGTH || deleteMutation.isPending}
            className="px-4 py-2 bg-red-600 text-white rounded text-sm hover:bg-red-700 disabled:opacity-50"
          >
            {deleteMutation.isPending
              ? t("checklists.runs.delete.in_progress")
              : t("checklists.runs.delete.confirm")}
          </button>
        </div>
      </div>
    </div>
  );
}

export function ChecklistRunList() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const selectedPlant = useAuthStore((s) => s.selectedPlant);
  const canDelete = RUN_DELETE_ROLES.includes(useAuthStore((s) => s.user?.role ?? ""));
  const [deleteRun, setDeleteRun] = useState<ChecklistRun | null>(null);
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
                {canDelete && <th className="px-4 py-3"></th>}
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
                  {canDelete && (
                    <td className="px-4 py-3 text-right">
                      {/* Un run completato è l'evidenza del controllo eseguito: non si cancella. */}
                      {run.status !== "completed" && (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setDeleteRun(run);
                          }}
                          title={t("checklists.runs.delete.tooltip")}
                          className="text-xs text-gray-400 hover:text-red-600"
                        >
                          ✕
                        </button>
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {deleteRun && <DeleteRunModal run={deleteRun} onClose={() => setDeleteRun(null)} />}
    </div>
  );
}
