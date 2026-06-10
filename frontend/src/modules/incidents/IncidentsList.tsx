import { useEffect, useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { incidentsApi, type Incident } from "../../api/endpoints/incidents";
import { plantsApi } from "../../api/endpoints/plants";
import { useAuthStore } from "../../store/auth";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { ModuleHelp } from "../../components/ui/ModuleHelp";
import { NewIncidentForm } from "./NewIncidentForm";
import { Nis2ConfigPanel } from "./Nis2ConfigPanel";
import { IncidentDetailModal } from "./IncidentDetailModal";
import { useTranslation } from "react-i18next";
import i18n from "../../i18n";

export function IncidentsList() {
  const { t } = useTranslation();
  const [showNew, setShowNew] = useState(false);
  const [selected, setSelected] = useState<Incident | null>(null);
  const [moduleView, setModuleView] = useState<"list" | "nis2_config">("list");
  const qc = useQueryClient();
  const selectedPlant = useAuthStore(s => s.selectedPlant);
  const user = useAuthStore(s => s.user);

  const params: Record<string, string> = {};
  if (selectedPlant?.id) params.plant = selectedPlant.id;

  const { data, isLoading } = useQuery({
    queryKey: ["incidents", selectedPlant?.id],
    queryFn: () => incidentsApi.list(params),
    retry: false,
  });

  const { data: plants } = useQuery({
    queryKey: ["plants"],
    queryFn: () => plantsApi.list(),
    retry: false,
  });

  const closeMutation = useMutation({
    mutationFn: incidentsApi.close,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["incidents"] }),
  });
  const deleteMutation = useMutation({
    mutationFn: incidentsApi.delete,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["incidents"] });
      setSelected(null);
    },
  });

  const incidents = data?.results ?? [];
  const canSeeConfig = user?.role === "super_admin" || user?.role === "compliance_officer";
  const dateLocale = i18n.language || "it";

  useEffect(() => {
    if (moduleView === "nis2_config") {
      setSelected(null);
    }
  }, [moduleView]);

  const selectedPlantCountry = useMemo(() => {
    return plants?.find(p => p.id === selectedPlant?.id)?.country ?? "IT";
  }, [plants, selectedPlant?.id]);

  return (
    <div>
      <div className="flex flex-col gap-3 mb-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-4">
          <h2 className="text-xl font-semibold text-gray-900 flex items-center">
            {t("incidents.title")}
            <ModuleHelp
              title={t("incidents.help.title")}
              description={t("incidents.help.description")}
              steps={[
                t("incidents.help.steps.1"),
                t("incidents.help.steps.2"),
                t("incidents.help.steps.3"),
                t("incidents.help.steps.4"),
                t("incidents.help.steps.5"),
              ]}
              connections={[
                { module: t("incidents.help.connections.pdca.module"), relation: t("incidents.help.connections.pdca.relation") },
                { module: t("incidents.help.connections.lessons.module"), relation: t("incidents.help.connections.lessons.relation") },
                { module: t("incidents.help.connections.tasks.module"), relation: t("incidents.help.connections.tasks.relation") },
              ]}
              configNeeded={[t("incidents.help.config_needed.1")]}
            />
          </h2>
          <div className="flex rounded-lg border border-gray-200 bg-gray-50 p-0.5 w-fit">
            <button
              type="button"
              onClick={() => setModuleView("list")}
              className={`px-3 py-1.5 text-xs rounded-md whitespace-nowrap ${
                moduleView === "list" ? "bg-white shadow text-primary-700 font-medium" : "text-gray-600 hover:text-gray-800"
              }`}
            >
              {t("incidents.views.list")}
            </button>
            {canSeeConfig && (
              <button
                type="button"
                onClick={() => setModuleView("nis2_config")}
                className={`px-3 py-1.5 text-xs rounded-md whitespace-nowrap ${
                  moduleView === "nis2_config" ? "bg-white shadow text-primary-700 font-medium" : "text-gray-600 hover:text-gray-800"
                }`}
              >
                {t("incidents.views.nis2_config")}
              </button>
            )}
          </div>
        </div>
        {moduleView === "list" && (
          <button
            onClick={() => setShowNew(true)}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 w-fit"
          >
            {t("incidents.new.open")}
          </button>
        )}
      </div>

      {moduleView === "list" && (
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">{t("common.loading")}</div>
        ) : incidents.length === 0 ? (
          <div className="p-8 text-center text-gray-400">{t("incidents.empty")}</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("incidents.table.title")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("incidents.table.severity")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("incidents.table.nis2")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("incidents.table.status")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("incidents.table.detected_at")}</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {incidents.map((inc) => (
                <tr key={inc.id} className="hover:bg-gray-50 transition-colors cursor-pointer" onClick={() => setSelected(inc)}>
                  <td className="px-4 py-3 font-medium text-gray-800">{inc.title}</td>
                  <td className="px-4 py-3"><StatusBadge status={inc.severity} /></td>
                  <td className="px-4 py-3"><StatusBadge status={inc.nis2_notifiable} /></td>
                  <td className="px-4 py-3"><StatusBadge status={inc.status} /></td>
                  <td className="px-4 py-3 text-gray-500 text-xs">
                    {new Date(inc.detected_at).toLocaleString(dateLocale)}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1">
                      {inc.status !== "chiuso" && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            closeMutation.mutate(inc.id);
                          }}
                          className="text-xs text-gray-500 hover:text-red-600 border border-gray-300 rounded px-2 py-0.5 hover:border-red-300"
                        >
                          {t("common.close")}
                        </button>
                      )}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          if (confirm(t("incidents.delete_confirm", { title: inc.title }))) deleteMutation.mutate(inc.id);
                        }}
                        className="text-xs text-gray-400 hover:text-red-600 border border-gray-200 rounded px-2 py-0.5 hover:border-red-300"
                      >
                        🗑
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      )}

      {moduleView === "nis2_config" && canSeeConfig && !selectedPlant && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          {t("incidents.nis2_config_select_plant")}
        </div>
      )}

      {moduleView === "nis2_config" && canSeeConfig && selectedPlant && (
        <Nis2ConfigPanel plantId={selectedPlant.id} plantCountry={selectedPlantCountry} />
      )}

      {moduleView === "list" && showNew && plants && (
        <NewIncidentForm plants={plants} onClose={() => setShowNew(false)} />
      )}

      {selected && (
        <IncidentDetailModal
          incident={selected}
          plants={plants}
          onChange={setSelected}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}
