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

  const { data, isLoading } = useQuery({
    queryKey: ["kpi-definitions"],
    queryFn: () => kpiApi.getKpiDefinitions(),
    retry: false,
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
                  <td className="px-4 py-3 text-gray-500">{t(`kpi.source.${kpi.source}`)}</td>
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
                      <button
                        onClick={() => setConfirmDeleteId(kpi.id)}
                        className="text-xs text-gray-400 hover:text-red-600"
                        title={t("actions.delete")}
                      >
                        ✕
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showWizard && (
        <KpiSuggestWizard
          initialPlantId={selectedPlant?.id}
          onClose={() => setShowWizard(false)}
          onImported={() => qc.invalidateQueries({ queryKey: ["kpi-definitions"] })}
        />
      )}
    </div>
  );
}
