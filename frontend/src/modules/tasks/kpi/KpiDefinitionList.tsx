import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { kpiApi, type KpiDefinitionListItem } from "../../../api/endpoints/kpi";
import { useAuthStore } from "../../../store/auth";
import { KpiSuggestWizard } from "./KpiSuggestWizard";

export function KpiDefinitionList() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const selectedPlant = useAuthStore((s) => s.selectedPlant);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [showWizard, setShowWizard] = useState(false);
  // KPI per cui è aperto l'inserimento manuale del valore.
  const [recordingId, setRecordingId] = useState<string | null>(null);
  const [value, setValue] = useState("");
  const [note, setNote] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["kpi-definitions"],
    queryFn: () => kpiApi.getKpiDefinitions(),
    retry: false,
  });

  const recordMutation = useMutation({
    mutationFn: () =>
      kpiApi.recordKpiValue(recordingId!, {
        value: Number(value),
        note,
        ...(selectedPlant ? { plant: selectedPlant.id } : {}),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["kpi-definitions"] });
      qc.invalidateQueries({ queryKey: ["kpi-snapshots"] });
      setRecordingId(null);
      setValue("");
      setNote("");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => kpiApi.deleteKpiDefinition(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["kpi-definitions"] });
      setConfirmDeleteId(null);
    },
  });

  const kpis: KpiDefinitionListItem[] = data?.results ?? [];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">{t("kpi.definitions.title")}</h2>
        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate("/kpi")}
            className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50"
          >
            ← {t("kpi.definitions.back_dashboard")}
          </button>
          <button
            onClick={() => setShowWizard(true)}
            className="px-4 py-2 border border-primary-300 text-primary-700 rounded text-sm hover:bg-primary-50"
          >
            ✨ {t("kpi.suggest.button")}
          </button>
          <button
            onClick={() => navigate("/kpi/definitions/new")}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700"
          >
            + {t("kpi.definitions.new")}
          </button>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">{t("common.loading")}</div>
        ) : kpis.length === 0 ? (
          <div className="p-8 text-center text-gray-400">{t("kpi.definitions.empty")}</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("kpi.definitions.table.code")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("kpi.definitions.table.name")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("kpi.definitions.table.source")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("kpi.definitions.table.warning")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("kpi.definitions.table.critical")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("kpi.definitions.table.active")}</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {kpis.map((kpi) => (
                <tr key={kpi.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">
                    <button
                      onClick={() => navigate(`/kpi/definitions/${kpi.id}/edit`)}
                      className="text-left font-mono text-xs text-primary-700 hover:underline"
                    >
                      {kpi.kpi_code}
                    </button>
                  </td>
                  <td className="px-4 py-3 text-gray-800">{kpi.name}</td>
                  <td className="px-4 py-3 text-gray-500">
                    {t(`kpi.source.${kpi.source}`)}
                    {kpi.source === "api" && (
                      <span
                        title={t("kpi.definitions.needs_feed_hint")}
                        className="ml-2 inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-medium bg-amber-100 text-amber-700"
                      >
                        {t("kpi.definitions.needs_feed")}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{kpi.threshold_warning ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{kpi.threshold_critical ?? "—"}</td>
                  <td className="px-4 py-3">
                    {kpi.is_active ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700">
                        {t("common.yes")}
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-500">
                        {t("common.no")}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {confirmDeleteId === kpi.id ? (
                      <span className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => deleteMutation.mutate(kpi.id)}
                          disabled={deleteMutation.isPending}
                          className="text-xs text-white bg-red-600 hover:bg-red-700 rounded px-2 py-0.5 disabled:opacity-50"
                        >
                          {t("actions.confirm")}
                        </button>
                        <button onClick={() => setConfirmDeleteId(null)} className="text-xs text-gray-500 hover:text-gray-700">
                          {t("actions.cancel")}
                        </button>
                      </span>
                    ) : (
                      <span className="flex items-center justify-end gap-2">
                        {(kpi.source === "api" || kpi.source === "manual") && (
                          <button
                            onClick={() => {
                              setRecordingId(recordingId === kpi.id ? null : kpi.id);
                              setValue("");
                              setNote("");
                              recordMutation.reset();
                            }}
                            className="text-xs text-primary-700 hover:text-primary-900 border border-primary-300 rounded px-2 py-0.5 hover:bg-primary-50"
                          >
                            {recordingId === kpi.id ? t("common.close") : t("kpi.definitions.record_value")}
                          </button>
                        )}
                        <button
                          onClick={() => setConfirmDeleteId(kpi.id)}
                          className="text-xs text-gray-400 hover:text-red-600"
                          title={t("actions.delete")}
                        >
                          ✕
                        </button>
                      </span>
                    )}
                  </td>
                </tr>
              ))}
              {recordingId && (
                <tr>
                  <td colSpan={7} className="px-4 pb-4 bg-primary-50/30">
                    <div className="flex flex-wrap items-end gap-2 pt-3">
                      <label className="text-xs text-gray-600">
                        {t("kpi.definitions.value")}
                        <input
                          type="number"
                          step="any"
                          value={value}
                          onChange={(e) => setValue(e.target.value)}
                          className="block w-32 border rounded px-2 py-1 text-sm mt-0.5"
                        />
                      </label>
                      <label className="flex-1 min-w-[16rem] text-xs text-gray-600">
                        {t("kpi.definitions.value_note")}
                        <input
                          value={note}
                          onChange={(e) => setNote(e.target.value)}
                          placeholder={t("kpi.definitions.value_note_placeholder")}
                          className="block w-full border rounded px-2 py-1 text-sm mt-0.5"
                        />
                      </label>
                      <button
                        onClick={() => recordMutation.mutate()}
                        disabled={value === "" || recordMutation.isPending}
                        className="px-3 py-1.5 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
                      >
                        {recordMutation.isPending ? t("common.saving") : t("actions.save")}
                      </button>
                    </div>
                    <p className="text-xs text-gray-500 mt-1.5">
                      {t("kpi.definitions.value_hint")}
                    </p>
                    {recordMutation.isError && (
                      <p className="text-sm text-red-600 mt-1">{t("common.save_error")}</p>
                    )}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      {showWizard && (
        <KpiSuggestWizard
          initialPlantId={selectedPlant?.id}
          onClose={() => setShowWizard(false)}
          onImported={() => {
            qc.invalidateQueries({ queryKey: ["kpi-definitions"] });
            qc.invalidateQueries({ queryKey: ["checklist-templates"] });
          }}
        />
      )}
    </div>
  );
}
