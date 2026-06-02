import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { checklistsApi, type ChecklistRunItem } from "../../api/endpoints/checklists";
import { StatusBadge } from "../../components/ui/StatusBadge";
import i18n from "../../i18n";

export function ChecklistRunDetail() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { id } = useParams();

  const { data: run, isLoading } = useQuery({
    queryKey: ["checklist-run", id],
    queryFn: () => checklistsApi.getRun(id!),
    retry: false,
  });

  const itemMutation = useMutation({
    mutationFn: (payload: { item_id: string; checked: boolean; note?: string }) =>
      checklistsApi.completeItem(id!, payload),
    onSuccess: (updated) => qc.setQueryData(["checklist-run", id], updated),
  });

  const completeMutation = useMutation({
    mutationFn: () => checklistsApi.completeRun(id!),
    onSuccess: (updated) => {
      qc.setQueryData(["checklist-run", id], updated);
      qc.invalidateQueries({ queryKey: ["checklist-runs"] });
    },
  });

  if (isLoading || !run) {
    return <div className="p-8 text-center text-gray-400">{t("common.loading")}</div>;
  }

  const sortedItems = [...run.items].sort((a, b) => a.order - b.order);
  const allMandatoryChecked = sortedItems
    .filter((it) => it.is_mandatory)
    .every((it) => it.checked);
  const isCompleted = run.status === "completed";
  const pct = run.progress_total > 0 ? Math.round((run.progress_done / run.progress_total) * 100) : 0;

  function toggle(item: ChecklistRunItem) {
    if (isCompleted) return;
    itemMutation.mutate({ item_id: item.id, checked: !item.checked, note: item.note });
  }

  function updateNote(item: ChecklistRunItem, note: string) {
    itemMutation.mutate({ item_id: item.id, checked: item.checked, note });
  }

  return (
    <div className="max-w-2xl">
      <button
        onClick={() => navigate("/checklists/runs")}
        className="text-sm text-gray-500 hover:text-gray-700 mb-3"
      >
        ← {t("checklists.run.back")}
      </button>

      <div className="flex items-start justify-between mb-2">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">{run.template_name}</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            {run.plant_name} · {new Date(run.due_date).toLocaleDateString(i18n.language || "it")}
          </p>
        </div>
        <StatusBadge status={run.status} />
      </div>

      {/* Barra progresso */}
      <div className="mb-5">
        <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
          <span>{t("checklists.run.progress")}</span>
          <span>{run.progress_done}/{run.progress_total}</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
          <div
            className={`h-2 rounded-full transition-all ${isCompleted ? "bg-green-500" : "bg-primary-500"}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      {/* Item */}
      <div className="bg-white rounded-lg border border-gray-200 divide-y divide-gray-100">
        {sortedItems.map((item) => (
          <div key={item.id} className="p-3">
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={item.checked}
                disabled={isCompleted || itemMutation.isPending}
                onChange={() => toggle(item)}
                className="mt-0.5 h-5 w-5 rounded border-gray-300 text-primary-600 focus:ring-primary-400 disabled:opacity-60"
              />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className={`text-sm ${item.checked ? "text-gray-400 line-through" : "text-gray-800"}`}>
                    {item.text}
                  </span>
                  {item.is_mandatory ? (
                    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-red-100 text-red-700">
                      {t("checklists.run.mandatory")}
                    </span>
                  ) : (
                    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-gray-100 text-gray-500">
                      {t("checklists.run.optional")}
                    </span>
                  )}
                </div>
              </div>
            </label>
            {!isCompleted && (
              <input
                defaultValue={item.note}
                onBlur={(e) => {
                  if (e.target.value !== item.note) updateNote(item, e.target.value);
                }}
                placeholder={t("checklists.run.note_placeholder")}
                className="mt-2 ml-8 w-[calc(100%-2rem)] border rounded px-2 py-1 text-xs text-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-300"
              />
            )}
            {isCompleted && item.note && (
              <p className="mt-1 ml-8 text-xs text-gray-500 italic">{item.note}</p>
            )}
          </div>
        ))}
      </div>

      {/* Completa */}
      <div className="mt-5 flex items-center justify-between">
        {isCompleted ? (
          <p className="text-sm text-green-700">
            ✓ {t("checklists.run.completed_on")} {run.completed_at ? new Date(run.completed_at).toLocaleString(i18n.language || "it") : ""}
          </p>
        ) : (
          <>
            <p className="text-xs text-gray-400">
              {allMandatoryChecked ? t("checklists.run.ready_hint") : t("checklists.run.complete_hint")}
            </p>
            <button
              onClick={() => completeMutation.mutate()}
              disabled={!allMandatoryChecked || completeMutation.isPending}
              className="px-5 py-2 bg-primary-600 text-white rounded text-sm font-medium hover:bg-primary-700 disabled:opacity-50"
            >
              {completeMutation.isPending ? t("common.saving") : t("checklists.run.complete")}
            </button>
          </>
        )}
      </div>
      {completeMutation.isError && (
        <p className="text-sm text-red-600 mt-2 text-right">{t("common.save_error")}</p>
      )}
    </div>
  );
}
