import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { tasksApi, type Task } from "../../api/endpoints/tasks";
import { plantsApi } from "../../api/endpoints/plants";
import { useAuthStore } from "../../store/auth";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { useTranslation } from "react-i18next";
import i18n from "../../i18n";

type StatusFilter = "tutti" | "aperto" | "in_corso" | "completato" | "scaduto";

function NewTaskModal({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [form, setForm] = useState<Partial<Task>>({ priority: "media" });

  const { data: plants } = useQuery({
    queryKey: ["plants"],
    queryFn: () => plantsApi.list(),
    retry: false,
  });

  const mutation = useMutation({
    mutationFn: tasksApi.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tasks"] });
      onClose();
    },
  });

  function handleChange(
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value || undefined }));
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6">
        <h3 className="text-lg font-semibold mb-4">{t("tasks.new.title")}</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("tasks.fields.title")}</label>
            <input
              name="title"
              onChange={handleChange}
              className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("tasks.fields.priority")}</label>
              <select
                name="priority"
                defaultValue="media"
                onChange={handleChange}
                className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
              >
                {["bassa", "media", "alta", "critica"].map((p) => (
                  <option key={p} value={p}>{t(`tasks.priority.${p}`)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("tasks.fields.due_date")}</label>
              <input
                type="date"
                name="due_date"
                onChange={handleChange}
                className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("tasks.fields.plant")}</label>
            <select
              name="plant"
              onChange={handleChange}
              className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
            >
              <option value="">{t("common.optional")}</option>
              {(plants ?? []).map(p => (
                <option key={p.id} value={p.id}>{p.code} — {p.name}</option>
              ))}
            </select>
          </div>
        </div>
        {mutation.isError && (
          <p className="text-sm text-red-600 mt-2">{t("common.save_error")}</p>
        )}
        <div className="flex justify-end gap-2 mt-4">
          <button
            onClick={onClose}
            className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50"
          >
            {t("actions.cancel")}
          </button>
          <button
            onClick={() => mutation.mutate(form)}
            disabled={mutation.isPending}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? t("common.saving") : t("tasks.new.submit")}
          </button>
        </div>
      </div>
    </div>
  );
}

function isDuePast(due_date: string | null): boolean {
  if (!due_date) return false;
  return new Date(due_date) < new Date();
}

export function TasksPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("tutti");
  const [showNew, setShowNew] = useState(false);
  const qc = useQueryClient();
  const selectedPlant = useAuthStore(s => s.selectedPlant);

  const params: Record<string, string> = {};
  if (statusFilter !== "tutti") params.status = statusFilter;
  if (selectedPlant?.id) params.plant = selectedPlant.id;

  const { data, isLoading } = useQuery({
    queryKey: ["tasks", statusFilter, selectedPlant?.id],
    queryFn: () => tasksApi.list(params),
    retry: false,
  });

  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const completeMutation = useMutation({
    mutationFn: (id: string) => tasksApi.complete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tasks"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => tasksApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tasks"] });
      setConfirmDeleteId(null);
    },
  });

  const tasks: Task[] = data?.results ?? [];

  const STATUS_FILTERS: { label: string; value: StatusFilter }[] = [
    { label: t("tasks.filters.all"), value: "tutti" },
    { label: t("tasks.filters.open"), value: "aperto" },
    { label: t("tasks.filters.in_progress"), value: "in_corso" },
    { label: t("tasks.filters.completed"), value: "completato" },
    { label: t("tasks.filters.overdue"), value: "scaduto" },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">{t("tasks.title")}</h2>
        <button
          onClick={() => setShowNew(true)}
          className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700"
        >
          + {t("tasks.new.submit")}
        </button>
      </div>

      <div className="mb-4 flex items-center gap-1">
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

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">{t("common.loading")}</div>
        ) : tasks.length === 0 ? (
          <div className="p-8 text-center text-gray-400">{t("tasks.empty")}</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("tasks.table.title")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("tasks.table.priority")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("tasks.table.status")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("tasks.table.due_date")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("tasks.table.source")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("tasks.table.escalation")}</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {tasks.map((task) => {
                const overdue =
                  task.status !== "completato" &&
                  task.status !== "annullato" &&
                  isDuePast(task.due_date);
                return (
                  <tr
                    key={task.id}
                    className={`transition-colors ${
                      overdue ? "bg-red-50 hover:bg-red-100" : "hover:bg-gray-50"
                    }`}
                  >
                    <td className="px-4 py-3 font-medium text-gray-800">
                      {task.source_module === "M03" && task.control_instance ? (
                        <button
                          onClick={() => navigate("/controls", { state: { openControlInstance: task.control_instance } })}
                          className="text-left text-primary-700 hover:underline hover:text-primary-900 font-medium"
                          title={t("tasks.actions.open_control")}
                        >
                          {task.title}
                        </button>
                      ) : (
                        task.title
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={task.priority} />
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={task.status} />
                    </td>
                    <td className="px-4 py-3 text-xs">
                      {task.due_date ? (
                        <span className={overdue ? "text-red-600 font-medium" : "text-gray-500"}>
                          {new Date(task.due_date).toLocaleDateString(i18n.language || "it")}
                        </span>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">{task.source}</td>
                    <td className="px-4 py-3">
                      {task.escalation_level > 0 && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-orange-100 text-orange-800">
                          Lv {task.escalation_level}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {(task.status === "aperto" || task.status === "in_corso") && (
                          <button
                            onClick={() => completeMutation.mutate(task.id)}
                            disabled={completeMutation.isPending}
                            className="text-xs text-gray-500 hover:text-green-700 border border-gray-300 rounded px-2 py-0.5 hover:border-green-400 disabled:opacity-50"
                          >
                            {t("tasks.actions.complete")}
                          </button>
                        )}
                        {confirmDeleteId === task.id ? (
                          <>
                            <button
                              onClick={() => deleteMutation.mutate(task.id)}
                              disabled={deleteMutation.isPending}
                              className="text-xs text-white bg-red-600 hover:bg-red-700 rounded px-2 py-0.5 disabled:opacity-50"
                            >
                              {t("actions.confirm")}
                            </button>
                            <button
                              onClick={() => setConfirmDeleteId(null)}
                              className="text-xs text-gray-500 hover:text-gray-700"
                            >
                              {t("actions.cancel")}
                            </button>
                          </>
                        ) : (
                          <button
                            onClick={() => setConfirmDeleteId(task.id)}
                            className="text-xs text-gray-400 hover:text-red-600"
                            title={t("actions.delete")}
                          >
                            ✕
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {showNew && <NewTaskModal onClose={() => setShowNew(false)} />}
    </div>
  );
}
