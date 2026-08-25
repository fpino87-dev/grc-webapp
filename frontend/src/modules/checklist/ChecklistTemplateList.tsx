import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  checklistsApi,
  CHECKLIST_FREQUENCIES,
  type ChecklistFrequency,
  type ChecklistTemplate,
} from "../../api/endpoints/checklists";
import { plantsApi } from "../../api/endpoints/plants";

type FrequencyFilter = "" | ChecklistFrequency;

export function ChecklistTemplateList() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [plantFilter, setPlantFilter] = useState("");
  const [freqFilter, setFreqFilter] = useState<FrequencyFilter>("");
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  // Template per cui è aperto il pannello di avvio manuale.
  const [startTpl, setStartTpl] = useState<ChecklistTemplate | null>(null);
  const [startPlant, setStartPlant] = useState("");
  const [startDue, setStartDue] = useState("");

  const { data: plants } = useQuery({
    queryKey: ["plants"],
    queryFn: () => plantsApi.list(),
    retry: false,
  });

  const params: Record<string, string> = {};
  if (plantFilter) params.plant = plantFilter;
  if (freqFilter) params.frequency = freqFilter;

  const { data, isLoading } = useQuery({
    queryKey: ["checklist-templates", plantFilter, freqFilter],
    queryFn: () => checklistsApi.listTemplates(params),
    retry: false,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => checklistsApi.deleteTemplate(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["checklist-templates"] });
      setConfirmDeleteId(null);
    },
  });

  const startMutation = useMutation({
    mutationFn: () =>
      checklistsApi.startRun(startTpl!.id, {
        ...(startPlant ? { plant: startPlant } : {}),
        ...(startDue ? { due_date: startDue } : {}),
      }),
    onSuccess: (run) => {
      qc.invalidateQueries({ queryKey: ["checklist-runs"] });
      closeStart();
      navigate(`/checklists/runs/${run.id}`);
    },
  });

  function openStart(tpl: ChecklistTemplate) {
    setStartTpl(tpl);
    setStartPlant("");
    setStartDue("");
    startMutation.reset();
  }

  function closeStart() {
    setStartTpl(null);
    setStartPlant("");
    setStartDue("");
  }

  const templates: ChecklistTemplate[] = data?.results ?? [];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">{t("checklists.templates.title")}</h2>
        <button
          onClick={() => navigate("/checklists/templates/new")}
          className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700"
        >
          + {t("checklists.templates.new")}
        </button>
      </div>

      <div className="mb-4 flex items-center gap-3">
        <select
          value={plantFilter}
          onChange={(e) => setPlantFilter(e.target.value)}
          className="border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
        >
          <option value="">{t("checklists.templates.all_plants")}</option>
          {(plants ?? []).map((p) => (
            <option key={p.id} value={p.id}>{p.code} — {p.name}</option>
          ))}
        </select>
        <select
          value={freqFilter}
          onChange={(e) => setFreqFilter(e.target.value as FrequencyFilter)}
          className="border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
        >
          <option value="">{t("checklists.templates.all_frequencies")}</option>
          {CHECKLIST_FREQUENCIES.map((f) => (
            <option key={f} value={f}>{t(`checklists.frequency.${f}`)}</option>
          ))}
        </select>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">{t("common.loading")}</div>
        ) : templates.length === 0 ? (
          <div className="p-8 text-center text-gray-400">{t("checklists.templates.empty")}</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("checklists.templates.table.name")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("checklists.templates.table.frequency")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("checklists.templates.table.plant")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("checklists.templates.table.active")}</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {templates.map((tpl) => (
                <tr key={tpl.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">
                    <button
                      onClick={() => navigate(`/checklists/templates/${tpl.id}/edit`)}
                      className="text-left text-primary-700 hover:underline hover:text-primary-900 font-medium"
                    >
                      {tpl.name}
                    </button>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{t(`checklists.frequency.${tpl.frequency}`)}</td>
                  <td className="px-4 py-3 text-gray-600">{tpl.plant_name ?? t("checklists.templates.all_plants_short")}</td>
                  <td className="px-4 py-3">
                    {tpl.is_active ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700">
                        {t("checklists.templates.active_yes")}
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-500">
                        {t("checklists.templates.active_no")}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-2">
                      {confirmDeleteId === tpl.id ? (
                        <>
                          <button
                            onClick={() => deleteMutation.mutate(tpl.id)}
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
                        <>
                          <button
                            onClick={() => openStart(tpl)}
                            disabled={!tpl.is_active}
                            className="text-xs text-primary-700 hover:text-primary-900 border border-primary-300 rounded px-2 py-0.5 hover:bg-primary-50 disabled:opacity-40 disabled:hover:bg-transparent"
                            title={t("checklists.templates.start_now_hint")}
                          >
                            ▶ {t("checklists.templates.start_now")}
                          </button>
                          <button
                            onClick={() => setConfirmDeleteId(tpl.id)}
                            className="text-xs text-gray-400 hover:text-red-600"
                            title={t("actions.delete")}
                          >
                            ✕
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {startTpl && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/30 p-4">
          <div className="bg-white rounded-lg shadow-lg border border-gray-200 w-full max-w-md p-5">
            <h3 className="text-base font-semibold text-gray-900 mb-1">
              {t("checklists.templates.start_now")}
            </h3>
            <p className="text-sm text-gray-600 mb-4">{startTpl.name}</p>

            {!startTpl.plant && (
              <div className="mb-3">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t("checklists.templates.plant")}
                </label>
                <select
                  value={startPlant}
                  onChange={(e) => setStartPlant(e.target.value)}
                  className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
                >
                  <option value="">{t("checklists.templates.start_pick_plant")}</option>
                  {(plants ?? []).map((p) => (
                    <option key={p.id} value={p.id}>{p.code} — {p.name}</option>
                  ))}
                </select>
              </div>
            )}

            <div className="mb-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t("checklists.templates.start_due_date")}
              </label>
              <input
                type="date"
                value={startDue}
                onChange={(e) => setStartDue(e.target.value)}
                className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
              />
              <p className="text-xs text-gray-500 mt-1">
                {t("checklists.templates.start_due_date_hint")}
              </p>
            </div>

            {startMutation.isError && (
              <p className="text-sm text-red-600 mt-2">{t("common.save_error")}</p>
            )}

            <div className="flex justify-end gap-2 pt-4">
              <button
                onClick={closeStart}
                className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50"
              >
                {t("actions.cancel")}
              </button>
              <button
                onClick={() => startMutation.mutate()}
                disabled={
                  startMutation.isPending || (!startTpl.plant && !startPlant)
                }
                className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
              >
                {startMutation.isPending
                  ? t("common.saving")
                  : t("checklists.templates.start_confirm")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
