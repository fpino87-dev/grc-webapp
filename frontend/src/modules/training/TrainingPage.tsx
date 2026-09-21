import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { trainingApi } from "../../api/endpoints/training";
import { ModuleHelp } from "../../components/ui/ModuleHelp";
import { useAuthStore } from "../../store/auth";
import { AudiencesTab } from "./AudiencesTab";
import { CoursesTab } from "./CoursesTab";
import { PlanTab } from "./PlanTab";
import { SessionsTab } from "./SessionsTab";

// Formazione a evidenze: la piattaforma non eroga la formazione e non si
// integra con l'e-learning, ne governa lo svolgimento. Piano → erogazioni con
// file di prova → evidenze sui controlli → KPI e obiettivi.

type Tab = "plan" | "sessions" | "audiences" | "courses";
const RECORD_TABS: Tab[] = ["plan", "sessions", "audiences"];

export function TrainingPage() {
  const { t } = useTranslation();
  const plant = useAuthStore(s => s.selectedPlant);
  const { data: caps, isLoading } = useQuery({
    queryKey: ["training-capabilities"],
    queryFn: trainingApi.capabilities,
  });
  const [tab, setTab] = useState<Tab | null>(null);

  if (isLoading || !caps) {
    return <div className="p-8 text-center text-gray-400">{t("common.loading")}</div>;
  }
  const tabs: Tab[] = caps.can_read_records ? [...RECORD_TABS, "courses"] : ["courses"];
  const current = tab && tabs.includes(tab) ? tab : tabs[0];
  const canManageSite = !!plant && caps.manage_plant_ids.includes(plant.id);

  return (
    <div>
      <div className="flex items-center mb-1">
        <h2 className="text-xl font-semibold text-gray-900">{t("training.title")}</h2>
        <ModuleHelp
          title={t("training.help.title")}
          description={t("training.help.description")}
          steps={[1, 2, 3, 4, 5].map(n => t(`training.help.steps.${n}`))}
          connections={[
            { module: "M07", relation: t("training.help.connections.documents") },
            { module: "M03", relation: t("training.help.connections.controls") },
            { module: "M08 KPI", relation: t("training.help.connections.kpi") },
            { module: "M00", relation: t("training.help.connections.objectives") },
          ]}
        />
      </div>
      <p className="text-sm text-gray-500 mb-4">{t("training.subtitle")}</p>

      <div className="flex gap-1 border-b border-gray-200 mb-5 overflow-x-auto">
        {tabs.map(k => (
          <button key={k} onClick={() => setTab(k)}
                  className={`px-4 py-2 text-sm font-medium whitespace-nowrap border-b-2 -mb-px ${
                    current === k ? "border-primary-600 text-primary-700" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
            {t(`training.tabs.${k}`)}
          </button>
        ))}
      </div>

      {current === "courses" ? (
        <CoursesTab canManage={caps.can_manage_courses} />
      ) : !plant ? (
        <div className="bg-white border border-gray-200 rounded-lg p-8 text-center text-gray-500 text-sm">
          {t("training.select_plant")}
        </div>
      ) : current === "plan" ? (
        <PlanTab plantId={plant.id} caps={caps} />
      ) : current === "sessions" ? (
        <SessionsTab plantId={plant.id} canManage={canManageSite} />
      ) : (
        <AudiencesTab plantId={plant.id} canManage={canManageSite} />
      )}
    </div>
  );
}
