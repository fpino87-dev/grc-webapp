import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import type { BcpPlan } from "../../api/endpoints/bcp";
import { plantsApi } from "../../api/endpoints/plants";
import { ModuleHelp } from "../../components/ui/ModuleHelp";
import { useAuthStore } from "../../store/auth";
import { BcpCoverageTab } from "./BcpCoverageTab";
import { BcpPlanForm } from "./BcpPlanForm";
import { BcpPlansTab } from "./BcpPlansTab";
import { BcpRecordTest } from "./BcpRecordTest";
import { BcpTestsTab } from "./BcpTestsTab";

const TABS = ["coverage", "plans", "tests"] as const;
type Tab = typeof TABS[number];

type FormState = { plan?: BcpPlan; plantId?: string; processId?: string } | null;

export function BcpPage() {
  const { t } = useTranslation();
  const selectedPlant = useAuthStore(s => s.selectedPlant);
  const plantId = selectedPlant?.id;
  const [form, setForm] = useState<FormState>(null);
  const [testPlan, setTestPlan] = useState<BcpPlan | null>(null);

  // Il tab aperto resta nell'indirizzo (?tab=), così un link porta allo stesso tab.
  const [searchParams, setSearchParams] = useSearchParams();
  const requested = searchParams.get("tab");
  const tab: Tab = (TABS as readonly string[]).includes(requested ?? "") ? (requested as Tab) : "coverage";
  const setTab = (next: Tab) => {
    const params = new URLSearchParams(searchParams);
    params.set("tab", next);
    setSearchParams(params, { replace: true });
  };

  const { data: plants = [] } = useQuery({
    queryKey: ["plants"],
    queryFn: () => plantsApi.list(),
    retry: false,
  });
  const plantLabel = (id: string | null) => {
    const p = plants.find(x => x.id === id);
    return p ? `${p.code} — ${p.name}` : "—";
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900 flex items-center">
          {t("bcp.title")}
          <ModuleHelp
            title={t("bcp.help.title")}
            description={t("bcp.help.description")}
            steps={[1, 2, 3, 4, 5, 6].map(n => t(`bcp.help.steps.${n}`))}
            connections={[
              { module: "M05 BIA", relation: t("bcp.help.connections.bia") },
              { module: "M07 Documenti", relation: t("bcp.help.connections.documents") },
              { module: "M11 PDCA", relation: t("bcp.help.connections.pdca") },
              { module: "M13 / M18", relation: t("bcp.help.connections.reporting") },
            ]}
            configNeeded={[t("bcp.help.config.bia"), t("bcp.help.config.document")]}
          />
        </h2>
        <button
          onClick={() => setForm({ plantId })}
          className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700"
        >
          {t("bcp.actions.new_plan")}
        </button>
      </div>

      <div className="flex gap-1 mb-4 border-b border-gray-200">
        {TABS.map(key => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              tab === key ? "border-primary-600 text-primary-600" : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t(`bcp.tabs.${key}`)}
          </button>
        ))}
      </div>

      {tab === "coverage" && (
        <BcpCoverageTab
          plantId={plantId}
          plantLabel={plantLabel}
          onCreatePlan={(pid, processId) => setForm({ plantId: pid, processId })}
        />
      )}
      {tab === "plans" && (
        <BcpPlansTab
          plantId={plantId}
          plantLabel={plantLabel}
          onEdit={plan => setForm({ plan })}
          onRecordTest={setTestPlan}
        />
      )}
      {tab === "tests" && <BcpTestsTab plantId={plantId} plantLabel={plantLabel} />}

      {form && (
        <BcpPlanForm
          plants={plants}
          plan={form.plan}
          initialPlantId={form.plantId}
          initialProcessId={form.processId}
          onClose={() => setForm(null)}
        />
      )}
      {testPlan && <BcpRecordTest plan={testPlan} onClose={() => setTestPlan(null)} />}
    </div>
  );
}
